"""Lógica de descubrimiento y sincronización multi-repositorio en personal.

Permite sincronizar proyectos de forma individual o recorrer recursivamente
rutas locales y unidades de Google Drive con deduplicación por ruta real.
"""

from __future__ import annotations

import logging
import os
import sys

from context_map.application.commands.personal.common import (
    _leer_decisiones_vault,
    _leer_lecciones_vault,
    _nombre_proyecto_por_ruta,
    _rutas_proyecto,
)
from context_map.core.parsing import (
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.personal import PersonalDB

logger = logging.getLogger(__name__)


def _bases_gdrive_estandar() -> list[str]:
    """Rutas de Google Drive comunes que no dependen de la letra de unidad."""
    candidatas: list[str] = []
    userprofile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if userprofile:
        candidatas.extend([
            os.path.join(userprofile, "Google Drive", "Mi unidad"),
            os.path.join(userprofile, "Google Drive", "My Drive"),
            os.path.join(userprofile, "GoogleDrive", "Mi unidad"),
            os.path.join(userprofile, "GoogleDrive", "My Drive"),
            os.path.join(userprofile, "Mi unidad"),
            os.path.join(userprofile, "My Drive"),
        ])
    localappdata = os.environ.get("LOCALAPPDATA", "")
    if localappdata:
        candidatas.append(os.path.join(localappdata, "Google", "DriveFS"))
    return candidatas


def _bases_gdrive_letras() -> list[str]:
    """Busca unidades virtuales de Google Drive en Windows (G:, H:, etc.)."""
    candidatas: list[str] = []
    if os.name == "nt":
        import string

        for letra in string.ascii_uppercase:
            raiz = f"{letra}:\\"
            if os.path.isdir(raiz):
                for sub in ("Mi unidad", "My Drive"):
                    candidata = os.path.join(raiz, sub)
                    if os.path.isdir(candidata):
                        candidatas.append(candidata)
    return candidatas


def _bases_por_defecto() -> list[str]:
    """Carpetas base que se escanean en ``sync --todos``."""
    env_roots = os.environ.get("CTXMAP_GDRIVE_ROOTS", "")
    if env_roots:
        return [r.strip() for r in env_roots.split(os.pathsep) if r.strip()]

    bases: list[str] = []
    userprofile = os.environ.get("USERPROFILE") or os.environ.get("HOME") or ""
    if userprofile:
        for sub in ("Desktop", "Escritorio", "Projects", "Proyectos", "dev", "src", "workspace"):
            d = os.path.join(userprofile, sub)
            if os.path.isdir(d):
                bases.append(d)

    bases.extend(_bases_gdrive_estandar())
    bases.extend(_bases_gdrive_letras())

    encontradas: list[str] = []
    vistas: set[str] = set()
    for b in bases:
        if os.path.isdir(b):
            real = os.path.realpath(b)
            if real not in vistas:
                vistas.add(real)
                encontradas.append(b)
    return encontradas


def _descubrir_proyectos(base_dir: str, profundidad: int = 4) -> list[tuple[str, str]]:
    """Descubre proyectos con .context-map/ dentro de base_dir recursivamente."""
    encontrados: list[tuple[str, str]] = []
    base_dir = os.path.abspath(base_dir)

    # Si la base misma es un proyecto
    if os.path.isdir(os.path.join(base_dir, ".context-map")):
        encontrados.append((_nombre_proyecto_por_ruta(base_dir), base_dir))

    sep_count_base = base_dir.rstrip(os.sep).count(os.sep)
    for raiz, dirs, _ in os.walk(base_dir):
        nivel = raiz.count(os.sep) - sep_count_base
        if nivel >= profundidad:
            dirs.clear()
            continue

        dirs[:] = [
            d for d in dirs
            if d not in (".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".tox")
        ]

        if ".context-map" in dirs:
            dirs.remove(".context-map")
            encontrados.append((_nombre_proyecto_por_ruta(raiz), raiz))

    return encontrados


def _deduplicar_por_ruta(proyectos: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Elimina proyectos repetidos conservando el orden de descubrimiento."""
    vistos: set[str] = set()
    unicos: list[tuple[str, str]] = []
    for nombre, ruta in proyectos:
        clave = os.path.normcase(os.path.realpath(ruta))
        if clave in vistos:
            logger.debug("Proyecto repetido omitido: %s (%s)", nombre, ruta)
            continue
        vistos.add(clave)
        unicos.append((nombre, ruta))
    return unicos


def _get_personal_func(nombre: str, fallback):
    """Obtiene una función del módulo fachada personal si fue parcheada en pruebas."""
    mod = sys.modules.get("context_map.application.commands.personal")
    if mod and hasattr(mod, nombre):
        return getattr(mod, nombre)
    return fallback


def _proyectos_para_sync(args) -> list[tuple[str, str]]:
    """Determina los proyectos a consolidar según los flags del comando sync."""
    proyectos: list[tuple[str, str]] = []
    func_bases = _get_personal_func("_bases_por_defecto", _bases_por_defecto)
    func_descubrir = _get_personal_func("_descubrir_proyectos", _descubrir_proyectos)
    func_nombre = _get_personal_func("_nombre_proyecto_por_ruta", _nombre_proyecto_por_ruta)
    func_dedup = _get_personal_func("_deduplicar_por_ruta", _deduplicar_por_ruta)

    if getattr(args, "todos", False):
        bases = func_bases()
        rutas_extra = [
            r.strip()
            for r in (getattr(args, "rutas", "") or "").split(";")
            if r.strip()
        ]
        bases.extend(rutas_extra)
        for base_dir in bases:
            if not os.path.isdir(base_dir):
                continue
            proyectos.extend(func_descubrir(base_dir))
    else:
        target = getattr(args, "target", ".") or "."
        target = os.path.abspath(target)
        proyectos.append((func_nombre(target), target))
    resultado: list[tuple[str, str]] = list(func_dedup(proyectos))
    return resultado



def _cmd_personal_sync(args) -> None:
    """Consolida proyectos en la BD personal."""
    db = PersonalDB(args.db)
    func_proy_sync = _get_personal_func("_proyectos_para_sync", _proyectos_para_sync)
    func_rutas = _get_personal_func("_rutas_proyecto", _rutas_proyecto)
    func_lecc = _get_personal_func("_leer_lecciones_vault", _leer_lecciones_vault)
    func_dec = _get_personal_func("_leer_decisiones_vault", _leer_decisiones_vault)

    try:
        proyectos = func_proy_sync(args)

        total_nuevos = 0
        total_lecciones = 0
        total_decisiones = 0
        total_omitidos = 0
        for nombre, ruta in proyectos:
            events_path, chats_path, vault_base = func_rutas(ruta)
            lecciones = func_lecc(vault_base, nombre)
            decisiones = func_dec(vault_base, nombre)

            eventos: list[dict] = []
            for ev in load_events_from_jsonl(events_path):
                eventos.append(ev.to_dict())
            for ev in load_events_from_chat_folder(chats_path):
                eventos.append(ev.to_dict())

            lecciones = _leer_lecciones_vault(vault_base, nombre)
            decisiones = _leer_decisiones_vault(vault_base, nombre)

            if not eventos and not lecciones and not decisiones:
                total_omitidos += 1
                print(f"sync {nombre}: sin contenido, omitido")
                continue

            nuevos = db.cargar_eventos(nombre, eventos, ruta)
            total_nuevos += nuevos

            lecciones_proyecto = 0
            for leccion in lecciones:
                if db.agregar_leccion(leccion):
                    total_lecciones += 1
                    lecciones_proyecto += 1

            decisiones_proyecto = 0
            for decision in decisiones:
                if db.agregar_decision(decision):
                    total_decisiones += 1
                    decisiones_proyecto += 1

            print(
                f"sync {nombre}: {len(eventos)} eventos (+{nuevos} nuevos), "
                f"lecciones +{lecciones_proyecto}, decisiones +{decisiones_proyecto}"
            )

        stats = db.estadisticas()
        print()
        print(f"BD personal: {db.ruta}")
        print(
            f"  proyectos={stats['proyectos']} eventos={stats['eventos']} "
            f"lecciones={stats['lecciones']} decisiones={stats['decisiones']}"
        )
        print(f"  nuevos en esta ejecución: {total_nuevos} eventos, {total_lecciones} lecciones, {total_decisiones} decisiones")
        if total_omitidos:
            print(f"  omitidos por no tener contenido: {total_omitidos}")
    finally:
        db.cerrar()

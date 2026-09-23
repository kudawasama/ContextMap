"""Funciones compartidas de lectura y sincronización de proyectos en personal.

Contiene helpers para resolución de rutas, extracción de lecciones en
8.0-KNOWLEDGE y decisiones en 7.0-MANUAL para la base de datos personal.
"""

from __future__ import annotations

import logging
import os
import re

from context_map.core.parsing import (
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.personal import Decision, Leccion, PersonalDB

logger = logging.getLogger(__name__)


def sincronizar_proyecto_automatico(
    proj_name: str,
    target_dir: str = ".",
) -> None:
    """Consolida el proyecto en la BD personal de forma silenciosa.

    Se invoca al final de ``do_sync`` (build/scan/refresh) para conectar el
    contexto del proyecto con el contexto global personal. Nunca lanza
    excepciones: si la BD no está accesible (ej. sin F: en CI), simplemente
    se registra en DEBUG y el flujo principal continúa intacto.

    Args:
        proj_name: Nombre del proyecto (clave en la tabla ``proyectos``).
        target_dir: Directorio raíz del proyecto a consolidar.
    """
    try:
        db = PersonalDB()
        try:
            events_path, chats_path, vault_base = _rutas_proyecto(target_dir)
            eventos: list[dict] = []
            for ev in load_events_from_jsonl(events_path):
                eventos.append(ev.to_dict())
            for ev in load_events_from_chat_folder(chats_path):
                eventos.append(ev.to_dict())

            nuevos = db.cargar_eventos(proj_name, eventos, os.path.abspath(target_dir))
            lecciones = 0
            for leccion in _leer_lecciones_vault(vault_base, proj_name):
                if db.agregar_leccion(leccion):
                    lecciones += 1

            decisiones = 0
            for decision in _leer_decisiones_vault(vault_base, proj_name):
                if db.agregar_decision(decision):
                    decisiones += 1

            if nuevos or lecciones or decisiones:
                logger.info(
                    "personal: %s consolidado (+%d eventos, +%d lecciones, +%d decisiones) en %s",
                    proj_name, nuevos, lecciones, decisiones, db.ruta,
                )
        finally:
            db.cerrar()
    except Exception as err:  # pragma: no cover - tolerancia total
        logger.debug("personal: consolidación automática omitida: %s", err)


def _rutas_proyecto(target_dir: str) -> tuple[str, str, str]:
    """Resuelve las rutas internas de eventos de un proyecto.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        tuple[str, str, str]: (ruta_events_jsonl, ruta_chats, ruta_vault)
    """
    base = os.path.join(target_dir, ".context-map")
    return (
        os.path.join(base, "raw", "events.jsonl"),
        os.path.join(base, "chats"),
        base,
    )


def _nombre_proyecto_por_ruta(target_dir: str) -> str:
    """Deriva el nombre del proyecto con la MISMA regla que la consolidación.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        str: Nombre estable del proyecto.
    """
    from types import SimpleNamespace

    from context_map.application.commands._helpers import project_name

    return project_name(SimpleNamespace(project=None, target=target_dir))


def _campo_knowledge(marca: str, cuerpo_nota: str) -> str:
    """Extrae un campo del formato knowledge (marca emoji -> siguiente marca).

    Args:
        marca (str): Marca emoji del campo (p. ej. '🎯 Lección').
        cuerpo_nota (str): Cuerpo de la nota sin frontmatter.

    Returns:
        str: Valor del campo, o string vacío si no se encontró.
    """
    patron = rf"{re.escape(marca)}\s*:?\s*(.*?)(?=\n\s*(?:🎯|🛠️|💬|📋|🔗)|\Z)"
    m = re.search(patron, cuerpo_nota, re.DOTALL)
    return m.group(1).strip() if m else ""


def _parsear_leccion(proyecto: str, cuerpo: str, titulo: str, nombre: str) -> Leccion:
    """Convierte el cuerpo de una nota knowledge en una Leccion estructurada.

    Args:
        proyecto (str): Nombre del proyecto para asociar la lección.
        cuerpo (str): Cuerpo de la nota sin frontmatter.
        titulo (str): Título derivado de la nota (primer encabezado o nombre).
        nombre (str): Nombre del archivo de la nota.

    Returns:
        Leccion: Lección estructurada con los campos disponibles.
    """
    leccion = _campo_knowledge("🎯 Lección", cuerpo)
    leccion = re.sub(r"^#\s*", "", leccion).strip() or titulo
    como = _campo_knowledge("🛠️ Cómo se resolvió", cuerpo)
    prompt = _campo_knowledge("💬 Prompt", cuerpo)
    instruccion = _campo_knowledge("📋 Instrucción", cuerpo)
    conexiones = _campo_knowledge("🔗 Conexiones", cuerpo)
    if not como and not prompt and not instruccion:
        cuerpo_limpio = re.sub(r"^#\s+.+$", "", cuerpo, count=1, flags=re.MULTILINE).strip()
        como = cuerpo_limpio[:500]
        conexiones = f"Origen: {nombre}"
    return Leccion(
        leccion=leccion,
        como_se_resolvio=como,
        prompt=prompt,
        instruccion=instruccion,
        conexiones=conexiones,
        proyecto=proyecto,
    )


def _leer_lecciones_vault(vault_base: str, proyecto: str) -> list[Leccion]:
    """Extrae lecciones de la zona 8.0-KNOWLEDGE del vault (si existe).

    Args:
        vault_base: Directorio base de ``.context-map`` del proyecto.
        proyecto: Nombre del proyecto para asociar las lecciones.

    Returns:
        list[Leccion]: Lecciones encontradas en ``8.0-KNOWLEDGE/*.md``.
    """
    knowledge_dir = None
    for candidato in (
        os.path.join(vault_base, "vault", "8.0-KNOWLEDGE"),
        os.path.join(vault_base, "vault-" + proyecto, "8.0-KNOWLEDGE"),
        os.path.join(vault_base, "8.0-KNOWLEDGE"),
    ):
        if os.path.isdir(candidato):
            knowledge_dir = candidato
            break
    if not knowledge_dir:
        return []

    lecciones: list[Leccion] = []
    for nombre in sorted(os.listdir(knowledge_dir)):
        if not nombre.endswith(".md"):
            continue
        nombre_upper = nombre.upper()
        if (
            nombre_upper.startswith("00-")
            or "INDICE" in nombre_upper
            or nombre in ("8.0-KNOWLEDGE.md", "README.md", "TEMPLATE.md", "PLANTILLA.md")
        ):
            continue

        ruta = os.path.join(knowledge_dir, nombre)
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
        except OSError:
            continue

        cuerpo = re.sub(r"^---.*?---\s*", "", contenido, flags=re.DOTALL).strip()
        if not cuerpo or ("🎯 Lección" not in cuerpo and "## " not in cuerpo):
            continue

        titulo = nombre[:-3].replace("-", " ").replace("_", " ").strip()
        m_titulo = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
        if m_titulo:
            titulo = m_titulo.group(1).strip()

        lec_obj = _parsear_leccion(proyecto, cuerpo, titulo, nombre)
        if lec_obj and lec_obj.leccion:
            lecciones.append(lec_obj)
    return lecciones


def _leer_decisiones_vault(vault_base: str, proyecto: str) -> list[Decision]:
    """Extrae decisiones de arquitectura y directrices desde el vault.

    Args:
        vault_base: Directorio base de ``.context-map`` del proyecto.
        proyecto: Nombre del proyecto.

    Returns:
        list[Decision]: Lista de decisiones estructuradas.
    """
    decisiones: list[Decision] = []
    candidatos_dirs = [
        os.path.join(vault_base, "vault", "7.0-MANUAL"),
        os.path.join(vault_base, "vault-" + proyecto, "7.0-MANUAL"),
        os.path.join(vault_base, "7.0-MANUAL"),
    ]

    for cdir in candidatos_dirs:
        if not os.path.isdir(cdir):
            continue
        for raiz, _, archivos in os.walk(cdir):
            for arch in archivos:
                if not arch.endswith(".md"):
                    continue
                ruta_arch = os.path.join(raiz, arch)
                try:
                    with open(ruta_arch, encoding="utf-8") as f:
                        contenido = f.read()
                except OSError:
                    continue

                m_type = re.search(r"^type:\s*(decision|directriz|regla|adr)\b", contenido, re.MULTILINE | re.I)
                if m_type:
                    tit = arch[:-3].replace("-", " ").replace("_", " ").strip()
                    m_tit = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
                    if m_tit:
                        tit = m_tit.group(1).strip()
                    cuerpo = re.sub(r"^---.*?---\s*", "", contenido, flags=re.DOTALL).strip()
                    decisiones.append(Decision(decision=tit, contexto=cuerpo[:400], proyecto=proyecto))
                    continue

                m_sec = re.search(r"##\s+(?:🎯\s*)?Decisiones.*?\n(.*?)(?=\n##|\Z)", contenido, re.DOTALL | re.I)
                if m_sec:
                    bloque = m_sec.group(1).strip()
                    for linea in bloque.splitlines():
                        linea_limpia = linea.strip()
                        if linea_limpia.startswith(("-", "*")) and len(linea_limpia) > 5:
                            texto_dec = linea_limpia.lstrip("-* ").strip()
                            decisiones.append(Decision(decision=texto_dec[:200], contexto=f"En {arch}", proyecto=proyecto))

    return decisiones

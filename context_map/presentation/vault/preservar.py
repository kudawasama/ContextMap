"""Limpieza del vault preservando el trabajo manual.

Centraliza la lógica de "borrar el vault regenerable SIN tocar lo que el
usuario/agente creó a mano":

- La carpeta reservada ``.manual/`` completa (zona protegida).
- Cualquier nota con frontmatter ``preserve: true`` (esté donde esté).

La usan ``build --clean`` (vía ``clean_vault_dir``) y los renderizadores del
vault (jerárquico/consolidado), que antes hacían ``shutil.rmtree`` directo y
destruían las notas manuales en cada build.
"""

from __future__ import annotations

import logging
import os
import shutil

logger = logging.getLogger(__name__)

NOMBRE_ZONA_MANUAL = ".manual"


def _leer_frontmatter_preserve(fpath: str) -> bool:
    """Detecta si una nota del vault pide ser preservada (frontmatter preserve: true).

    Args:
        fpath (str): Ruta del archivo Markdown.

    Returns:
        bool: True si el frontmatter contiene ``preserve: true``.
    """
    try:
        with open(fpath, encoding="utf-8") as f:
            primeras = [next(f, "") for _ in range(10)]
    except Exception:
        return False
    if not primeras or primeras[0].strip() != "---":
        return False
    for linea in primeras[1:]:
        if linea.strip().startswith("---"):
            break
        clave = linea.strip().lower().replace(" ", "")
        if clave.startswith("preserve:") and "true" in clave:
            return True
    return False


def _copiar_dir(origen: str, destino: str) -> None:
    """Copia recursiva de un directorio (sin sobrescribir destino existente)."""
    if not os.path.isdir(origen):
        return
    for raiz, _dirs, archivos in os.walk(origen):
        for archivo in archivos:
            src = os.path.join(raiz, archivo)
            rel = os.path.relpath(src, origen)
            dst = os.path.join(destino, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def limpiar_vault(output_dir: str) -> int:
    """Elimina el vault regenerable preservando el trabajo manual.

    Respalda ``.manual/`` y las notas con ``preserve: true`` en un directorio
    temporal, borra el vault, lo recrea y restaura lo respaldado.

    Args:
        output_dir (str): Directorio raíz del vault.

    Returns:
        int: Cantidad de archivos manuales preservados.
    """
    temp_preservados = os.path.join(output_dir, "..", "_preservar_manual")
    temp_preservados = os.path.abspath(temp_preservados)

    manual_dir = os.path.join(output_dir, NOMBRE_ZONA_MANUAL)
    if os.path.isdir(manual_dir):
        destino_manual = os.path.join(temp_preservados, NOMBRE_ZONA_MANUAL)
        os.makedirs(destino_manual, exist_ok=True)
        _copiar_dir(manual_dir, destino_manual)

    # Notas preserve:true en cualquier parte del vault (excepto .manual/, ya respaldado)
    if os.path.isdir(output_dir):
        for raiz, _dirs, archivos in os.walk(output_dir):
            if NOMBRE_ZONA_MANUAL in raiz.split(os.sep):
                continue
            for fname in archivos:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(raiz, fname)
                if _leer_frontmatter_preserve(fpath):
                    rel = os.path.relpath(fpath, output_dir)
                    dst = os.path.join(temp_preservados, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    try:
                        shutil.copy2(fpath, dst)
                    except Exception as err:
                        logger.debug("No se pudo respaldar nota preserve %s: %s", rel, err)

    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)

    n_restaurados = 0
    if os.path.isdir(temp_preservados):
        _copiar_dir(temp_preservados, output_dir)
        n_restaurados = sum(
            len(archivos)
            for _raiz, _dirs, archivos in os.walk(temp_preservados)
        )
        shutil.rmtree(temp_preservados, ignore_errors=True)

    return n_restaurados

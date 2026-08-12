"""Verificación de actualizaciones de ContextMap.

Compara la versión local con el último tag publicado en GitHub y avisa si
hay una actualización pendiente. La consulta remota va con caché (24h) y
NUNCA bloquea: si la red falla, se informa silenciosamente.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.request

logger = logging.getLogger(__name__)

REPO_API_TAGS = "https://api.github.com/repos/kudawasama/ContextMap/tags"
_CACHE_PATH = os.path.join(os.path.expanduser("~"), ".context-map-version.json")
_CACHE_TTL = 24 * 3600  # 24 horas


def version_local() -> str:
    """Versión local de ContextMap.

    Usa los metadatos del paquete instalado; si corre desde el repo sin
    instalar, lee ``pyproject.toml``.

    Returns:
        str: Versión local (ej. "1.3.0").
    """
    try:
        import importlib.metadata as md

        return md.version("context-map")
    except Exception:
        pass
    try:
        import tomllib

        with open(os.path.join(os.path.dirname(__file__), "..", "..", "pyproject.toml"), "rb") as f:
            data = tomllib.load(f)
        return str(data.get("project", {}).get("version", "0.0.0"))
    except Exception:
        return "0.0.0"


def _normalizar(v: str) -> tuple:
    """Convierte 'v1.2.3' o '1.2.3' a tupla comparable (1, 2, 3)."""
    v = v.strip().lstrip("vV")
    partes: list[int] = []
    for p in v.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        partes.append(int(num) if num else 0)
    while len(partes) < 3:
        partes.append(0)
    return tuple(partes[:3])


def _leer_cache() -> str | None:
    """Lee la última versión remota cacheada si no expiró."""
    try:
        if os.path.exists(_CACHE_PATH):
            with open(_CACHE_PATH, encoding="utf-8") as f:
                datos = json.load(f)
            if time.time() - datos.get("ts", 0) < _CACHE_TTL:
                return datos.get("version")
    except Exception:
        pass
    return None


def _guardar_cache(version: str) -> None:
    try:
        with open(_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "version": version}, f)
    except Exception:
        pass


def ultima_version_remota(force: bool = False) -> str | None:
    """Última versión publicada en GitHub (tags), con caché de 24h.

    Args:
        force (bool): Ignorar la caché y consultar de nuevo.

    Returns:
        str | None: Última versión (ej. "1.4.0") o None si no se pudo.
    """
    if not force:
        cache = _leer_cache()
        if cache:
            return cache

    try:
        req = urllib.request.Request(
            REPO_API_TAGS,
            headers={"User-Agent": "context-map", "Accept": "application/vnd.github+json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
        if not isinstance(tags, list) or not tags:
            return None
        # Los tags vienen ordenados (el más reciente primero); tomar el primero
        # que parezca una versión semántica.
        for tag in tags:
            nombre = str(tag.get("name", ""))
            if nombre and nombre[0].isdigit() or nombre.startswith("v"):
                _guardar_cache(nombre.lstrip("v"))
                return nombre.lstrip("v")
        return None
    except Exception as err:  # noqa: BLE001 — sin red no debe romper nada
        logger.debug("No se pudo consultar la última versión: %s", err)
        return None


def hay_actualizacion(force: bool = False) -> tuple[bool, str, str]:
    """Compara la versión local con la remota.

    Args:
        force (bool): Ignorar la caché.

    Returns:
        tuple[bool, str, str]: (hay actualización, versión local, versión remota).
    """
    local = version_local()
    remota = ultima_version_remota(force=force)
    if not remota:
        return False, local, ""
    try:
        return _normalizar(remota) > _normalizar(local), local, remota
    except Exception:
        return False, local, remota


def aviso_actualizacion(force: bool = False) -> str:
    """Aviso de actualización pendiente (vacío si no hay o no se pudo saber).

    Se usa al final de los comandos (check, refresh, build) para informar de
    actualizaciones sin bloquear. Respeta la caché de 24h.

    Args:
        force (bool): Ignorar la caché.

    Returns:
        str: Mensaje de aviso o string vacío.
    """
    try:
        hay, local, remota = hay_actualizacion(force=force)
        if hay:
            return (
                f"\n⬆️ Hay una actualización disponible: v{remota} (tienes {local}).\n"
                f"   Actualiza con: uv tool install --force "
                f"git+https://github.com/kudawasama/ContextMap.git"
            )
    except Exception as err:  # noqa: BLE001 — jamás romper el flujo por esto
        logger.debug("aviso de actualización omitido: %s", err)
    return ""


def aviso_pre_actualizacion(force: bool = False) -> str:
    """Aviso DESTACADO para ANTES de actualizar el contexto (punto de control).

    A diferencia de ``aviso_actualizacion`` (que se muestra al final de los
    comandos), este se usa al INICIO de ``refresh``: si el PROGRAMA (binario)
    está desactualizado, se solicita actualizarlo antes de actualizar el
    CONTEXTO del proyecto (lección: actualizar el programa ≠ actualizar el
    contexto). El aviso es accionable y no bloqueante — jamás interrumpe.

    Args:
        force (bool): Ignorar la caché de 24h.

    Returns:
        str: Mensaje destacado o string vacío si no hay actualización.
    """
    try:
        hay, local, remota = hay_actualizacion(force=force)
        if hay:
            return (
                f"\n⬆️⚠️  ContextMap DESACTUALIZADO: tienes v{local}, la última es v{remota}.\n"
                f"   Antes de actualizar el CONTEXTO, actualiza el PROGRAMA:\n"
                f"   uv tool install --force \"git+https://github.com/kudawasama/ContextMap.git\" "
                f"--with \"mcp>=1.2.0,<2.0.0\"\n"
            )
    except Exception as err:  # noqa: BLE001 — jamás romper el flujo por esto
        logger.debug("aviso pre-actualización omitido: %s", err)
    return ""

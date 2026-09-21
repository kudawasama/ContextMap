"""Fuente única de verdad de lo que el análisis de código debe ignorar.

Antes cada analizador mantenía su propia lista y solo el escáner conocía las
cachés modernas de despliegue. Consecuencia real (auditoría 2026-09-21): un
proyecto con `.vercel/` se contaba con sus dependencias vendorizadas —3.721
archivos y 909.560 líneas en lugar de su código— y su riesgo principal de
complejidad señalaba a `fastapi/routing.py` y `setuptools`, no al proyecto.

Criterio de inclusión: solo rutas **inequívocamente** generadas o de terceros.
Nombres ambiguos como `target`, `vendor`, `env` o `lib` NO se excluyen porque
pueden contener código fuente legítimo del proyecto.
"""

from __future__ import annotations

import os

CARPETAS_EXCLUIDAS: frozenset[str] = frozenset(
    {
        # Control de versiones y contexto
        ".git",
        ".hg",
        ".svn",
        ".context-map",
        # Entornos virtuales y dependencias de terceros
        ".venv",
        "venv",
        "env",
        "node_modules",
        "site-packages",
        "archive-v0",
        # Cachés de herramientas
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".cache",
        ".turbo",
        ".eggs",
        # Artefactos de build y despliegue
        "dist",
        "build",
        ".next",
        ".nuxt",
        ".output",
        ".svelte-kit",
        ".vercel",
        # Cobertura
        "coverage",
        "htmlcov",
        # Infraestructura como código
        ".terraform",
        ".serverless",
        ".aws-sam",
        # Editores
        ".idea",
        ".vscode",
        ".vs",
        # Directorios temporales del propio repositorio
        ".tmp-verif",
        ".tmp-tests",
    }
)
"""Nombres de carpeta que nunca se analizan (comparación exacta, sin distinción de mayúsculas)."""

ARCHIVOS_EXCLUIDOS: frozenset[str] = frozenset({"desktop.ini", ".ds_store", "thumbs.db"})
"""Archivos de sistema que nunca cuentan como código ni como conversación."""

SUFIJOS_EXCLUIDOS: tuple[str, ...] = (".egg-info", ".gdoc", ".gsheet", ".gslides")
"""Sufijos de carpeta/archivo generados por herramientas."""


def es_carpeta_excluida(nombre: str) -> bool:
    """Indica si una carpeta debe ignorarse durante el análisis.

    Args:
        nombre: Nombre de la carpeta (sin ruta).

    Returns:
        bool: True si la carpeta está excluida.
    """
    bajo = nombre.lower()
    return bajo in CARPETAS_EXCLUIDAS or bajo.endswith(SUFIJOS_EXCLUIDOS)


def es_archivo_excluido(nombre: str) -> bool:
    """Indica si un archivo debe ignorarse (sistema, binarios de Drive).

    Args:
        nombre: Nombre del archivo (sin ruta).

    Returns:
        bool: True si el archivo está excluido.
    """
    return nombre.lower() in ARCHIVOS_EXCLUIDOS or nombre.lower().endswith(SUFIJOS_EXCLUIDOS)


def es_ruta_excluida(ruta: str) -> bool:
    """Indica si alguna parte de la ruta está excluida.

    Args:
        ruta: Ruta completa o relativa a evaluar.

    Returns:
        bool: True si debe ignorarse.
    """
    if es_archivo_excluido(os.path.basename(ruta)):
        return True
    partes = ruta.replace("\\", "/").split("/")
    return any(es_carpeta_excluida(parte) for parte in partes if parte not in ("", ".", ".."))


def carpetas_excluidas() -> list[str]:
    """Devuelve la lista canónica de carpetas excluidas.

    Returns:
        list[str]: Nombres de carpeta ordenados, listos para APIs que esperan una lista.
    """
    return sorted(CARPETAS_EXCLUIDAS)

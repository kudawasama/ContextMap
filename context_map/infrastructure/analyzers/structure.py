"""Analizador de estructura de proyecto.

Escanea archivos, clasifica por tipo, y genera contexto estructural.
"""

from __future__ import annotations

import os
import re
from typing import List, Dict, Set
from dataclasses import dataclass, field


@dataclass
class ArchivoInfo:
    """Información de un archivo analizado."""
    ruta: str
    tipo: str  # python, js, config, doc, test, etc.
    tamano: int = 0
    es_entrypoint: bool = False
    es_importante: bool = False
    es_config: bool = False
    es_test: bool = False
    es_doc: bool = False


@dataclass
class EstructuraProyecto:
    """Resultado del análisis de estructura."""
    nombre: str
    ruta_raiz: str
    archivos: List[ArchivoInfo] = field(default_factory=list)
    por_tipo: Dict[str, int] = field(default_factory=dict)
    entrypoints: List[str] = field(default_factory=list)
    configs: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    docs: List[str] = field(default_factory=list)
    total_lineas: int = 0


# Extensiones clasificadas
EXTENSIONES_PYTHON = {".py", ".pyw", ".pyi"}
EXTENSIONES_JS = {".js", ".jsx", ".ts", ".tsx", ".mjs"}
EXTENSIONES_CONFIG = {
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env",
    ".gitignore", ".dockerignore", "Dockerfile", "docker-compose.yml",
}
EXTENSIONES_DOC = {".md", ".rst", ".txt", ".adoc"}
EXTENSIONES_TEST = {"test_", "_test.py", "tests.py", "spec.py"}

# Archivos importantes
ARCHIVOS_IMPORTANTES = {
    "README.md", "README.rst", "README.txt",
    "CHANGELOG.md", "CHANGES.md", "HISTORY.md",
    "LICENSE", "LICENSE.md", "LICENSE.txt",
    "CONTRIBUTING.md", "CONTRIBUTING.rst",
    "AGENTS.md", "CLAUDE.md", "CURSOR.md",
}

# Archivos de config conocidos
ARCHIVOS_CONFIG = {
    "pyproject.toml", "setup.py", "setup.cfg",
    "package.json", "tsconfig.json",
    "Makefile", "Justfile",
    ".env", ".env.example",
    "requirements.txt", "requirements-dev.txt",
}

# Patrones de entrypoint
PATRONES_ENTRYPOINT = [
    r"^main\.py$",
    r"^app\.py$",
    r"^cli\.py$",
    r"^__main__\.py$",
    r"^server\.py$",
    r"^index\.(js|ts)$",
]


def _es_entrypoint(ruta: str) -> bool:
    """Determina si un archivo es un entrypoint."""
    nombre = os.path.basename(ruta)
    for patron in PATRONES_ENTRYPOINT:
        if re.match(patron, nombre):
            return True
    return False


def _clasificar_archivo(ruta: str) -> str:
    """Clasifica un archivo por su tipo."""
    _, ext = os.path.splitext(ruta)
    nombre = os.path.basename(ruta)

    if ext in EXTENSIONES_PYTHON:
        return "python"
    elif ext in EXTENSIONES_JS:
        return "javascript"
    elif ext in EXTENSIONES_CONFIG or nombre in ARCHIVOS_CONFIG:
        return "config"
    elif ext in EXTENSIONES_DOC:
        return "doc"
    elif "test" in nombre.lower() or "spec" in nombre.lower():
        return "test"
    else:
        return "otro"


def _contar_lineas(ruta: str) -> int:
    """Cuenta líneas de un archivo de texto."""
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def escanear_proyecto(ruta_raiz: str, ignorar: List[str] = None) -> EstructuraProyecto:
    """Escanea un proyecto y retorna su estructura.

    Args:
        ruta_raiz: Ruta raíz del proyecto
        ignorar: Lista de carpetas a ignorar

    Returns:
        EstructuraProyecto con toda la información
    """
    if ignorar is None:
        ignorar = {
            "__pycache__", ".git", ".venv", "venv", "env",
            "node_modules", ".mypy_cache", ".pytest_cache",
            ".tox", "dist", "build", "*.egg-info",
        }

    nombre = os.path.basename(os.path.abspath(ruta_raiz))
    estructura = EstructuraProyecto(nombre=nombre, ruta_raiz=ruta_raiz)

    for dirpath, dirnames, filenames in os.walk(ruta_raiz):
        # Filtrar directorios ignorados
        dirnames[:] = [
            d for d in dirnames
            if d not in ignorar and not d.endswith(".egg-info")
        ]

        for filename in filenames:
            ruta_completa = os.path.join(dirpath, filename)
            ruta_relativa = os.path.relpath(ruta_completa, ruta_raiz)

            # Saltar archivos binarios grandes
            try:
                tamano = os.path.getsize(ruta_completa)
            except OSError:
                continue

            if tamano > 1_000_000:  # > 1MB
                continue

            tipo = _clasificar_archivo(ruta_completa)
            lineas = _contar_lineas(ruta_completa)

            archivo = ArchivoInfo(
                ruta=ruta_relativa,
                tipo=tipo,
                tamano=tamano,
                es_entrypoint=_es_entrypoint(ruta_relativa),
                es_importante=filename in ARCHIVOS_IMPORTANTES,
                es_config=filename in ARCHIVOS_CONFIG or tipo == "config",
                es_test="test" in filename.lower() or "spec" in filename.lower(),
                es_doc=tipo == "doc",
            )

            estructura.archivos.append(archivo)
            estructura.total_lineas += lineas

            # Contar por tipo
            estructura.por_tipo[tipo] = estructura.por_tipo.get(tipo, 0) + 1

            # Agrupar
            if archivo.es_entrypoint:
                estructura.entrypoints.append(ruta_relativa)
            if archivo.es_config:
                estructura.configs.append(ruta_relativa)
            if archivo.es_test:
                estructura.tests.append(ruta_relativa)
            if archivo.es_doc:
                estructura.docs.append(ruta_relativa)

    return estructura

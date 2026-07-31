"""Analizador de contenido de archivos.

Extrae información útil del código fuente.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field


@dataclass
class InfoContenido:
    """Información extraída del contenido de un archivo."""
    ruta: str
    docstring_principal: str = ""
    imports: list[str] = field(default_factory=list)
    clases: list[str] = field(default_factory=list)
    funciones: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    lineas_codigo: int = 0
    complejidad: str = "baja"  # baja, media, alta


def extraer_docstring(ruta: str) -> str:
    """Extrae el docstring principal de un archivo Python."""
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            contenido = f.read(4000)  # Solo primeros 4KB

        # Buscar docstring triple comillas
        match = re.search(r'"""(.*?)"""', contenido, re.DOTALL)
        if match:
            return match.group(1).strip()[:200]

        match = re.search(r"'''(.*?)'''", contenido, re.DOTALL)
        if match:
            return match.group(1).strip()[:200]

    except Exception:
        pass
    return ""


def extraer_imports(ruta: str) -> list[str]:
    """Extrae imports de un archivo Python."""
    imports = []
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            for linea in f:
                linea = linea.strip()
                if linea.startswith("import ") or linea.startswith("from "):
                    imports.append(linea[:100])
                if len(imports) >= 20:  # Límite
                    break
    except Exception:
        pass
    return imports


def extraer_clases(ruta: str) -> list[str]:
    """Extrae nombres de clases de un archivo Python."""
    clases = []
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            for linea in f:
                match = re.match(r"class\s+(\w+)", linea)
                if match:
                    clases.append(match.group(1))
    except Exception:
        pass
    return clases


def extraer_funciones(ruta: str) -> list[str]:
    """Extrae nombres de funciones de un archivo Python."""
    funciones = []
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            for linea in f:
                match = re.match(r"def\s+(\w+)", linea)
                if match:
                    funciones.append(match.group(1))
    except Exception:
        pass
    return funciones


def extraer_todos(ruta: str) -> list[str]:
    """Extrae TODOs, FIXMEs, HACKs de un archivo."""
    todos = []
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            for i, linea in enumerate(f, 1):
                linea_lower = linea.lower()
                if any(kw in linea_lower for kw in ["todo", "fixme", "hack", "bug", "optimize"]):
                    todos.append(f"L{i}: {linea.strip()[:100]}")
                if len(todos) >= 10:
                    break
    except Exception:
        pass
    return todos


def calcular_complejidad(ruta: str) -> str:
    """Calcula el nivel de complejidad ciclomática de un archivo Python."""
    from context_map.domain.analysis.complexity import calcular_complejidad_archivo
    res = calcular_complejidad_archivo(ruta)
    if res:
        if res.max_complejidad_funcion > 10 or res.complejidad_total > 40:
            return "alta"
        elif res.max_complejidad_funcion > 5 or res.complejidad_total > 20:
            return "media"
    return "baja"


def analizar_contenido(ruta: str) -> InfoContenido | None:
    """Analiza el contenido de un archivo y extrae información."""
    if not os.path.isfile(ruta):
        return None

    _, ext = os.path.splitext(ruta)
    if ext not in {".py", ".pyw"}:
        return None

    info = InfoContenido(ruta=ruta)
    info.docstring_principal = extraer_docstring(ruta)
    info.imports = extraer_imports(ruta)
    info.clases = extraer_clases(ruta)
    info.funciones = extraer_funciones(ruta)
    info.todos = extraer_todos(ruta)
    info.complejidad = calcular_complejidad(ruta)

    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            info.lineas_codigo = sum(1 for _ in f)
    except Exception:
        pass

    return info


def analizar_directorio(ruta: str) -> list[InfoContenido]:
    """Analiza todos los archivos Python de un directorio."""
    ignorar = {
        "__pycache__", ".git", ".venv", "venv", "env",
        "node_modules", ".mypy_cache", ".pytest_cache",
        ".tox", "dist", "build", "*.egg-info",
        ".context-map",
    }
    resultados = []
    contador = 0
    for dirpath, dirnames, filenames in os.walk(ruta):
        # Filtrar directorios ignorados
        dirnames[:] = [
            d for d in dirnames
            if d not in ignorar and not d.endswith(".egg-info")
        ]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            ruta_completa = os.path.join(dirpath, filename)
            # Saltar archivos grandes
            try:
                if os.path.getsize(ruta_completa) > 1_000_000:
                    continue
            except OSError:
                continue
            contador += 1
            if contador % 10 == 0:
                print(f"   [analizando] Archivos Python analizados: {contador}\r", end="", flush=True)
            info = analizar_contenido(ruta_completa)
            if info:
                resultados.append(info)
    if contador > 0:
        print(f"   [OK] Archivos Python analizados: {contador} total    ")
    return resultados

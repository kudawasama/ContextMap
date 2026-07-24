"""Analizador de contenido de archivos.

Extrae información útil del código fuente.
"""

from __future__ import annotations

import re
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class InfoContenido:
    """Información extraída del contenido de un archivo."""
    ruta: str
    docstring_principal: str = ""
    imports: List[str] = field(default_factory=list)
    clases: List[str] = field(default_factory=list)
    funciones: List[str] = field(default_factory=list)
    todos: List[str] = field(default_factory=list)
    lineas_codigo: int = 0
    complejidad: str = "baja"  # baja, media, alta


def extraer_docstring(ruta: str) -> str:
    """Extrae el docstring principal de un archivo Python."""
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
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


def extraer_imports(ruta: str) -> List[str]:
    """Extrae imports de un archivo Python."""
    imports = []
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                linea = linea.strip()
                if linea.startswith("import ") or linea.startswith("from "):
                    imports.append(linea[:100])
                if len(imports) >= 20:  # Límite
                    break
    except Exception:
        pass
    return imports


def extraer_clases(ruta: str) -> List[str]:
    """Extrae nombres de clases de un archivo Python."""
    clases = []
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                match = re.match(r"class\s+(\w+)", linea)
                if match:
                    clases.append(match.group(1))
    except Exception:
        pass
    return clases


def extraer_funciones(ruta: str) -> List[str]:
    """Extrae nombres de funciones de un archivo Python."""
    funciones = []
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                match = re.match(r"def\s+(\w+)", linea)
                if match:
                    funciones.append(match.group(1))
    except Exception:
        pass
    return funciones


def extraer_todos(ruta: str) -> List[str]:
    """Extrae TODOs, FIXMEs, HACKs de un archivo."""
    todos = []
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
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
    """Estima la complejidad de un archivo Python."""
    try:
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            lineas = f.readlines()

        total = len(lineas)
        if total == 0:
            return "baja"

        # Contar estructuras de control
        estructuras = 0
        for linea in lineas:
            linea = linea.strip()
            if any(linea.startswith(kw) for kw in ["if ", "elif ", "for ", "while ", "try:", "except"]):
                estructuras += 1

        ratio = estructuras / total if total > 0 else 0

        if ratio > 0.3 or total > 500:
            return "alta"
        elif ratio > 0.15 or total > 200:
            return "media"
        else:
            return "baja"

    except Exception:
        return "baja"


def analizar_contenido(ruta: str) -> Optional[InfoContenido]:
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
        with open(ruta, "r", encoding="utf-8", errors="ignore") as f:
            info.lineas_codigo = sum(1 for _ in f)
    except Exception:
        pass

    return info


def analizar_directorio(ruta: str) -> List[InfoContenido]:
    """Analiza todos los archivos Python de un directorio."""
    resultados = []
    for dirpath, _, filenames in os.walk(ruta):
        for filename in filenames:
            if filename.endswith(".py"):
                ruta_completa = os.path.join(dirpath, filename)
                info = analizar_contenido(ruta_completa)
                if info:
                    resultados.append(info)
    return resultados

"""Analizador de contenido de archivos.

Extrae información útil del código fuente.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict, dataclass, field

from context_map.infrastructure.analyzers.exclusions import (
    CARPETAS_EXCLUIDAS,
    es_carpeta_excluida,
)

logger = logging.getLogger(__name__)


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

    except Exception as err:
        logger.debug("No se pudo extraer docstring de %s: %s", ruta, err)
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
    except Exception as err:
        logger.debug("No se pudieron extraer imports de %s: %s", ruta, err)
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
    except Exception as err:
        logger.debug("No se pudieron extraer clases de %s: %s", ruta, err)
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
    except Exception as err:
        logger.debug("No se pudieron extraer funciones de %s: %s", ruta, err)
    return funciones


_RE_MARCADOR_TODO = re.compile(
    r"(?:#|//|/\*|\*|<!--|--)\s*(?:TODO|FIXME|HACK|BUG|OPTIMIZE|XXX)[Ss]?\b:?"
)
"""Marcador de tarea pendiente: requiere signo de comentario y palabra en MAYÚSCULAS.

La heurística anterior buscaba la subcadena ``todo``/``bug`` en cualquier línea,
así que marcaba como pendiente la prosa en español («todo el rango», «todos los
módulos»), las llamadas ``logger.debug(...)`` y los docstrings. En la BD personal
eso produjo 647 de 685 eventos ``TODO`` falsos (94%). La coincidencia en
mayúsculas es deliberada: ``# todo`` en un comentario en español es prosa, no un
marcador; ``# TODO`` sí lo es.
"""


def extraer_todos(ruta: str) -> list[str]:
    """Extrae los marcadores TODO/FIXME/HACK/BUG/OPTIMIZE/XXX escritos en comentarios.

    Args:
        ruta (str): Ruta del archivo a analizar.

    Returns:
        list[str]: Líneas con marcador, con el formato ``L<n>: <texto>``
        (máximo 10 por archivo).
    """
    todos = []
    try:
        with open(ruta, encoding="utf-8", errors="ignore") as f:
            for i, linea in enumerate(f, 1):
                if _RE_MARCADOR_TODO.search(linea):
                    todos.append(f"L{i}: {linea.strip()[:100]}")
                if len(todos) >= 10:
                    break
    except Exception as err:
        logger.debug("No se pudieron extraer TODOs de %s: %s", ruta, err)
    return todos


def calcular_complejidad(ruta: str) -> str:
    """Calcula el nivel de complejidad ciclomática de un archivo Python."""
    from context_map.domain.analyzers.cyclomatic import calcular_complejidad_archivo
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
    except Exception as err:
        logger.debug("No se pudo contar líneas de %s: %s", ruta, err)

    return info


def _cargar_scan_cache(ruta_cache: str) -> dict[str, dict[str, object]]:
    """Carga la caché de análisis sintáctico de archivos desde disco si existe."""
    if not os.path.isfile(ruta_cache):
        return {}
    try:
        with open(ruta_cache, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception as err:
        logger.debug("No se pudo leer la caché de escaneo %s: %s", ruta_cache, err)
    return {}


def _guardar_scan_cache(cache: dict[str, dict[str, object]], ruta_cache: str) -> None:
    """Persiste la caché de análisis en disco de manera segura."""
    try:
        os.makedirs(os.path.dirname(ruta_cache), exist_ok=True)
        with open(ruta_cache, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as err:
        logger.debug("No se pudo guardar la caché de escaneo en %s: %s", ruta_cache, err)


def analizar_directorio(ruta: str, use_cache: bool = True) -> list[InfoContenido]:
    """Analiza todos los archivos Python de un directorio de forma acelerada e incremental.

    Utiliza una caché basada en mtime y tamaño de archivo para evitar re-analizar
    archivos no modificados, logrando tiempos de ejecución sub-150ms en proyectos medianos/grandes.

    Args:
        ruta (str): Directorio raíz a analizar.
        use_cache (bool): Si True, habilita la reutilización de caché incremental.

    Returns:
        list[InfoContenido]: Lista de metadatos extraídos de los archivos Python.
    """
    ignorar = set(CARPETAS_EXCLUIDAS)
    resultados: list[InfoContenido] = []
    contador = 0

    ruta_cache = os.path.join(ruta, ".context-map", ".scan_cache.json")
    cache: dict[str, dict[str, object]] = _cargar_scan_cache(ruta_cache) if use_cache else {}
    nueva_cache: dict[str, dict[str, object]] = {}
    cache_modificada = False

    for dirpath, dirnames, filenames in os.walk(ruta):
        # Filtrar directorios ignorados
        dirnames[:] = [
            d for d in dirnames
            if d not in ignorar and not es_carpeta_excluida(d)
        ]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            ruta_completa = os.path.join(dirpath, filename)
            # Saltar archivos grandes (> 1MB)
            try:
                stat = os.stat(ruta_completa)
                if stat.st_size > 1_000_000:
                    continue
            except OSError as err:
                logger.debug("No se pudo obtener stat de %s: %s", ruta_completa, err)
                continue

            contador += 1
            if contador % 25 == 0:
                print(f"   [analizando] Archivos Python analizados: {contador}\r", end="", flush=True)

            ruta_key = os.path.normpath(ruta_completa)
            # Comprobar si está en caché y el archivo no ha cambiado
            cached_entry = cache.get(ruta_key)
            if (
                cached_entry
                and isinstance(cached_entry, dict)
                and cached_entry.get("mtime_ns") == stat.st_mtime_ns
                and cached_entry.get("size") == stat.st_size
                and "data" in cached_entry
                and isinstance(cached_entry["data"], dict)
            ):
                try:
                    data_dict = cached_entry["data"]
                    info_cached = InfoContenido(**data_dict)
                    resultados.append(info_cached)
                    nueva_cache[ruta_key] = cached_entry
                    continue
                except Exception:
                    pass

            # Si cambió o no está en caché, analizar en profundidad
            info_nuevo = analizar_contenido(ruta_completa)
            if info_nuevo:
                resultados.append(info_nuevo)
                nueva_cache[ruta_key] = {
                    "mtime_ns": stat.st_mtime_ns,
                    "size": stat.st_size,
                    "data": asdict(info_nuevo),
                }
                cache_modificada = True

    if contador > 0:
        print(f"   [OK] Archivos Python analizados: {contador} total    ")

    if use_cache and (cache_modificada or len(nueva_cache) != len(cache)):
        _guardar_scan_cache(nueva_cache, ruta_cache)

    return resultados


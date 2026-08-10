"""Utilidades compartidas para el renderizado de vaults consolidados y jerárquicos.

Centraliza helpers de propósito común: clasificación de nodos por tipo,
extracción del propósito del proyecto desde README y escritura de archivos
Markdown con codificación UTF-8.
"""

from __future__ import annotations

import logging
import os

from context_map.core.models import Edge, Node

logger = logging.getLogger(__name__)


def _extract_project_purpose(cwd: str) -> str:
    """Extrae el propósito del proyecto desde README.md si existe.

    Busca README.md en cwd, extrae el primer párrafo después del título,
    saltando badges, TOC y líneas vacías.

    Returns:
        String con el párrafo extraído, o string vacío si no existe.
    """
    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""

    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("#!"):
            title_idx = i
            break

    if title_idx is None:
        return ""

    start_idx = title_idx + 1
    paragraphs: list[str] = []
    current_para: list[str] = []

    for line in lines[start_idx:]:
        stripped = line.strip()

        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("[!["):
            continue

        if stripped.startswith("- [") or stripped.startswith("* ["):
            continue

        if stripped.startswith("<!--"):
            continue

        if stripped.startswith("---") or stripped.startswith("___") or stripped.startswith("***"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("#"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            break

        current_para.append(stripped)

    if current_para:
        paragraphs.append(" ".join(current_para))

    return paragraphs[0] if paragraphs else ""


def _extract_proposito_biblia(cwd: str) -> str:
    """Extrae el PROPOSITO-BIBLIA del README: tagline + sección '¿Qué es?'.

    A diferencia de ``_extract_project_purpose`` (solo el primer párrafo),
    esta función recoge la identidad completa: el tagline (línea en negrita
    tras el título) y los párrafos de la primera sección con contenido
    (normalmente ``## ¿Qué es?``), que contienen el alma del proyecto
    (qué es, por qué existe, qué promete).

    Args:
        cwd (str): Directorio raíz del proyecto.

    Returns:
        str: Párrafos de identidad separados por doble salto de línea,
        o string vacío si no se pudo extraer.
    """
    import re

    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""
    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    tagline = ""
    parrafos: list[str] = []
    en_seccion_contenido = False
    pausa_hasta_seccion = False  # tras el tagline esperamos la primera '## '

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("[!["):          # badge de imagen
            continue
        if s.startswith("---") or s.startswith("<!--") or s.startswith("___"):
            continue
        if s.startswith("# "):           # título principal
            continue
        if s.startswith("## "):
            if not en_seccion_contenido:
                # primera sección con contenido (normalmente ¿Qué es?)
                en_seccion_contenido = True
                continue
            # segunda sección → fin del bloque de identidad
            break
        if s.startswith("|") or s.startswith("- [") or s.startswith("* ["):
            continue
        if s.startswith("```"):
            continue

        # limpiar markdown: **bold**, enlaces [x](url), imágenes ![..](..)
        texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
        texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
        texto = texto.replace("**", "").strip()
        if not texto:
            continue

        if not en_seccion_contenido:
            # antes de la primera sección: el tagline (frase corta en negrita)
            if not tagline and len(texto) < 140:
                tagline = texto
            continue

        parrafos.append(texto)

    partes = [p for p in [tagline] + parrafos if p]
    return "\n\n".join(partes)


def _clasificar_nodos(nodes: list[Node]) -> dict[str, list[Node]]:
    """Clasifica los nodos del grafo según su tipo semántico.

    Args:
        nodes (list[Node]): Lista completa de nodos del mapa de contexto.

    Returns:
        dict[str, list[Node]]: Diccionario con listas de nodos agrupadas por
        tipo ('BASE', 'IDEA', 'RIESGO', 'CAMBIO', 'PRUEBA', 'FUTURO', 'HITO').
        CAMBIO agrupa también los nodos de tipo 'CORRECCION'.
    """
    return {
        "BASE": [n for n in nodes if n.type == "BASE"],
        "IDEA": [n for n in nodes if n.type == "IDEA"],
        "RIESGO": [n for n in nodes if n.type == "RIESGO"],
        "CAMBIO": [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")],
        "PRUEBA": [n for n in nodes if n.type == "PRUEBA"],
        "FUTURO": [n for n in nodes if n.type == "FUTURO"],
        "HITO": [n for n in nodes if n.type == "HITO"],
        "DOCUMENTO": [n for n in nodes if n.type == "DOCUMENTO"],
    }


def _escribir_markdown(output_dir: str, nombre: str, partes: list[str]) -> str:
    """Escribe un archivo Markdown uniendo las líneas generadas.

    Args:
        output_dir (str): Directorio donde se escribe el archivo.
        nombre (str): Nombre del archivo (debe incluir la extensión .md).
        partes (list[str]): Líneas de contenido en orden.

    Returns:
        str: Ruta absoluta/relativa del archivo escrito.
    """
    ruta = os.path.join(output_dir, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    return ruta


def _mencion_nodo_en_lista(nodo: Node, vistos: set[str], clave_limite: int = 80) -> bool:
    """Verifica si un nodo ya fue incluido en el listado.

    Args:
        nodo (Node): Nodo a evaluar.
        vistos (set[str]): Conjunto de claves ya procesadas.
        clave_limite (int): Límite de caracteres para la clave de deduplicación.

    Returns:
        bool: True si el nodo ya fue procesado, False en caso contrario.
    """
    clave = nodo.title[:clave_limite]
    if clave in vistos:
        return True
    vistos.add(clave)
    return False


def _render_grafo_conexiones(
    output_dir: str,
    nodes: list[Node],
    edges: list[Edge],
    con_wikilinks: bool = True,
    usar_rutas_reales: bool = False,
) -> None:
    """Renderiza el archivo de conexiones del grafo.

    Args:
        output_dir (str): Directorio de salida de la bóveda.
        nodes (list[Node]): Lista de nodos del mapa de contexto.
        edges (list[Edge]): Lista de aristas/relaciones.
        con_wikilinks (bool): Si True renderiza con wikilinks; si False usa
            texto plano (topología jerárquica estricta, evita nodos fantasma).
        usar_rutas_reales (bool): Si True, los wikilinks se resuelven a la
            ruta real de archivo del nodo (modo jerárquico); si False, usa
            slugs (modo raw/consolidado donde los slugs existen como archivos).
    """
    from context_map.presentation.vault.atomic import _render_conexiones

    _render_conexiones(
        output_dir, nodes, edges,
        con_wikilinks=con_wikilinks,
        usar_rutas_reales=usar_rutas_reales,
    )

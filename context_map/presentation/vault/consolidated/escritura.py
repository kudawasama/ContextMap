"""Escritura de artefactos del vault: notas Markdown y el grafo de conexiones."""

from __future__ import annotations

import os

from context_map.core.models import Edge, Node


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

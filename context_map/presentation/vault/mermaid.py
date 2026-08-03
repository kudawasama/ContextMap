"""Generador de diagramas Mermaid para la bóveda Obsidian.

Proporciona funciones para transformar nodos y relaciones (aristas)
del mapa conceptual en bloques de código Mermaid (graph TD).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_map.core.models import Edge, Node


def _sanear_etiqueta(texto: str) -> str:
    """Limpia y escapa caracteres especiales para evitar errores de sintaxis en etiquetas Mermaid.

    Args:
        texto (str): Texto original.

    Returns:
        str: Texto saneado apto para etiquetas Mermaid.
    """
    if not texto:
        return "sin_titulo"
    saneado = texto.replace('"', "'").replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
    return saneado.strip()[:50]


def _crear_id_mermaid(raw_id: str) -> str:
    """Convierte un ID arbitrario en un identificador válido para nodos Mermaid.

    Args:
        raw_id (str): ID original del nodo.

    Returns:
        str: ID alfanumérico seguro para Mermaid.
    """
    return re.sub(r"[^\w]", "_", raw_id)


def generar_diagrama_mermaid_nodo(
    node: Node,
    all_nodes: list[Node],
    edges: list[Edge],
    max_relaciones: int = 10,
) -> str:
    """Genera un diagrama Mermaid en formato 'graph TD' centrado en un nodo específico.

    Args:
        node (Node): Nodo focal.
        all_nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista completa de relaciones.
        max_relaciones (int): Límite de conexiones a graficar.

    Returns:
        str: Cadena de código Markdown con bloque ```mermaid o cadena vacía si no hay relaciones.
    """
    node_map = {n.id: n for n in all_nodes}
    rel_edges = [
        e for e in edges
        if e.source == node.id or e.target == node.id
    ][:max_relaciones]

    if not rel_edges:
        return ""

    lineas = ["```mermaid", "graph TD"]
    focal_id = _crear_id_mermaid(node.id)
    focal_label = _sanear_etiqueta(node.title)
    lineas.append(f'    {focal_id}["{focal_label}"]')

    vistos_nodos: set[str] = {focal_id}

    for e in rel_edges:
        src_id = _crear_id_mermaid(e.source)
        tgt_id = _crear_id_mermaid(e.target)

        if src_id not in vistos_nodos:
            src_node = node_map.get(e.source)
            src_label = _sanear_etiqueta(src_node.title if src_node else e.source)
            lineas.append(f'    {src_id}["{src_label}"]')
            vistos_nodos.add(src_id)

        if tgt_id not in vistos_nodos:
            tgt_node = node_map.get(e.target)
            tgt_label = _sanear_etiqueta(tgt_node.title if tgt_node else e.target)
            lineas.append(f'    {tgt_id}["{tgt_label}"]')
            vistos_nodos.add(tgt_id)

        rel_kind = e.kind or "relacionado"
        lineas.append(f'    {src_id} -->|{rel_kind}| {tgt_id}')

    lineas.append("```")
    return "\n".join(lineas)


def generar_diagrama_mermaid_global(
    nodes: list[Node],
    edges: list[Edge],
    max_edges: int = 20,
) -> str:
    """Genera un diagrama Mermaid global que representa la topología principal del proyecto.

    Args:
        nodes (list[Node]): Nodos del grafo.
        edges (list[Edge]): Relaciones del grafo.
        max_edges (int): Límite máximo de relaciones.

    Returns:
        str: Bloque Markdown con el código Mermaid.
    """
    if not edges and not nodes:
        return ""

    node_map = {n.id: n for n in nodes}
    edges_vis = edges[:max_edges]

    lineas = ["```mermaid", "graph TD"]
    vistos: set[str] = set()

    for e in edges_vis:
        src_id = _crear_id_mermaid(e.source)
        tgt_id = _crear_id_mermaid(e.target)

        if src_id not in vistos:
            src_node = node_map.get(e.source)
            src_label = _sanear_etiqueta(src_node.title if src_node else e.source)
            lineas.append(f'    {src_id}["{src_label}"]')
            vistos.add(src_id)

        if tgt_id not in vistos:
            tgt_node = node_map.get(e.target)
            tgt_label = _sanear_etiqueta(tgt_node.title if tgt_node else e.target)
            lineas.append(f'    {tgt_id}["{tgt_label}"]')
            vistos.add(tgt_id)

        rel_kind = e.kind or "relacionado"
        lineas.append(f'    {src_id} -->|{rel_kind}| {tgt_id}')

    if not edges_vis:
        base_nodes = [n for n in nodes if n.type == "BASE"][:8]
        for n in base_nodes:
            nid = _crear_id_mermaid(n.id)
            lbl = _sanear_etiqueta(n.title)
            lineas.append(f'    {nid}["{lbl}"]')

    lineas.append("```")
    return "\n".join(lineas)

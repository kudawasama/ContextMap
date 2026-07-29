"""Generador de vault Obsidian desde el grafo de contexto.

Módulo Fachada que coordina los submódulos especializados:
- templates.py: Constantes, slugs, formateo de YAML y Markdown.
- atomic.py: Generación de notas atómicas individuales y MOC simple.
- consolidated.py: Generación de bovedas consolidadas y jerárquicas en árbol.
"""

from __future__ import annotations

import os
from typing import List, Dict, Optional, Set, Tuple

from context_map.core.models import Node, Edge
from context_map.presentation.vault.templates import (
    TYPE_TO_FOLDER,
    STATUS_FOLDERS,
    FOLDER_BY_NAME,
    STANDARD_TAGS_BY_TYPE,
    STANDARD_TAGS_COMMON,
    _slugificar,
    _safe_slug,
    _safe_filename,
    _mermaid_safe_id,
    _normalize_tags,
    _frontmatter,
    _wiki_links,
    _section,
    _node_list,
    _edges_table,
)
from context_map.presentation.vault.atomic import (
    _render_nota,
    _render_moc,
    _detectar_grupo,
    _consolidar_grupo,
    _consolidar_nodos,
    _obtener_carpeta_estado,
    _crear_estructura_carpetas,
    _obtener_ruta_nota,
    _render_conexiones,
    _render_tracking_consolidacion,
)
from context_map.presentation.vault.consolidated import (
    _extract_project_purpose,
    _render_consolidated_vault,
    _render_hierarchical_vault,
)


def _vault_nodes_and_edges(output_dir: str) -> Tuple[List[Node], List[Edge]]:
    """Reconstruye el grafo de nodos y aristas leyendo los archivos de la bóveda."""
    nodes: List[Node] = []
    edges: List[Edge] = []
    seen_nodes: Set[str] = {"00-INDICE"}
    seen_edges: Set[Tuple[str, str, str]] = set()

    def add_node(
        node_id: str,
        title: str,
        kind: str,
        tags: List[str],
        summary: str = "",
        source: str = "vault",
    ) -> Optional[Node]:
        if node_id in seen_nodes:
            return None
        seen_nodes.add(node_id)
        node = Node(
            id=node_id,
            type=kind,
            title=title,
            summary=summary,
            tags=tags,
            source=source,
            status="completado",
        )
        nodes.append(node)
        return node

    def add_edge(src: str, target: str, kind: str = "contains", note: str = "") -> None:
        if not src or not target or src == target:
            return
        edge_key = (src, target, kind)
        if edge_key in seen_edges:
            return
        seen_edges.add(edge_key)
        edges.append(Edge(source=src, target=target, kind=kind, note=note))

    # Nodos principales MOC
    add_node("00-INDICE", "Índice MOC", "BASE", ["moc", "indice"])
    add_node("01-PROPOSITO", "Propósito del Proyecto", "BASE", ["proposito"])
    add_node("02-IDEAS", "Ideas y Características", "IDEA", ["ideas"])
    add_node("03-ESTRUCTURA", "Estructura del Proyecto", "BASE", ["estructura"])
    add_node("04-RIESGOS_Y_COMPLEJIDAD", "Riesgos y Complejidad", "RIESGO", ["riesgo"])
    add_node("05-BACKLOG_Y_TODOS", "Backlog y Tareas Pendientes", "FUTURO", ["backlog"])
    add_node("06-HISTORIAL_Y_DECISIONES", "Historial y Decisiones", "CAMBIO", ["historial"])

    add_edge("00-INDICE", "01-PROPOSITO", "contains")
    add_edge("00-INDICE", "02-IDEAS", "contains")
    add_edge("00-INDICE", "03-ESTRUCTURA", "contains")
    add_edge("00-INDICE", "04-RIESGOS_Y_COMPLEJIDAD", "contains")
    add_edge("00-INDICE", "05-BACKLOG_Y_TODOS", "contains")
    add_edge("00-INDICE", "06-HISTORIAL_Y_DECISIONES", "contains")

    return nodes, edges


def render_obsidian_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
    mode: str = "consolidated",
) -> str:
    """Renderiza la bóveda Obsidian en el modo solicitado.

    Args:
        project_name: Nombre del proyecto.
        nodes: Lista de nodos del mapa de contexto.
        edges: Lista de aristas/relaciones.
        output_dir: Directorio de salida de la bóveda.
        mode: 'consolidated' (por defecto), 'hierarchical' o 'raw' / 'atomic'.

    Returns:
        Ruta del directorio de la bóveda.
    """
    mode_clean = (mode or "consolidated").lower().strip()

    if mode_clean in ("raw", "atomic"):
        _crear_estructura_carpetas(output_dir)
        nodos_proc, tracking = _consolidar_nodos(nodes, project_name=project_name)

        for n in nodos_proc:
            filepath = _obtener_ruta_nota(n, output_dir)
            content = _render_nota(n, nodos_proc, edges)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        moc_content = _render_moc(project_name, nodos_proc, edges)
        with open(os.path.join(output_dir, "00-INDICE.md"), "w", encoding="utf-8") as f:
            f.write(moc_content)

        _render_conexiones(output_dir, nodos_proc, edges)
        if tracking:
            _render_tracking_consolidacion(output_dir, tracking)

        return output_dir

    if mode_clean in ("hierarchical", "tree"):
        return _render_hierarchical_vault(
            project_name=project_name,
            nodes=nodes,
            edges=edges,
            output_dir=output_dir,
        )

    # Modo por defecto: consolidado
    return _render_consolidated_vault(
        project_name=project_name,
        nodes=nodes,
        edges=edges,
        output_dir=output_dir,
    )


def render_active_map(project_name: str, nodes: List[Node], edges: List[Edge]) -> str:
    """Genera una vista textual sintética del mapa de contexto para ACTIVE.md."""
    nodes_by_type: Dict[str, List[Node]] = {}
    for n in nodes:
        nodes_by_type.setdefault(n.type, []).append(n)

    body = ""
    body += _section("Identidad del proyecto", project_name)
    body += _section(
        "Historia causal",
        "\n".join(
            f"- {n.id}: {n.title}"
            for n in (nodes_by_type.get("HITO", []) or nodes[:5])
        ) or "_(pendiente)_",
    )
    body += _section("Mapa mental de contexto", _node_list(nodes))
    body += _section("Conexiones", _edges_table(edges))
    body += _section(
        "Cambios esperados / vivos",
        "\n".join(
            f"- {n.id}: {n.title}" for n in nodes_by_type.get("CAMBIO", [])
        ) or "_(pendiente)_",
    )
    body += _section(
        "Riesgos activos",
        "\n".join(
            f"- {n.id}: {n.title}" for n in nodes_by_type.get("RIESGO", [])
        ) or "_(pendiente)_",
    )
    body += _section(
        "Instrucciones para agentes",
        (
            "1) Usar solo este archivo como memoria oficial del proyecto.\n"
            "2) No reeditar el mapa: usar CLI para agregar nodos/eventos.\n"
            "3) Toda modificación genera snapshot en `.context-map/maps/HISTORY/`."
        ),
    )

    return f"# {project_name} — Context Map\n\n{body}"


def render_mermaid(nodes: List[Node], edges: List[Edge]) -> str:
    """Genera un diagrama Mermaid de las conexiones entre nodos."""
    if not nodes:
        return "```mermaid\ngraph TD\n    empty[Vacío]\n```"

    lines = ["```mermaid", "graph TD"]
    node_ids = {n.id for n in nodes}

    for n in nodes[:50]:
        safe_id = _mermaid_safe_id(n.id)
        short_title = n.title[:30].replace('"', "'")
        iconos = {
            "BASE": "📦", "IDEA": "💡", "RIESGO": "⚠️", "CAMBIO": "🔄",
            "PRUEBA": "🧪", "FUTURO": "🔮", "HITO": "🎯", "CORRECCION": "🔧",
        }
        icon = iconos.get(n.type, "📝")
        lines.append(f'    {safe_id}["{icon} {short_title}"]')

    for e in edges[:100]:
        if e.source in node_ids and e.target in node_ids:
            src_safe = _mermaid_safe_id(e.source)
            tgt_safe = _mermaid_safe_id(e.target)
            label = f"|{e.kind}|" if e.kind else ""
            lines.append(f"    {src_safe} -->{label} {tgt_safe}")

    lines.append("```")
    return "\n".join(lines)

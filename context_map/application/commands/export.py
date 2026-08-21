"""Comando de exportación portable (XML/JSON/Markdown) para chats web de LLMs."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

from context_map.core.models import Node
from context_map.core.normalization.inference import classification_tag
from context_map.core.storage import load_jsonl
from context_map.core.tokenization import contar_tokens_texto
from context_map.presentation.briefs.brief import generar_brief


def exportar_contexto(
    project_path: Path,
    format_type: str = "xml",
    output_file: Path | None = None,
    brief_only: bool = False,
    model_name: str = "gpt-4o",
) -> Path:
    """Exporta todo el contexto del proyecto en un formato portable (XML, JSON o Markdown).

    Args:
        project_path: Ruta raíz del proyecto.
        format_type: Formato de salida ("xml", "json", "markdown").
        output_file: Ruta opcional del archivo de salida.
        brief_only: Si es True, sólo exporta el brief ejecutivo.
        model_name: Nombre del modelo para cálculo de tokens.

    Returns:
        Path del archivo exportado generado.
    """
    fmt = format_type.lower().strip()
    if fmt not in ("xml", "json", "markdown"):
        fmt = "xml"

    # Definir ruta de salida por defecto si no se proporcionó
    if not output_file:
        ext = "xml" if fmt == "xml" else ("json" if fmt == "json" else "md")
        output_file = project_path / f"contextmap_export.{ext}"

    # Cargar nodos y edges del mapa
    nodos: list[Node] = []
    edges: list = []
    graph_file = project_path / ".context-map" / "maps" / "graph.jsonl"
    edges_file = project_path / ".context-map" / "maps" / "edges.jsonl"

    if graph_file.exists():
        records = load_jsonl(str(graph_file))
        nodos = [Node.from_dict(r) for r in records if isinstance(r, dict)]

    if edges_file.exists():
        edges = load_jsonl(str(edges_file))

    if brief_only:
        nodos = []

    # Cargar o generar contenido del brief executive
    brief_file = project_path / ".context-map" / "CONTEXT.md"
    if brief_file.exists():
        brief_content = brief_file.read_text(encoding="utf-8")
    else:
        brief_content = generar_brief(
            project_name=project_path.name,
            nodes=nodos,
            edges=edges,
            project_dir=str(project_path),
        )

    # Calcular estimación de tokens
    tokens_brief = contar_tokens_texto(brief_content, model_name=model_name)

    if fmt == "json":
        data_json = {
            "metadata": {
                "project": project_path.name,
                "format": "json",
                "model_target": model_name,
                "estimated_tokens_brief": tokens_brief,
                "total_nodes": len(nodos),
            },
            "brief": brief_content,
            "nodes": [nodo.to_dict() for nodo in nodos],
        }
        output_file.write_text(json.dumps(data_json, indent=2, ensure_ascii=False), encoding="utf-8")

    elif fmt == "markdown":
        parts: list[str] = [
            f"# ContextMap Export: {project_path.name}",
            f"> **Target Model:** {model_name} | **Brief Tokens:** {tokens_brief} | **Nodes:** {len(nodos)}",
            "",
            "## Executive Brief (CONTEXT.md)",
            "",
            brief_content,
        ]

        if not brief_only and nodos:
            parts.extend(["", "## Project Memory & Nodes", ""])
            for nodo in nodos:
                parts.append(f"### [{nodo.tipo.upper()}] {nodo.titulo}")
                parts.append(f"- **ID:** `{nodo.id}`")
                parts.append(f"- **File:** `{nodo.filepath}`")
                parts.append(f"- **Tag:** `{classification_tag(nodo)}`")
                parts.append(f"- **Details:** {nodo.contenido or 'N/A'}")
                parts.append("")

        output_file.write_text("\n".join(parts), encoding="utf-8")

    else:  # XML format (Repomix compatible)
        root = ET.Element("contextmap", attrib={"project": project_path.name, "target_model": model_name})

        # Encabezado metadata
        meta = ET.SubElement(root, "metadata")
        ET.SubElement(meta, "estimated_tokens_brief").text = str(tokens_brief)
        ET.SubElement(meta, "total_nodes").text = str(len(nodos))

        # Sección Brief
        brief_elem = ET.SubElement(root, "brief")
        brief_elem.text = brief_content

        # Sección Nodos
        if not brief_only and nodos:
            nodes_elem = ET.SubElement(root, "nodes")
            for nodo in nodos:
                n_elem = ET.SubElement(nodes_elem, "node", attrib={"id": nodo.id, "type": nodo.tipo})
                ET.SubElement(n_elem, "title").text = nodo.titulo
                ET.SubElement(n_elem, "filepath").text = str(nodo.filepath)
                ET.SubElement(n_elem, "content").text = nodo.contenido or ""

        # Formatear XML con sangría limpia
        xml_str = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ")
        output_file.write_text(xml_str, encoding="utf-8")

    return output_file

"""Pruebas unitarias para el comando de exportación portable XML/JSON/Markdown."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

from context_map.application.commands.export import exportar_contexto
from context_map.core.models import Node
from context_map.core.storage import append_jsonl


def _sembrar_nodo(tmp_path: Path) -> Node:
    """Crea un vault mínimo en tmp_path con un nodo real persistido en state/graph.jsonl."""
    nodo = Node(
        id="n1",
        type="IDEA",
        title="Idea de prueba",
        summary="Contenido detallado de la idea.",
        evidence=["context_map/foo.py:10"],
        classification="feature",
    )
    graph_file = tmp_path / ".context-map" / "state" / "graph.jsonl"
    append_jsonl(str(graph_file), [nodo.to_dict()])
    return nodo


def test_exportar_contexto_xml(tmp_path: Path) -> None:
    """Verifica que la exportación en XML genere un archivo válido y parseable."""
    out_file = tmp_path / "export_test.xml"
    res = exportar_contexto(project_path=tmp_path, format_type="xml", output_file=out_file)

    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "<contextmap" in content
    assert "<brief>" in content

    # Validar que sea un XML bien formado
    tree = ET.parse(res)
    root = tree.getroot()
    assert root.tag == "contextmap"


def test_exportar_contexto_json(tmp_path: Path) -> None:
    """Verifica que la exportación en JSON genere la estructura esperada."""
    out_file = tmp_path / "export_test.json"
    res = exportar_contexto(project_path=tmp_path, format_type="json", output_file=out_file)

    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert '"metadata"' in content
    assert '"brief"' in content


def test_exportar_contexto_markdown(tmp_path: Path) -> None:
    """Verifica la exportación en formato Markdown."""
    out_file = tmp_path / "export_test.md"
    res = exportar_contexto(project_path=tmp_path, format_type="markdown", output_file=out_file)

    assert res.exists()
    content = res.read_text(encoding="utf-8")
    assert "# ContextMap Export" in content


def test_exportar_contexto_markdown_incluye_nodos_reales(tmp_path: Path) -> None:
    """Un vault con nodos reales debe listarlos en el Markdown, no solo el brief."""
    nodo = _sembrar_nodo(tmp_path)
    out_file = tmp_path / "export_test.md"
    res = exportar_contexto(project_path=tmp_path, format_type="markdown", output_file=out_file)

    content = res.read_text(encoding="utf-8")
    assert "## Project Memory & Nodes" in content
    assert f"[{nodo.type}] {nodo.title}" in content
    assert nodo.evidence[0] in content
    assert nodo.summary in content


def test_exportar_contexto_json_incluye_nodos_reales(tmp_path: Path) -> None:
    """Un vault con nodos reales debe serializarlos en el JSON exportado."""
    nodo = _sembrar_nodo(tmp_path)
    out_file = tmp_path / "export_test.json"
    res = exportar_contexto(project_path=tmp_path, format_type="json", output_file=out_file)

    data = json.loads(res.read_text(encoding="utf-8"))
    assert data["metadata"]["total_nodes"] == 1
    assert data["nodes"][0]["title"] == nodo.title
    assert data["nodes"][0]["type"] == nodo.type


def test_exportar_contexto_xml_incluye_nodos_reales(tmp_path: Path) -> None:
    """Un vault con nodos reales debe listarlos como <node> en el XML exportado."""
    nodo = _sembrar_nodo(tmp_path)
    out_file = tmp_path / "export_test.xml"
    res = exportar_contexto(project_path=tmp_path, format_type="xml", output_file=out_file)

    root = ET.parse(res).getroot()
    node_elem = root.find("./nodes/node")
    assert node_elem is not None
    assert node_elem.attrib["type"] == nodo.type
    assert node_elem.find("title").text == nodo.title

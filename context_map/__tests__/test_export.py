"""Pruebas unitarias para el comando de exportación portable XML/JSON/Markdown."""

import xml.etree.ElementTree as ET
from pathlib import Path

from context_map.application.commands.export import exportar_contexto


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

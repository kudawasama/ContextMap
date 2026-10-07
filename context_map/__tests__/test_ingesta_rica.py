"""Ingesta rica (F12): HTML local, alias de video y captura por stdin."""

from __future__ import annotations

import io
import zipfile
from types import SimpleNamespace

from context_map.application.cli.parser import create_parser
from context_map.application.commands.inbox import _texto_de_entrada
from context_map.application.commands.ingest import EXTENSIONES_SOPORTADAS
from context_map.domain.ingestion import extraer_texto


def test_extraer_texto_de_html_local(tmp_path) -> None:
    """Una página .html guardada se convierte a Markdown legible."""
    archivo = tmp_path / "articulo.html"
    archivo.write_text(
        "<html><head><title>Mi Artículo</title></head><body>"
        "<article><h1>Mi Artículo</h1><p>Contenido importante del artículo.</p></article>"
        "</body></html>",
        encoding="utf-8",
    )

    texto, tipo = extraer_texto(str(archivo))

    assert tipo == "html"
    assert "Contenido importante del artículo." in texto


def test_html_esta_en_extensiones_soportadas() -> None:
    """El comando ingest reconoce .html/.htm en lote."""
    assert ".html" in EXTENSIONES_SOPORTADAS
    assert ".htm" in EXTENSIONES_SOPORTADAS


def test_extraer_texto_de_docx(tmp_path) -> None:
    """Un .docx se lee con la librería estándar (ZIP + word/document.xml)."""
    archivo = tmp_path / "informe.docx"
    ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    xml = (
        f'<w:document xmlns:w="{ns}"><w:body>'
        "<w:p><w:r><w:t>Primer párrafo del informe.</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>Segundo párrafo con detalle.</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(archivo, "w") as zf:
        zf.writestr("word/document.xml", xml)

    texto, tipo = extraer_texto(str(archivo))

    assert tipo == "docx"
    assert "Primer párrafo del informe." in texto
    assert "Segundo párrafo con detalle." in texto
    assert ".docx" in EXTENSIONES_SOPORTADAS


def test_docx_invalido_da_error_claro(tmp_path) -> None:
    """Un .docx corrupto falla con un ValueError descriptivo (no un traceback crudo)."""
    archivo = tmp_path / "roto.docx"
    archivo.write_bytes(b"esto no es un zip")
    import pytest

    with pytest.raises(ValueError, match="No se pudo leer el .docx"):
        extraer_texto(str(archivo))


def test_parser_acepta_video_generico() -> None:
    """`ingest --video` es un alias genérico de la captura de transcripción."""
    args = create_parser().parse_args(["ingest", "--video", "https://ejemplo.com/v/1"])
    assert args.video == "https://ejemplo.com/v/1"


def test_inbox_add_lee_de_stdin(monkeypatch) -> None:
    """`inbox add -` toma el texto de stdin (para bookmarklets/pipes)."""
    monkeypatch.setattr("sys.stdin", io.StringIO("Texto capturado desde el navegador"))

    args = SimpleNamespace(texto="-", stdin=False)
    assert _texto_de_entrada(args) == "Texto capturado desde el navegador"

    args_stdin = SimpleNamespace(texto="", stdin=True)
    monkeypatch.setattr("sys.stdin", io.StringIO("Otra captura"))
    assert _texto_de_entrada(args_stdin) == "Otra captura"

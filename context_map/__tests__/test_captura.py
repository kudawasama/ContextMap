"""Tests de captura de fuentes del mundo CONOCIMIENTO (Web Clipper + YouTube)."""

from __future__ import annotations

import os

from context_map.domain.knowledge import captura as cap
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM sembrado y devuelve su ruta."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def test_vtt_a_texto_limpia_timestamps():
    """El VTT se convierte en texto continuo sin timestamps ni duplicados."""
    vtt = (
        "WEBVTT\n\n"
        "Kind: captions\nLanguage: es\n\n"
        "00:00:01.000 --> 00:00:04.000\n"
        "<c>Hola mundo</c>\n\n"
        "00:00:04.000 --> 00:00:08.000\n"
        "<c>esto es</c>\n\n"
        "00:00:04.000 --> 00:00:08.000\n"
        "<c>esto es</c>\n\n"
        "00:00:08.000 --> 00:00:10.000\n"
        "<c>una prueba</c>\n"
    )
    texto = cap.vtt_a_texto(vtt)
    assert texto == "Hola mundo esto es una prueba"


def test_html_a_markdown():
    """El HTML se convierte en (título, markdown) con énfasis, enlaces y listas."""
    html = (
        "<html><head><title>Mi Artículo de Prueba</title></head><body>"
        "<h1>Introducción</h1>"
        "<p>Este es un <strong>texto</strong> con un <a href=\"https://x.com\">enlace</a>.</p>"
        "<ul><li>Uno</li><li>Dos</li></ul>"
        "</body></html>"
    )
    titulo, md = cap.html_a_markdown(html)
    assert titulo == "Mi Artículo de Prueba"
    assert "# Introducción" in md
    assert "**texto**" in md
    assert "[enlace](https://x.com)" in md
    assert "- Uno" in md and "- Dos" in md


def test_capturar_a_inbox(tmp_path):
    """La captura por defecto entra al inbox (namespace knowledge)."""
    vdir = _vault(tmp_path)
    res = cap.capturar(vdir, "Contenido capturado de la web", "Mi captura", "https://x.com")
    assert res["destino"] == "inbox"
    assert os.path.exists(res["ruta"])
    with open(res["ruta"], encoding="utf-8") as f:
        contenido = f.read()
    assert "namespace: knowledge" in contenido
    assert "Mi captura" in contenido


def test_capturar_a_wiki(tmp_path):
    """Con destino wiki, la captura crea una página de resumen con entidades."""
    vdir = _vault(tmp_path)
    res = cap.capturar(vdir, "Resumen del artículo", "Artículo X", "https://x.com",
                       destino="wiki", entidades="RAG")
    assert res["destino"] == "wiki"
    assert os.path.exists(res["ruta"])
    with open(res["ruta"], encoding="utf-8") as f:
        contenido = f.read()
    assert "namespace: knowledge" in contenido
    assert "Artículo X" in contenido
    assert "RAG" in contenido


def test_captura_destino_desconocido(tmp_path):
    """Un destino inválido lanza ValueError."""
    vdir = _vault(tmp_path)
    try:
        cap.capturar(vdir, "x", "y", "z", destino="raiz")
    except ValueError:
        return
    raise AssertionError("Debe lanzar ValueError para destino desconocido")

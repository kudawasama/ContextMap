"""Wiki 2.0 (F9): síntesis extractiva local, contradicciones y MOC."""

from __future__ import annotations

import os

from context_map.domain.knowledge import wiki as kb
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM sembrado."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def test_sintetizar_responde_con_citas(tmp_path) -> None:
    """La síntesis extractiva encadena frases afines y cita cada fuente."""
    vdir = _vault(tmp_path)
    kb.ingresar(
        vdir,
        "Sistemas RAG",
        "RAG (retrieval augmented generation) combina recuperación de documentos "
        "con generación de texto natural. "
        "Los embeddings representan el significado en vectores densos.",
        entidades="RAG, Embeddings",
    )
    kb.ingresar(vdir, "Cocina", "Recetas de pastas italianas tradicionales.")

    res = kb.sintetizar(vdir, "¿cómo funciona retrieval augmented generation?", limite=5)

    assert res["respuesta"], "Debe producir una respuesta extractiva"
    assert "[1]" in res["respuesta"], "Debe citar la fuente con [1]"
    assert res["fuentes"], "Debe listar fuentes"
    assert "[[" in res["fuentes"][0]["cita"]


def test_sintetizar_sin_match_devuelve_vacio(tmp_path) -> None:
    """Sin solape no inventa: respuesta vacía y sin fuentes."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Cocina", "Recetas de pastas italianas tradicionales.")
    res = kb.sintetizar(vdir, "kubernetes con certificados TLS")
    assert res["respuesta"] == ""
    assert res["fuentes"] == []


def test_sintetizar_es_determinista(tmp_path) -> None:
    """Dos ejecuciones idénticas producen la misma respuesta (local, sin LLM)."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "RAG", "RAG combina recuperación de documentos con generación de texto.")
    a = kb.sintetizar(vdir, "recuperación de documentos")
    b = kb.sintetizar(vdir, "recuperación de documentos")
    assert a["respuesta"] == b["respuesta"]


def test_lint_detecta_contradiccion(tmp_path) -> None:
    """Dos páginas que afirman y niegan lo mismo producen un aviso (no un error)."""
    vdir = _vault(tmp_path)
    kb.ingresar(
        vdir, "PARA afirmado",
        "PARA organiza por accion priorizando los proyectos activos.",
    )
    kb.ingresar(
        vdir, "PARA negado",
        "PARA no organiza por accion priorizando los proyectos activos.",
    )

    reporte = kb.lint(vdir)

    assert reporte.ok, "Una contradicción es un aviso, no un error de estructura"
    assert any("CONTRADICCIÓN" in a for a in reporte.avisos), reporte.avisos


def test_moc_agrupa_conceptos_y_se_enlaza(tmp_path) -> None:
    """El MOC agrupa cada concepto con sus fuentes y cuelga del índice 05-WIKI."""
    vdir = _vault(tmp_path)
    kb.ingresar(
        vdir, "Sistemas RAG",
        "RAG combina recuperación de documentos con generación de texto.",
        entidades="RAG",
    )

    ruta_moc = os.path.join(kb.ruta_wiki(vdir), "MOC.md")
    assert os.path.exists(ruta_moc), "La ingesta regenera el MOC"
    with open(ruta_moc, encoding="utf-8") as f:
        contenido = f.read()
    assert "namespace: knowledge" in contenido
    assert "### 🔖 RAG" in contenido
    assert "Sistemas RAG" in contenido, "El concepto debe listar su fuente"

    # El MOC cuelga del índice de la wiki (padre único).
    with open(os.path.join(kb.ruta_wiki(vdir), "05-WIKI.md"), encoding="utf-8") as f:
        index = f.read()
    assert "/05-WIKI/MOC" in index

    # Y no rompe el lint.
    assert kb.lint(vdir).ok, kb.lint(vdir).errores

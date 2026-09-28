"""Tests de la LLM Wiki (patrón Karpathy) del mundo conocimiento (namespace knowledge)."""

from __future__ import annotations

import os

from context_map.domain.knowledge import wiki as kb
from context_map.domain.knowledge.indices import slug
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM sembrado y devuelve su ruta."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def _leer(ruta: str) -> str:
    """Lee un archivo con context manager."""
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def test_ingresar_crea_resumen_indices_y_entidades(tmp_path):
    """La ingesta crea la página, la indexa, registra el entry log y crea entidades."""
    vdir = _vault(tmp_path)
    res = kb.ingresar(
        vdir,
        "Retrieval Augmented Generation",
        "RAG combina recuperación de documentos con generación de texto.",
        fuente="https://ejemplo.com/rag",
        entidades="RAG, Vectores",
    )
    assert os.path.exists(res["ruta"])
    contenido = _leer(res["ruta"])
    assert "namespace: knowledge" in contenido
    assert "preserve: true" in contenido
    assert "Retrieval Augmented Generation" in contenido

    idx_res = _leer(os.path.join(kb.ruta_resumenes(vdir), "resumenes.md"))
    assert "Retrieval Augmented Generation" in idx_res, "Índice de resúmenes debe enlazar la página"

    log = _leer(os.path.join(kb.ruta_wiki(vdir), "entry-log.md"))
    assert "Retrieval Augmented Generation" in log, "El entry log debe registrar la ingesta"

    for ent in ("RAG", "Vectores"):
        assert os.path.exists(os.path.join(kb.ruta_entidades(vdir), f"{slug(ent)}.md")), (
            f"Falta la página de la entidad {ent}"
        )
    idx_ent = _leer(os.path.join(kb.ruta_entidades(vdir), "entidades.md"))
    assert "RAG" in idx_ent


def test_ingresar_es_idempotente_en_entidades(tmp_path):
    """Una entidad ya existente no se duplica y acumula páginas relacionadas."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Resumen A", "Contenido A sobre RAG", entidades="RAG")
    kb.ingresar(vdir, "Resumen B", "Contenido B sobre RAG", entidades="RAG")
    ruta_ent = os.path.join(kb.ruta_entidades(vdir), f"{slug('RAG')}.md")
    contenido = _leer(ruta_ent)
    assert contenido.count("Páginas relacionadas") == 1
    assert "Resumen A" in contenido and "Resumen B" in contenido


def test_consultar_ranking_con_citas(tmp_path):
    """Consultar devuelve las páginas más afines con su cita (wikilink) y fragmento."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Sistemas RAG", "Guía sobre retrieval augmented generation y embeddings", entidades="RAG")
    kb.ingresar(vdir, "Pomodoro", "Técnica de productividad con intervalos de trabajo")

    resultados = kb.consultar(vdir, "¿cómo funciona el retrieval aumentado?", limite=5)
    assert resultados, "Debe encontrar la página de RAG"
    mejor = resultados[0]
    assert mejor["titulo"] == "Sistemas RAG"
    assert "[[" in mejor["cita"], "La respuesta debe poder citar la página"
    assert "excerpt" in mejor and mejor["excerpt"]


def test_consultar_sin_match_devuelve_vacio(tmp_path):
    """Una consulta sin solape no devuelve resultados en lugar de basura."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Cocina", "Recetas de pastas italianas")
    assert kb.consultar(vdir, "autenticación de kubernetes con certificados") == []


def test_lint_detecta_concepto_sin_pagina(tmp_path):
    """El lint marca un concepto mencionado que no tiene página propia."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Tema", "Contenido de prueba", entidades="EntidadReal")

    resumen = kb.consultar(vdir, "tema", 1)[0]["ruta"]
    with open(resumen, encoding="utf-8") as f:
        txt = f.read()
    txt += "\nVer [[90-CONOCIMIENTO/05-WIKI/entidades/Fantasma|Fantasma]]\n"
    with open(resumen, "w", encoding="utf-8") as f:
        f.write(txt)

    reporte = kb.lint(vdir)
    assert not reporte.ok
    assert any("CONCEPTO SIN PÁGINA" in e for e in reporte.errores)


def test_lint_limpio_cuando_esta_sano(tmp_path):
    """Una wiki recién ingerida no tiene errores de lint."""
    vdir = _vault(tmp_path)
    kb.ingresar(vdir, "Tema sano", "Contenido consistente", entidades="RAG")
    reporte = kb.lint(vdir)
    assert reporte.ok, reporte.errores

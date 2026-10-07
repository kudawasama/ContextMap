"""Puente knowledge → agentes (F8): el Second Brain llega al brief.

El mundo PKM (`90-CONOCIMIENTO/`) es una isla independiente del código. Estos
tests garantizan que sus páginas relevantes entren en el **bloque dinámico** del
brief (después del boundary de prompt-cache) y que su ausencia no rompa nada.
"""

from __future__ import annotations

import os
from pathlib import Path

from context_map.presentation.briefs.brief import generar_brief
from context_map.presentation.briefs.extractors import panorama_conocimiento

BOUNDARY = "<!-- PROMPT_CACHE_BOUNDARY: INVARIANT_PREFIX -->"


def _pagina(carpeta: Path, nombre: str, titulo: str, tipo: str) -> None:
    """Crea una página de la wiki con frontmatter ``title``."""
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / nombre).write_text(
        f'---\ntype: {tipo}\nnamespace: knowledge\npreserve: true\ntitle: "{titulo}"\n---\n\n'
        f"# {titulo}\n\nContenido de {titulo}.\n",
        encoding="utf-8",
    )


def _proyecto_pkm(tmp_path: Path) -> Path:
    """Siembra un proyecto con una wiki mínima (resumen + entidad) y un inbox."""
    wiki = tmp_path / ".context-map" / "vault-MiProyecto" / "90-CONOCIMIENTO" / "05-WIKI"
    _pagina(wiki / "resumenes", "curso-obsidian.md", "Curso de Obsidian", "resumen")
    _pagina(wiki / "entidades", "para.md", "PARA", "entidad")
    (wiki / "resumenes" / "resumenes.md").write_text("índice", encoding="utf-8")

    inbox = tmp_path / ".context-map" / "vault-MiProyecto" / "90-CONOCIMIENTO" / "00-INBOX"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "00-INBOX.md").write_text("índice", encoding="utf-8")
    (inbox / "nota-cruda.md").write_text("# Nota cruda", encoding="utf-8")
    return tmp_path


def test_panorama_conocimiento_lista_paginas(tmp_path: Path) -> None:
    """El panorama lista resúmenes primero, cuenta el total y el inbox."""
    ruta = _proyecto_pkm(tmp_path)

    panorama = panorama_conocimiento("MiProyecto", str(ruta))

    assert panorama["total"] == 2
    assert len(panorama["paginas"]) == 2
    assert panorama["paginas"][0]["tipo"] == "resumen"
    assert panorama["paginas"][0]["titulo"] == "Curso de Obsidian"
    assert "90-CONOCIMIENTO/05-WIKI/resumenes/curso-obsidian" in panorama["paginas"][0]["cita"]
    assert panorama["inbox"] == 1


def test_brief_incluye_conocimiento_en_bloque_dinamico(tmp_path: Path) -> None:
    """El conocimiento entra en el brief, DESPUÉS del boundary de prompt-cache."""
    ruta = _proyecto_pkm(tmp_path)
    salida = str(tmp_path / "CONTEXT.md")

    contenido = generar_brief(
        project_name="MiProyecto",
        nodes=[],
        edges=[],
        readiness_score=90,
        output_path=salida,
        project_dir=str(ruta),
    )

    assert "## 🧠 Conocimiento Relevante (Second Brain)" in contenido
    assert "Curso de Obsidian" in contenido
    assert "PARA" in contenido
    assert "Inbox pendiente de clasificar" in contenido
    # Debe vivir en el bloque dinámico para no romper el caché del prefijo.
    assert contenido.index("Conocimiento Relevante") > contenido.index(BOUNDARY)


def test_brief_sin_conocimiento_no_rompe(tmp_path: Path) -> None:
    """Sin wiki, la sección se renderiza con la guía de captura y sin errores."""
    salida = str(tmp_path / "CONTEXT.md")

    contenido = generar_brief(
        project_name="ProyectoVacio",
        nodes=[],
        edges=[],
        readiness_score=50,
        output_path=salida,
        project_dir=str(tmp_path),
    )

    assert "## 🧠 Conocimiento Relevante (Second Brain)" in contenido
    assert "Sin páginas todavía" in contenido
    assert os.path.exists(salida)

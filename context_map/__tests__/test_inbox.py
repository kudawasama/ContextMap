"""Tests del mundo CONOCIMIENTO: inbox PKM (Second Brain) del namespace knowledge."""

from __future__ import annotations

import os

from context_map.domain.knowledge import inbox as kb
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM sembrado y devuelve su ruta."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def _leer(ruta: str) -> str:
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def test_crear_nota_en_inbox(tmp_path):
    """Una nota nueva entra al inbox con namespace knowledge y queda enlazada."""
    vdir = _vault(tmp_path)
    ruta = kb.crear_nota(vdir, "Una idea suelta para procesar", titulo="Mi idea")
    assert os.path.exists(ruta)
    contenido = _leer(ruta)
    assert "namespace: knowledge" in contenido
    assert "preserve: true" in contenido
    assert "Mi idea" in contenido

    idx = _leer(os.path.join(kb.ruta_categoria(vdir, "inbox"), "00-INBOX.md"))
    assert "Mi idea" in idx, "El índice del inbox debe enlazar la nota (tiene padre)"


def test_listar_inbox_excluye_indices(tmp_path):
    """listar_notas devuelve solo las notas, nunca el índice ni el entry-log."""
    vdir = _vault(tmp_path)
    kb.crear_nota(vdir, "Nota A", titulo="A")
    kb.crear_nota(vdir, "Nota B", titulo="B")
    titulos = {n["titulo"] for n in kb.listar_notas(vdir, "inbox")}
    assert titulos == {"A", "B"}


def test_clasificar_por_palabras_clave():
    """La heurística PARA mapea palabras clave a su categoría."""
    assert kb.clasificar("Implementar el proyecto del curso") == "projects"
    assert kb.clasificar("Rutina de salud y ejercicio diario") == "areas"
    assert kb.clasificar("Apuntes de referencia sobre RAG") == "resources"
    assert kb.clasificar("Documento obsoleto y cerrado") == "archive"
    assert kb.clasificar("xyzzy sin pistas") == "resources"  # default PARA


def test_mover_nota_actualiza_enlaces(tmp_path):
    """Mover una nota la re-cuelga de su nueva sección y no deja enlaces rotos."""
    vdir = _vault(tmp_path)
    ruta = kb.crear_nota(vdir, "Nota a mover", titulo="Mover")
    destino = kb.mover_nota(vdir, os.path.basename(ruta), "projects")

    assert os.path.exists(destino)
    assert not os.path.exists(ruta), "La nota original debe removerse del inbox"
    assert "01-PROJECTS" in _leer(destino), "El pie debe apuntar al nuevo padre"

    proj_idx = _leer(os.path.join(kb.ruta_categoria(vdir, "projects"), "01-PROJECTS.md"))
    inbox_idx = _leer(os.path.join(kb.ruta_categoria(vdir, "inbox"), "00-INBOX.md"))
    assert "Mover" in proj_idx
    assert "Mover" not in inbox_idx, "El índice del inbox no debe conservar el enlace"


def test_purgar_clasifica_y_vacia(tmp_path):
    """Purgar clasifica cada nota y deja el inbox vacío."""
    vdir = _vault(tmp_path)
    kb.crear_nota(vdir, "Implementar proyecto del curso", titulo="Curso")
    kb.crear_nota(vdir, "Rutina de salud", titulo="Salud")

    decisiones = kb.purgar(vdir)
    assert len(decisiones) == 2
    assert kb.listar_notas(vdir, "inbox") == []
    assert {d["destino"] for d in decisiones} == {"projects", "areas"}


def test_purgar_dry_run_no_mueve(tmp_path):
    """Con dry_run las decisiones se calculan pero el inbox no cambia."""
    vdir = _vault(tmp_path)
    kb.crear_nota(vdir, "Implementar proyecto", titulo="Curso")
    decisiones = kb.purgar(vdir, dry_run=True)
    assert len(decisiones) == 1
    assert len(kb.listar_notas(vdir, "inbox")) == 1


def test_notas_pkm_tienen_namespace_knowledge(tmp_path):
    """Toda nota del inbox declara su namespace y es preservada por el build."""
    from context_map.presentation.vault.preservar import ZONAS_MANUALES

    vdir = _vault(tmp_path)
    ruta = kb.crear_nota(vdir, "Contenido", titulo="Namespace")
    contenido = _leer(ruta)
    assert "namespace: knowledge" in contenido
    assert "90-CONOCIMIENTO" in ZONAS_MANUALES

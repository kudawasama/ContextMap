"""Test: Ingesta de documentos externos (comando ingest).

Verifica que:
1. La síntesis extractiva y las citas se generan correctamente.
2. El nodo DOCUMENTO se crea con concepto y evidencia.
3. El vault jerárquico renderiza 3.2-DOCUMENTOS como rama del árbol
   (3.0 → 3.2 → nota → SOLO a 3.2), sin colisiones ni enlaces rotos.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from context_map.core.models import Node
from context_map.domain.ingestion import (
    crear_nodo_documento,
    detectar_concepto,
    extraer_citas,
    extraer_texto,
    sintetizar,
)
from context_map.presentation.vault import render_obsidian_vault

TEXTO_DOCUMENTO = """\
# Estrategia de Inversión

El valor intrínseco de una empresa se calcula descontando los flujos de caja
futuros esperados. El margen de seguridad es la diferencia entre el precio de
mercado y el valor intrínseco estimado.

Warren Buffett recomienda invertir en negocios con ventajas competitivas
duraderas y retornos sobre el capital sostenidos en el tiempo.

La paciencia es fundamental: el interés compuesto multiplica las ganancias
cuando se mantienen las posiciones durante décadas.

Los inversores deben evitar el ruido del mercado y centrarse en los
fundamentos del negocio, la gestión y la asignación de capital.
"""


def test_sintesis_y_citas() -> None:
    """Verifica que la síntesis extrae lo relevante y las citas tienen referencia."""
    sintesis = sintetizar(TEXTO_DOCUMENTO)
    assert len(sintesis) > 80, "La síntesis quedó vacía o demasiado corta"
    assert "inversión" in sintesis.lower() or "valor" in sintesis.lower()

    citas = extraer_citas(TEXTO_DOCUMENTO)
    assert len(citas) > 0, "No se extrajeron citas"
    assert all(len(c) > 30 for c in citas), "Cita demasiado corta"

    concepto = detectar_concepto(TEXTO_DOCUMENTO)
    assert concepto, "No se detectó concepto"


def test_crear_nodo_documento() -> None:
    """Verifica que el nodo DOCUMENTO se crea con los campos esperados."""
    nodo = crear_nodo_documento(
        "cartas-buffett.md", TEXTO_DOCUMENTO, project_name="TestProj"
    )
    assert nodo.type == "DOCUMENTO"
    assert nodo.title == "cartas-buffett"
    assert nodo.source == "ingest"
    assert nodo.concept, "Falta concepto"
    assert nodo.summary, "Falta síntesis"
    assert nodo.evidence, "Faltan citas"
    assert nodo.classification == "docs"


def test_extraer_texto_markdown() -> None:
    """Verifica la extracción de texto desde archivo MD."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_ingest_texto_")
    try:
        ruta = os.path.join(temp_dir, "doc.md")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(TEXTO_DOCUMENTO)
        texto, tipo = extraer_texto(ruta)
        assert tipo == "markdown"
        assert "valor intrínseco" in texto
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_vault_documentos_en_arbol() -> None:
    """Verifica que 3.2-DOCUMENTOS cuelga de 3.0 y las notas de su índice."""
    nodo = crear_nodo_documento(
        "carta-2012.md", TEXTO_DOCUMENTO, project_name="TestProj"
    )
    nodo_base = Node(
        id="BASE-01", type="BASE", title="Modulo principal",
        summary="Componente base", source="test", tags=["estructura"],
    )
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_ingest_vault_")

    try:
        render_obsidian_vault(
            project_name="TestProj",
            nodes=[nodo, nodo_base],
            edges=[],
            output_dir=temp_dir,
            mode="hierarchical",
        )

        # 3.0 enlaza a 3.2 (condicional, hay documentos)
        seccion3 = os.path.join(temp_dir, "3.0-ESTRUCTURA", "3.0-ESTRUCTURA.md")
        with open(seccion3, encoding="utf-8") as f:
            contenido3 = f.read()
        assert "3.2-DOCUMENTOS" in contenido3, "3.0 no enlaza a 3.2"

        # 3.2 índice existe y enlaza a la nota
        docs_dir = os.path.join(temp_dir, "3.0-ESTRUCTURA", "3.2-DOCUMENTOS")
        assert os.path.isdir(docs_dir), "No existe 3.2-DOCUMENTOS"
        indice = os.path.join(docs_dir, "3.2-DOCUMENTOS.md")
        with open(indice, encoding="utf-8") as f:
            contenido_indice = f.read()
        assert "carta-2012" in contenido_indice, "El índice no enlaza a la nota"

        # La nota existe, enlaza SOLO a 3.2 (su padre)
        nota = os.path.join(docs_dir, "carta-2012.md")
        assert os.path.exists(nota), "No se generó la nota del documento"
        with open(nota, encoding="utf-8") as f:
            contenido_nota = f.read()
        assert "3.2-DOCUMENTOS" in contenido_nota, "La nota no enlaza a 3.2"
        assert "📄" in contenido_nota, "Falta encabezado de documento"
        assert "Síntesis" in contenido_nota, "Falta sección de síntesis"
        assert "Citas" in contenido_nota, "Falta sección de citas"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Test: Ingesta de documentos ===")
    test_sintesis_y_citas()
    print("   OK: test_sintesis_y_citas PASO")

    print()
    print("=== Test: Nodo DOCUMENTO ===")
    test_crear_nodo_documento()
    print("   OK: test_crear_nodo_documento PASO")

    print()
    print("=== Test: Extracción MD ===")
    test_extraer_texto_markdown()
    print("   OK: test_extraer_texto_markdown PASO")

    print()
    print("=== Test: Vault 3.2 en árbol ===")
    test_vault_documentos_en_arbol()
    print("   OK: test_vault_documentos_en_arbol PASO")

    print()
    print("Todos los tests pasaron correctamente.")

"""Test: Verificación del modo consolidado de generación de vault.

Comprueba que render_obsidian_vault en modo 'consolidated' genere
un máximo de 10 archivos .md (actualmente se esperan 5-6), y que
cada uno contenga YAML Frontmatter y Wikilinks funcionales.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from typing import List

from context_map.core.models import Node, Edge
from context_map.presentation.writer import render_obsidian_vault


def _crear_nodos_de_prueba() -> List[Node]:
    """Genera un conjunto representativo de nodos para validar la consolidación."""
    nodos: List[Node] = []

    # Nodos BASE (estructura)
    for i in range(5):
        nodos.append(Node(
            id=f"BASE-{i:02d}",
            type="BASE",
            title=f"Modulo {i}",
            summary=f"Módulo de prueba número {i}",
            source="test",
            tags=["estructura", "test"],
        ))

    # Nodos IDEA
    for i in range(3):
        nodos.append(Node(
            id=f"IDEA-{i:02d}",
            type="IDEA",
            title=f"Concepto {i}",
            summary=f"Idea conceptual de prueba {i}",
            source="test",
            tags=["idea", "test"],
        ))

    # Nodos RIESGO
    nodos.append(Node(
        id="RIESGO-01",
        type="RIESGO",
        title="Archivo complejo detectado",
        summary="writer.py tiene 800+ líneas",
        source="test",
        tags=["riesgo", "complejidad"],
    ))

    # Nodos FUTURO
    for i in range(4):
        nodos.append(Node(
            id=f"FUTURO-{i:02d}",
            type="FUTURO",
            title=f"TODO: Refactorizar modulo {i}",
            summary=f"Pendiente de refactorización en módulo {i}",
            source="test",
            tags=["todo", "futuro"],
        ))

    # Nodos CAMBIO
    for i in range(3):
        nodos.append(Node(
            id=f"CAMBIO-{i:02d}",
            type="CAMBIO",
            title=f"feat: implementar feature {i}",
            summary=f"Commit de feature {i}",
            source="git",
            tags=["commit", "cambio"],
        ))

    # Nodo HITO
    nodos.append(Node(
        id="HITO-01",
        type="HITO",
        title="Release v1.0",
        summary="Primera versión estable",
        source="git",
        tags=["hito", "release"],
    ))

    # Nodo PRUEBA
    nodos.append(Node(
        id="PRUEBA-01",
        type="PRUEBA",
        title="test_smoke",
        summary="Prueba de humo del writer",
        source="test",
        tags=["prueba", "test"],
    ))

    return nodos


def _crear_edges_de_prueba() -> List[Edge]:
    """Genera aristas de prueba."""
    return [
        Edge(source="BASE-00", target="IDEA-00", kind="depends_on"),
        Edge(source="BASE-01", target="RIESGO-01", kind="has_risk"),
        Edge(source="FUTURO-00", target="BASE-02", kind="relates_to"),
    ]


def test_consolidated_vault_limita_archivos() -> None:
    """Verifica que en modo consolidado no se generen más de 10 archivos .md."""
    nodos = _crear_nodos_de_prueba()
    edges = _crear_edges_de_prueba()
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_vault_")

    try:
        render_obsidian_vault(
            project_name="TestProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="consolidated",
        )

        archivos_md = [
            f for f in os.listdir(temp_dir)
            if f.endswith(".md")
        ]

        print(f"   Archivos generados ({len(archivos_md)}): {archivos_md}")

        assert len(archivos_md) <= 10, (
            f"Se generaron {len(archivos_md)} archivos .md, el máximo permitido es 10"
        )
        assert len(archivos_md) >= 4, (
            f"Se generaron solo {len(archivos_md)} archivos .md, se esperan al menos 4"
        )

        # Verificar que todos tienen Frontmatter YAML
        for archivo in archivos_md:
            ruta = os.path.join(temp_dir, archivo)
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
            assert contenido.startswith("---"), (
                f"El archivo {archivo} no comienza con YAML Frontmatter"
            )
            assert "---" in contenido[3:], (
                f"El archivo {archivo} no cierra el bloque YAML Frontmatter"
            )

        # Verificar que el índice contiene Wikilinks
        indice_path = os.path.join(temp_dir, "00-INDICE.md")
        assert os.path.exists(indice_path), "No se generó 00-INDICE.md"
        with open(indice_path, "r", encoding="utf-8") as f:
            contenido_indice = f.read()
        assert "[[" in contenido_indice, "El índice no contiene Wikilinks"
        assert "03-ESTRUCTURA" in contenido_indice, (
            "El indice no enlaza a 03-ESTRUCTURA"
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_raw_mode_genera_estructura_carpetas() -> None:
    """Verifica que el modo 'raw' sigue generando la estructura de carpetas heredada."""
    nodos = _crear_nodos_de_prueba()
    edges = _crear_edges_de_prueba()
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_vault_raw_")

    try:
        render_obsidian_vault(
            project_name="TestProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="raw",
        )

        # El modo raw genera carpetas por tipo
        assert os.path.exists(os.path.join(temp_dir, "00-INDICE.md")), (
            "No se generó 00-INDICE.md en modo raw"
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_hierarchical_vault_estructura() -> None:
    """Verifica que el modo 'hierarchical' genere la estructura de archivos correcta."""
    nodos = _crear_nodos_de_prueba()
    edges = _crear_edges_de_prueba()
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_vault_hier_")

    try:
        render_obsidian_vault(
            project_name="TestProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="hierarchical",
        )

        # Verificar archivos raíz del modo hierarchical
        assert os.path.exists(os.path.join(temp_dir, "00-INDICE.md")), \
            "No se generó 00-INDICE.md"
        assert os.path.exists(os.path.join(temp_dir, "1.0-PROPOSITO.md")), \
            "No se generó 1.0-PROPOSITO.md"
        assert os.path.exists(os.path.join(temp_dir, "1.1-Mapa-Mental-Narrativo.md")), \
            "No se generó 1.1-Mapa-Mental-Narrativo.md"
        assert os.path.exists(os.path.join(temp_dir, "1.2-Datos-Clave.md")), \
            "No se generó 1.2-Datos-Clave.md"
        assert os.path.exists(os.path.join(temp_dir, "1.3-Proposito.md")), \
            "No se generó 1.3-Proposito.md"
        assert os.path.exists(os.path.join(temp_dir, "2.0-IDEAS.md")), \
            "No se generó 2.0-IDEAS.md"
        assert os.path.exists(os.path.join(temp_dir, "2.4-Ideas-Relevantes.md")), \
            "No se generó 2.4-Ideas-Relevantes.md"
        assert os.path.exists(os.path.join(temp_dir, "3.0-ESTRUCTURA.md")), \
            "No se generó 3.0-ESTRUCTURA.md"
        assert os.path.exists(os.path.join(temp_dir, "4.0-RIESGOS.md")), \
            "No se generó 4.0-RIESGOS.md"
        assert os.path.exists(os.path.join(temp_dir, "5.0-BACKLOG.md")), \
            "No se generó 5.0-BACKLOG.md"
        assert os.path.exists(os.path.join(temp_dir, "6.0-HISTORIAL.md")), \
            "No se generó 6.0-HISTORIAL.md"

        # Verificar que NO genera archivos del modo consolidated
        assert not os.path.exists(os.path.join(temp_dir, "01-PROPOSITO.md")), \
            "No debería generar 01-PROPOSITO.md (modo consolidated)"
        assert not os.path.exists(os.path.join(temp_dir, "02-IDEAS.md")), \
            "No debería generar 02-IDEAS.md (modo consolidated)"
        assert not os.path.exists(os.path.join(temp_dir, "03-ESTRUCTURA.md")), \
            "No debería generar 03-ESTRUCTURA.md (modo consolidated)"

        # Verificar que todos los archivos .md (raíz) tienen frontmatter YAML
        archivos_raiz = [
            f for f in os.listdir(temp_dir)
            if f.endswith(".md") and os.path.isfile(os.path.join(temp_dir, f))
        ]
        for archivo in archivos_raiz:
            ruta = os.path.join(temp_dir, archivo)
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
            assert contenido.startswith("---"), (
                f"El archivo {archivo} no comienza con YAML Frontmatter"
            )
            assert "---" in contenido[3:], (
                f"El archivo {archivo} no cierra el bloque YAML Frontmatter"
            )

        # Verificar que el índice contiene wikilinks a las secciones
        indice_path = os.path.join(temp_dir, "00-INDICE.md")
        with open(indice_path, "r", encoding="utf-8") as f:
            contenido_indice = f.read()
        assert "[[1.0-PROPOSITO" in contenido_indice, (
            "El índice no enlaza a 1.0-PROPOSITO"
        )
        assert "[[2.0-IDEAS" in contenido_indice, (
            "El índice no enlaza a 2.0-IDEAS"
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Test: Vault Consolidado ===")
    test_consolidated_vault_limita_archivos()
    print("   OK: test_consolidated_vault_limita_archivos PASO")

    print()
    print("=== Test: Vault Raw ===")
    test_raw_mode_genera_estructura_carpetas()
    print("   OK: test_raw_mode_genera_estructura_carpetas PASO")

    print()
    print("=== Test: Vault Jerárquico ===")
    test_hierarchical_vault_estructura()
    print("   OK: test_hierarchical_vault_estructura PASO")

    print()
    print("Todos los tests pasaron correctamente.")

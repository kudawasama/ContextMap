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
from context_map.presentation.vault import render_obsidian_vault


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

        # Verificar archivos y carpetas del modo hierarchical
        assert os.path.exists(os.path.join(temp_dir, "00-INDICE.md")), \
            "No se generó 00-INDICE.md"

        # Verificar carpetas de secciones
        seccion_dirs = ["1.0-PROPOSITO", "2.0-IDEAS", "3.0-ESTRUCTURA",
                        "4.0-RIESGOS", "5.0-BACKLOG", "6.0-HISTORIAL"]
        for sd in seccion_dirs:
            assert os.path.isdir(os.path.join(temp_dir, sd)), \
                f"No se creó la carpeta {sd}"

        # Verificar archivos dentro de carpetas
        assert os.path.exists(os.path.join(temp_dir, "1.0-PROPOSITO", "1.0-PROPOSITO.md")), \
            "No se generó la sección 1.0-PROPOSITO"
        assert os.path.exists(os.path.join(temp_dir, "1.0-PROPOSITO", "1.1-Mapa-Mental-Narrativo.md")), \
            "No se generó 1.1-Mapa-Mental-Narrativo"
        assert os.path.exists(os.path.join(temp_dir, "2.0-IDEAS", "2.0-IDEAS.md")), \
            "No se generó 2.0-IDEAS"
        assert os.path.exists(os.path.join(temp_dir, "3.0-ESTRUCTURA", "3.0-ESTRUCTURA.md")), \
            "No se generó 3.0-ESTRUCTURA"

        # Verificar que NO genera archivos del modo consolidated
        assert not os.path.exists(os.path.join(temp_dir, "01-PROPOSITO.md")), \
            "No debería generar 01-PROPOSITO.md (modo consolidated)"
        assert not os.path.exists(os.path.join(temp_dir, "02-IDEAS.md")), \
            "No debería generar 02-IDEAS.md (modo consolidated)"
        assert not os.path.exists(os.path.join(temp_dir, "03-ESTRUCTURA.md")), \
            "No debería generar 03-ESTRUCTURA.md (modo consolidated)"

        # Verificar que todos los archivos .md (raíz y carpetas) tienen frontmatter YAML
        todos_md = []
        for root, _dirs, files in os.walk(temp_dir):
            for f in files:
                if f.endswith(".md"):
                    todos_md.append(os.path.join(root, f))
        for ruta in todos_md:
            with open(ruta, "r", encoding="utf-8") as f:
                contenido = f.read()
            assert contenido.startswith("---"), (
                f"El archivo {ruta} no comienza con YAML Frontmatter"
            )
            assert "---" in contenido[3:], (
                f"El archivo {ruta} no cierra el bloque YAML Frontmatter"
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


def test_contexto_narrativo_con_alma() -> None:
    """Verifica que las notas de idea incluyan las 5 preguntas narrativas y la matriz de Pros/Contras."""
    nodos = [
        Node(
            id="IDEA-PEND-01",
            type="IDEA",
            title="Implementar autenticación JWT",
            summary="Soporte para tokens seguros JWT en endpoints de la API",
            status="pendiente",
            source="scanner",
            tags=["idea", "auth", "pendiente"],
        )
    ]
    edges = _crear_edges_de_prueba()
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_vault_narrativa_")

    try:
        render_obsidian_vault(
            project_name="TestProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="hierarchical",
        )

        ideas_dir = os.path.join(temp_dir, "2.0-IDEAS", "2.1-Ideas-Pendientes")
        assert os.path.exists(ideas_dir), "No se creó el directorio de ideas pendientes"

        archivos = [f for f in os.listdir(ideas_dir) if f.endswith(".md") and f != "2.1-Ideas-Pendientes.md"]
        assert len(archivos) > 0, "No se generaron notas de ideas pendientes"

        sample_note = os.path.join(ideas_dir, archivos[0])
        with open(sample_note, "r", encoding="utf-8") as f:
            content = f.read()

        assert "POR QUÉ" in content, "La nota no contiene la sección ¿POR QUÉ?"
        assert "DE DÓNDE SURGIÓ" in content, "La nota no contiene la sección ¿DE DÓNDE SURGIÓ?"
        assert "PARA QUÉ" in content, "La nota no contiene la sección ¿PARA QUÉ?"
        assert "CÓMO" in content, "La nota no contiene la sección ¿CÓMO?"
        assert "PROS Y CONTRAS" in content, "La nota no contiene la sección PROS Y CONTRAS"
        assert "PROS (Ventajas)" in content, "La nota no contiene la tabla de PROS"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_contexto_narrativo_diferenciado_riesgo() -> None:
    """Verifica que los nodos RIESGO generen narrativa con matriz de gravedad y mitigación."""
    nodos = [
        Node(
            id="RIESGO-01",
            type="RIESGO",
            title="Archivo complejo: writer.py (2300 líneas)",
            summary="Zona de alta complejidad en el renderizador de notas.",
            status="activo",
            source="scanner",
            tags=["riesgo", "complejidad"],
        )
    ]
    edges = []
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_vault_riesgo_")

    try:
        render_obsidian_vault(
            project_name="TestProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="hierarchical",
        )

        from context_map.core.generators import generar_contexto_narrativo
        narrativa = generar_contexto_narrativo(nodos[0])

        assert "RIESGO" in narrativa, "La narrativa no contiene sección de RIESGO"
        assert "IMPACTO" in narrativa, "La narrativa no contiene sección de IMPACTO"
        assert "MITIGAR" in narrativa, "La narrativa no contiene sección de MITIGACIÓN"
        assert "MATRIZ DE GRAVEDAD" in narrativa, "La narrativa no contiene la MATRIZ DE GRAVEDAD"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_null_byte_character_in_filename() -> None:
    """Verifica que títulos con caracteres nulos (\x00) no provoquen ValueError al abrir archivos."""
    nodos = [
        Node(
            id="IDEA-NUL-01",
            type="IDEA",
            title="Idea con caracter\x00 nulo en titulo",
            summary="Resumen con \x00 nulos",
            status="pendiente",
            source="scanner",
            tags=["idea", "pendiente"],
        )
    ]
    edges = []
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_nul_")

    try:
        render_obsidian_vault(
            project_name="TestNulProject",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="hierarchical",
        )
        ideas_dir = os.path.join(temp_dir, "2.0-IDEAS", "2.1-Ideas-Pendientes")
        assert os.path.exists(ideas_dir)
        archivos = [f for f in os.listdir(ideas_dir) if f.endswith(".md") and f != "2.1-Ideas-Pendientes.md"]
        assert len(archivos) > 0
        assert "\x00" not in archivos[0]

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
    print("=== Test: Contexto Narrativo con Alma ===")
    test_contexto_narrativo_con_alma()
    print("   OK: test_contexto_narrativo_con_alma PASO")

    print()
    print("=== Test: Caracteres Nulos ===")
    test_null_byte_character_in_filename()
    print("   OK: test_null_byte_character_in_filename PASO")

    print()
    print("Todos los tests pasaron correctamente.")

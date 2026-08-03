"""Pruebas unitarias para la generación de diagramas Mermaid en Obsidian."""

from __future__ import annotations

from context_map.core.models import Edge, Node
from context_map.presentation.vault.mermaid import (
    _crear_id_mermaid,
    _sanear_etiqueta,
    generar_diagrama_mermaid_global,
    generar_diagrama_mermaid_nodo,
)


def test_sanear_etiqueta() -> None:
    """Verifica que las etiquetas no contengan caracteres problemáticos para Mermaid."""
    raw = 'Archivo complejo: "main.py" [100 líneas] {test}'
    saneado = _sanear_etiqueta(raw)

    assert '"' not in saneado
    assert '[' not in saneado
    assert ']' not in saneado
    assert '{' not in saneado
    assert '}' not in saneado
    assert "main.py" in saneado


def test_crear_id_mermaid() -> None:
    """Verifica la generación de identificadores seguros."""
    assert _crear_id_mermaid("BASE-01.002") == "BASE_01_002"
    assert _crear_id_mermaid("node@test") == "node_test"


def test_generar_diagrama_mermaid_nodo() -> None:
    """Verifica que generar_diagrama_mermaid_nodo construya un bloque graph TD válido."""
    n1 = Node(id="N1", type="BASE", title="Modulo A")
    n2 = Node(id="N2", type="BASE", title="Modulo B")
    e1 = Edge(source="N1", target="N2", kind="depends_on")

    diag = generar_diagrama_mermaid_nodo(n1, [n1, n2], [e1])

    assert "```mermaid" in diag
    assert "graph TD" in diag
    assert "N1" in diag
    assert "N2" in diag
    assert "-->|depends_on|" in diag


def test_generar_diagrama_mermaid_global() -> None:
    """Verifica la generación del diagrama global de arquitectura."""
    n1 = Node(id="N1", type="BASE", title="CLI Core")
    n2 = Node(id="N2", type="BASE", title="Scanner Engine")
    e1 = Edge(source="N1", target="N2", kind="blocks")

    diag = generar_diagrama_mermaid_global([n1, n2], [e1])

    assert "```mermaid" in diag
    assert "graph TD" in diag
    assert "CLI Core" in diag
    assert "Scanner Engine" in diag

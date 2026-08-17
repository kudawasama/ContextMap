"""El diario consolida bloques del scanner en uno solo (R4) y no trunca títulos (R5).

Auditoría 2026-08-14: el diario del 13-08 acumuló 9 bloques "🤖 Ingresados
por el scanner" por builds repetidos del mismo día. Cada anexo debe
CONSOLIDARSE en la sección autogenerada existente, no crear otra.
"""

from __future__ import annotations

from datetime import date

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.canvas import render_nota_dia


def _nodo(titulo: str, fecha: str) -> Node:
    """Crea un nodo BASE con la fecha de creación dada.

    Args:
        titulo (str): Título del nodo.
        fecha (str): Fecha ISO (YYYY-MM-DD) del nodo.

    Returns:
        Node: Nodo listo para renderizar.
    """
    return Node(id=titulo, type="BASE", title=titulo, created_at=f"{fecha}T10:00:00")


def _ruta_diario(tmp_path, hoy: str):
    """Ruta esperada del diario del día en el vault del proyecto."""
    return (
        tmp_path
        / ".context-map"
        / "vault-MiProyecto"
        / "7.0-MANUAL"
        / "Diario"
        / f"{hoy}.md"
    )


def test_anexa_una_sola_seccion_autogenerada(tmp_path):
    """Dos builds del mismo día consolidan en UNA sección autogenerada."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    n1 = _nodo("Primer nodo del día", hoy)
    n2 = _nodo("Segundo nodo del día", hoy)
    render_nota_dia(out, "MiProyecto", [n1])
    render_nota_dia(out, "MiProyecto", [n1, n2])
    ruta = _ruta_diario(tmp_path, hoy)
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("🤖 Ingresados por el scanner") == 1
    assert "Segundo nodo del día" in contenido


def test_no_trunca_titulos_a_60(tmp_path):
    """Un título largo se escribe completo (sin [:60])."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    titulo_largo = "x" * 120
    render_nota_dia(out, "MiProyecto", [_nodo(titulo_largo, hoy)])
    ruta = _ruta_diario(tmp_path, hoy)
    assert titulo_largo in ruta.read_text(encoding="utf-8")


def test_tres_builds_tres_nodos_un_bloque(tmp_path):
    """Tres builds con nodos distintos siguen consolidando en un solo bloque."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    for i in range(3):
        nodos = [_nodo(f"Nodo {j}", hoy) for j in range(i + 1)]
        render_nota_dia(out, "MiProyecto", nodos)
    ruta = _ruta_diario(tmp_path, hoy)
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("🤖 Ingresados por el scanner") == 1
    assert "Nodo 0" in contenido and "Nodo 1" in contenido and "Nodo 2" in contenido


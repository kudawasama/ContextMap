"""P2.3: el lienzo del vault debe ser **determinista** (reproducible byte a byte).

Antes usaba ``uuid4()`` para los ids de nodos y aristas, así que cada build
generaba un ``00-MAPA-MENTAL.canvas`` distinto: imposible comparar versiones o
verificar un cambio por hash. Ahora los ids derivan del contenido con ``uuid5``.
"""

from __future__ import annotations

import json
from pathlib import Path

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.canvas import _canvas_id, render_canvas


def _nodos() -> list[Node]:
    """Dos nodos con archivo propio (los agrupados no van al lienzo)."""
    return [
        Node(id="R1", type="RIESGO", title="Ruido de snapshots"),
        Node(id="R2", type="RIESGO", title="Vaults duplicados"),
    ]


def test_ids_estables_para_la_misma_clave() -> None:
    """La misma clave produce el mismo id; claves distintas, ids distintos."""
    assert _canvas_id("4.0-RIESGOS/a.md") == _canvas_id("4.0-RIESGOS/a.md")
    assert _canvas_id("4.0-RIESGOS/a.md") != _canvas_id("4.0-RIESGOS/b.md")


def test_lienzo_identico_entre_builds(tmp_path) -> None:
    """Dos renders del mismo grafo generan exactamente el mismo payload."""
    nodos = _nodos()
    aristas = [Edge(source="R1", target="R2", kind="relaciona")]
    dirs = []
    for nombre in ("a", "b"):
        carpeta = tmp_path / nombre
        carpeta.mkdir()
        dirs.append(render_canvas(str(carpeta), nodos, aristas))

    with open(dirs[0], encoding="utf-8") as f:
        primero = json.load(f)
    with open(dirs[1], encoding="utf-8") as f:
        segundo = json.load(f)

    assert primero == segundo, "el lienzo cambió entre builds (ids aleatorios)"
    assert [n["id"] for n in primero["nodes"]] == [n["id"] for n in segundo["nodes"]]
    assert [e["id"] for e in primero["edges"]] == [e["id"] for e in segundo["edges"]]


def test_no_quedan_uuid_aleatorios_en_el_lienzo(tmp_path) -> None:
    """El payload no debe contener ids regenerados al azar (regresión)."""
    from context_map.presentation.vault.consolidated import canvas as modulo

    fuente = Path(modulo.__file__).read_text(encoding="utf-8")
    assert "uuid.uuid4()" not in fuente, "el lienzo debe usar uuid5 (determinista)"

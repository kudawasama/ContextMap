from __future__ import annotations

import os
from context_map.store import write_map, snapshot_map
from context_map.writer import render_active_map
from context_map.models import Node, Edge


def test_smoke_render() -> None:
    """
    Verifica que el writer genera el mapa esperado.
    """
    nodes: list[Node] = [
        Node(id="BASE-01", type="BASE", title="Demo", summary="demo", source="test")
    ]
    edges: list[Edge] = [Edge(source="BASE-01", target="IDEA-01", kind="depends_on")]
    md = render_active_map("Demo", nodes, edges)
    assert "# Demo — Context Map" in md
    assert "## Mapa mental de contexto" in md
    assert "## Conexiones" in md


if __name__ == "__main__":
    test_smoke_render()
    print("smoke:ok")

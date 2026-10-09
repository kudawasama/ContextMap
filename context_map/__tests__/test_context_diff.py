"""Tests del diff de contexto (`context_diff`): detectar solo lo que cambió."""

from __future__ import annotations

import json
import os

from context_map.core.models import Node
from context_map.domain.analysis.diff_contexto import (
    cargar_indice,
    comparar,
    digest_de,
    formatear_diff,
    guardar_indice,
    snapshot_de_nodos,
)


def _nodo(nid: str, titulo: str, upd: str = "2026-01-01", resumen: str = "x") -> Node:
    """Nodo mínimo para el diff."""
    return Node(id=nid, type="BASE", title=titulo, summary=resumen, updated_at=upd)


def test_digest_cambia_cuando_cambia_un_nodo() -> None:
    """El digest agregado distingue conjuntos distintos y es estable."""
    a = [_nodo("1", "Uno"), _nodo("2", "Dos")]
    b = [_nodo("1", "Uno"), _nodo("2", "Dos", upd="2026-02-02")]
    assert digest_de(a) != digest_de(b)
    assert digest_de(a) == digest_de(list(a))


def test_comparar_detecta_agregados_cambiados_eliminados() -> None:
    """El diff clasifica nodos en agregados, cambiados y eliminados."""
    antes = snapshot_de_nodos([_nodo("1", "Uno"), _nodo("2", "Dos"), _nodo("3", "Tres")])
    despues = snapshot_de_nodos(
        [_nodo("1", "Uno"), _nodo("2", "Dos v2", upd="2026-03-03"), _nodo("4", "Cuatro")]
    )
    cambios = comparar(antes, despues)
    assert cambios["agregados"] == ["Cuatro"]
    assert cambios["eliminados"] == ["Tres"]
    assert cambios["cambiados"] == ["Dos v2"]


def test_formatear_diff_sin_cambios() -> None:
    """Sin cambios devuelve una sola línea compacta."""
    txt = formatear_diff("abc", "abc", {"agregados": [], "cambiados": [], "eliminados": []})
    assert "Sin cambios" in txt


def test_indice_persistente_con_retencion(tmp_path) -> None:
    """El índice se guarda, se relee y recorta a los más recientes."""
    ruta = str(tmp_path / "digest_index.json")
    assert cargar_indice(ruta) == {}
    guardar_indice(ruta, {"d1": {"1": {"fp": "a", "t": "Uno"}}, "d2": {}}, retencion=1)
    indice = cargar_indice(ruta)
    assert list(indice) == ["d2"]


def test_tool_context_diff_end_to_end(tmp_path) -> None:
    """La tool devuelve el digest, detecta 'sin cambios' y luego el delta real."""
    state = os.path.join(str(tmp_path), ".context-map", "state")
    os.makedirs(state)

    def escribir(nodos: list[Node]) -> None:
        with open(os.path.join(state, "graph.jsonl"), "w", encoding="utf-8") as f:
            for n in nodos:
                f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")

    from context_map.infrastructure.mcp_server import context_diff

    escribir([_nodo("1", "Uno"), _nodo("2", "Dos")])
    primera = context_diff(target=str(tmp_path))
    digest = [ln for ln in primera.splitlines() if ln.startswith("digest:")][0].split(": ", 1)[1]
    assert "Sin cambios" in context_diff(since=digest, target=str(tmp_path))

    escribir([_nodo("1", "Uno"), _nodo("2", "Dos v2", upd="2026-05-05"), _nodo("3", "Tres")])
    salida = context_diff(since=digest, target=str(tmp_path))
    assert "Tres" in salida and "Dos v2" in salida

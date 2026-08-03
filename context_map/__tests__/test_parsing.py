"""Pruebas unitarias para los módulos de parsing, clasificación y almacenamiento."""

from __future__ import annotations

import os
import tempfile

from context_map.core.models import Event, Node
from context_map.core.parsing import (
    _dedup_events,
    events_to_model,
    load_events_from_jsonl,
)
from context_map.core.parsing.clasificacion import _heuristic_event
from context_map.core.storage import append_jsonl, load_jsonl


def test_heuristic_event() -> None:
    """Verifica la inferencia de tipos a partir de keywords en el texto."""
    assert _heuristic_event("Fix error in main loop", "chat").type == "CORRECCION"
    assert _heuristic_event("Feature nueva implementada", "chat").type == "IDEA"
    assert _heuristic_event("Pytest unit tests passing", "chat").type == "PRUEBA"


def test_dedup_events() -> None:
    """Verifica la eliminación de eventos duplicados por tipo y texto."""
    e1 = Event(type="IDEA", text="Nueva idea 1", timestamp="2026-07-31T10:00:00")
    e2 = Event(type="IDEA", text="Nueva idea 1", timestamp="2026-07-31T11:00:00")
    e3 = Event(type="BASE", text="Componente base", timestamp="2026-07-31T12:00:00")

    unicos = _dedup_events([e1, e2, e3])
    assert len(unicos) == 2
    assert unicos[0].text == "Nueva idea 1"
    assert unicos[1].text == "Componente base"


def test_events_to_model() -> None:
    """Verifica la conversión de eventos a nodos y generación de IDs."""
    e1 = Event(type="BASE", text="Modulo core principal", timestamp="2026-07-31T10:00:00")
    e2 = Event(type="IDEA", text="Soporte para plugin X", timestamp="2026-07-31T10:05:00")

    nodes, edges = events_to_model([e1, e2], start_id=1)
    assert len(nodes) == 2
    assert nodes[0].type == "BASE"
    assert nodes[0].id == "BASE.001"
    assert nodes[1].type == "IDEA"
    assert nodes[1].id == "IDEA.001"


def test_storage_jsonl_roundtrip() -> None:
    """Verifica la persistencia y lectura JSONL en disco."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_storage_")
    filepath = os.path.join(temp_dir, "test.jsonl")

    try:
        node = Node(id="TEST-01", type="BASE", title="Nodo de prueba")
        append_jsonl(filepath, [node.to_dict()])

        cargados = load_jsonl(filepath)
        assert len(cargados) == 1
        assert cargados[0]["id"] == "TEST-01"
        assert cargados[0]["title"] == "Nodo de prueba"
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)
        os.rmdir(temp_dir)

"""Submódulo de almacenamiento y persistencia del mapa conceptual."""

from __future__ import annotations

from context_map.core.storage.store import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)

__all__ = [
    "append_jsonl",
    "load_jsonl",
    "write_map",
    "snapshot_map",
]

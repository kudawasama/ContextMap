"""Submódulo de parsing e ingesta de eventos para el mapa conceptual."""

from __future__ import annotations

from context_map.core.parsing.parser import (
    JSONL_TYPES,
    _dedup_events,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)

__all__ = [
    "load_events_from_jsonl",
    "load_events_from_chat_folder",
    "events_to_model",
    "_dedup_events",
    "JSONL_TYPES",
]

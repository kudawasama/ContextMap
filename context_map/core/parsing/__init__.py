"""Submódulo de parsing e ingesta de eventos para el mapa conceptual."""

from context_map.core.parsing.parser import (
    load_events_from_jsonl,
    load_events_from_chat_folder,
    events_to_model,
    _dedup_events,
    JSONL_TYPES,
)

__all__ = [
    "load_events_from_jsonl",
    "load_events_from_chat_folder",
    "events_to_model",
    "_dedup_events",
    "JSONL_TYPES",
]

"""Submódulo de parsing e ingesta de eventos para el mapa conceptual."""

from __future__ import annotations

from context_map.core.parsing.cargadores import (
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.parsing.clasificacion import JSONL_TYPES
from context_map.core.parsing.dedup import _dedup_events
from context_map.core.parsing.grafo import events_to_model

__all__ = [
    "load_events_from_jsonl",
    "load_events_from_chat_folder",
    "events_to_model",
    "_dedup_events",
    "JSONL_TYPES",
]

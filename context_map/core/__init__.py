"""Capa principal Core de context_map.

Re-exporta símbolos principales desde los submódulos:
- `models`: Dataclasses Node, Edge, Event.
- `parsing`: Carga y conversión de eventos.
- `storage`: Persistencia de mapas y snapshots.
- `normalization`: Estandarización y clasificación semántica de nodos.
- `generators`: Generación de summaries y narrativa con alma.
"""

from __future__ import annotations

from context_map.core.generators import (
    generar_contexto_narrativo,
    generar_summary,
)
from context_map.core.models import NODE_TYPES, Edge, Event, Node
from context_map.core.normalization import (
    classification_tag,
    corregir_tipo,
    estandarizar_nodo,
    estandarizar_nodos,
    estandarizar_tags,
    inferir_classification,
    inferir_evidence,
    inferir_status,
)
from context_map.core.parsing import (
    JSONL_TYPES,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.storage import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)

__all__ = [
    "Node",
    "Edge",
    "Event",
    "NODE_TYPES",
    "load_events_from_jsonl",
    "load_events_from_chat_folder",
    "events_to_model",
    "JSONL_TYPES",
    "append_jsonl",
    "load_jsonl",
    "write_map",
    "snapshot_map",
    "inferir_classification",
    "classification_tag",
    "estandarizar_tags",
    "inferir_status",
    "inferir_evidence",
    "corregir_tipo",
    "estandarizar_nodo",
    "estandarizar_nodos",
    "generar_summary",
    "generar_contexto_narrativo",
]

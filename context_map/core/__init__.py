"""Capa principal Core de context_map.

Re-exporta símbolos principales desde los submódulos:
- `models`: Dataclasses Node, Edge, Event.
- `parsing`: Carga y conversión de eventos.
- `storage`: Persistencia de mapas y snapshots.
- `normalization`: Estandarización y clasificación semántica de nodos.
- `generators`: Generación de summaries y narrativa con alma.
"""

from context_map.core.models import Node, Edge, Event, NODE_TYPES
from context_map.core.parsing import (
    load_events_from_jsonl,
    load_events_from_chat_folder,
    events_to_model,
    JSONL_TYPES,
)
from context_map.core.storage import (
    append_jsonl,
    load_jsonl,
    write_map,
    snapshot_map,
    nodes_to_digest,
    edges_dedup,
)
from context_map.core.normalization import (
    inferir_classification,
    classification_tag,
    estandarizar_tags,
    inferir_status,
    inferir_evidence,
    corregir_tipo,
    estandarizar_nodo,
    estandarizar_nodos,
)
from context_map.core.generators import (
    generar_summary,
    generar_contexto_narrativo,
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
    "nodes_to_digest",
    "edges_dedup",
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

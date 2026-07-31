"""Submódulo de estandarización y normalización semántica de nodos."""

from __future__ import annotations

from context_map.core.normalization.standardize import (
    classification_tag,
    corregir_tipo,
    dedup_nodes,
    estandarizar_nodo,
    estandarizar_nodos,
    estandarizar_tags,
    inferir_classification,
    inferir_evidence,
    inferir_status,
)

__all__ = [
    "inferir_classification",
    "classification_tag",
    "estandarizar_tags",
    "inferir_status",
    "inferir_evidence",
    "corregir_tipo",
    "estandarizar_nodo",
    "estandarizar_nodos",
    "dedup_nodes",
]

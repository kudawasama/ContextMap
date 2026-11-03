"""Estandarización y clasificación semántica de nodos del grafo.

Este módulo es el **orquestador** del proceso: decide en qué orden se aplican
las piezas y compone el nodo final. Las piezas viven en los submódulos
especializados:

- ``mappings.py``: constantes y patrones.
- ``inference.py``: clasificación, concepto, estado y evidencias.
- ``cleaning.py``: tags, título y deduplicación.
- ``paneles.py``: motor de decisión y cola de revisión.

El orden importa: el estado se infiere del nodo **ya normalizado** (título y
tags limpios), no del original, porque los volátiles numéricos de los títulos
de ``RIESGO`` alteraban la inferencia. Los ``DOCUMENTO`` son la excepción: su
estado y su clasificación vienen de la ingesta y no se reinterpretan.
"""

from __future__ import annotations

from context_map.core.models import Node
from context_map.core.normalization.cleaning import (
    _restaurar_paths_legibles,
    ajustar_tags,
    dedup_nodes,
    depurar_nodos_obsoletos,
    estandarizar_tags,
    normalizar_titulo,
)
from context_map.core.normalization.inference import (
    clasificar_tipo,
    classification_tag,
    corregir_tipo,
    inferir_classification,
    inferir_concepto,
    inferir_evidence,
    inferir_status,
)
from context_map.core.normalization.mappings import (
    CLASSIFICATION_PATTERNS,
    CONCEPT_PATTERNS,
    DEFAULT_CLASSIFICATION,
    DEFAULT_CONCEPT,
    TAG_FILE_MAP,
    TAG_MERGE,
    TAGS_ELIMINAR,
)
from context_map.core.normalization.paneles import TAG_REVISION


def estandarizar_nodo(node: Node) -> Node:
    """Aplica el proceso completo de estandarización y clasificación a un nodo.

    Args:
        node (Node): Nodo original.

    Returns:
        Node: Nuevo nodo estandarizado.
    """
    es_documento = node.type == "DOCUMENTO"

    if es_documento:
        classif_id = node.classification or "docs"
        concept_id = node.concept or DEFAULT_CONCEPT
    else:
        classif_id, _ = inferir_classification(node)
        concept_id = inferir_concepto(node)

    tags = ajustar_tags(estandarizar_tags(node.tags), classif_id)

    nuevo_tipo, tipo_decision = clasificar_tipo(node)
    # Cola de revisión: si dos tipos distintos acumularon evidencia comparable,
    # la etiqueta queda visible en el vault en lugar de resolverse en silencio.
    if tipo_decision.en_conflicto() and TAG_REVISION not in tags:
        tags.append(TAG_REVISION)

    estandarizado = Node(
        id=node.id,
        type=nuevo_tipo,
        title=normalizar_titulo(node),
        summary=node.summary,
        tags=tags,
        source=node.source,
        status=node.status,
        version=node.version,
        evidence=node.evidence,
        created_at=node.created_at,
        updated_at=node.updated_at,
        classification=classif_id,
        concept=concept_id,
    )

    if not es_documento:
        estandarizado.status = inferir_status(estandarizado)

    evidencia_inferida = inferir_evidence(node)
    if evidencia_inferida:
        estandarizado.evidence = evidencia_inferida

    return estandarizado


def estandarizar_nodos(nodes: list[Node]) -> list[Node]:
    """Aplica la estandarización a una lista completa de nodos.

    Args:
        nodes (list[Node]): Lista de nodos.

    Returns:
        list[Node]: Lista de nodos procesados.
    """
    return [estandarizar_nodo(n) for n in nodes]


__all__ = [
    "TAGS_ELIMINAR",
    "CLASSIFICATION_PATTERNS",
    "DEFAULT_CLASSIFICATION",
    "CONCEPT_PATTERNS",
    "DEFAULT_CONCEPT",
    "TAG_FILE_MAP",
    "TAG_MERGE",
    "inferir_concepto",
    "inferir_classification",
    "classification_tag",
    "estandarizar_tags",
    "inferir_status",
    "inferir_evidence",
    "corregir_tipo",
    "clasificar_tipo",
    "_restaurar_paths_legibles",
    "ajustar_tags",
    "normalizar_titulo",
    "estandarizar_nodo",
    "estandarizar_nodos",
    "depurar_nodos_obsoletos",
    "dedup_nodes",
]

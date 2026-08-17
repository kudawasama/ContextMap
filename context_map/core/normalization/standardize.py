"""Estandarización y clasificación semántica de nodos del grafo.

Proporciona funciones para:
- Clasificación semántica basada en Conventional Commits.
- Normalización y estandarización de tags.
- Inferencia de estado del nodo (completado, pendiente, activo).
- Corrección de tipo según contenido real.
- Inferencia de evidencias.
- Deduplicación de nodos por (tipo, título) para mantener el grafo limpio.

Este módulo actúa como facade orquestador reexportando las funciones
e inferencias de los submódulos especializados:
- ``mappings.py`` (constantes y patrones)
- ``inference.py`` (inferencias semánticas)
- ``cleaning.py`` (limpieza, depuración y dedup)
"""

from __future__ import annotations

import re

from context_map.core.models import Node
from context_map.core.normalization.cleaning import (
    _restaurar_paths_legibles,
    dedup_nodes,
    depurar_nodos_obsoletos,
    estandarizar_tags,
)
from context_map.core.normalization.inference import (
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


def estandarizar_nodo(node: Node) -> Node:
    """Aplica el proceso completo de estandarización y clasificación a un solo nodo.

    Args:
        node (Node): Nodo original.

    Returns:
        Node: Nuevo nodo estandarizado.
    """
    es_documento = node.type == "DOCUMENTO"
    classif_id, _ = inferir_classification(node) if not es_documento else (node.classification or "docs", "Documento")
    concept_id = inferir_concepto(node) if not es_documento else (node.concept or "GENERAL")
    tags = estandarizar_tags(node.tags)

    # Limpiar tags legacy "class{X}" sin colon (ej: "classchore", "classfeature")
    tags = [t for t in tags if not re.match(r'^class[a-z]+$', t)]

    # Agregar class_tag solo si no existe ya en formato limpio
    class_tag = classification_tag(classif_id)
    if class_tag not in tags:
        tags.append(class_tag)

    # Normalizar título para eliminar volátiles numéricos en RIESGO
    title = node.title
    if node.type == "RIESGO":
        title = re.sub(r'\s*\(\d+\s*(?:l[ií]neas?|l[ií]n|total|l(?!\w))\)?', '', title)
        title = re.sub(r';\s*[^;]+\(\d+\s*l[ií]neas?\)?', '', title)
        title = re.sub(r'\s*;\s*', ', ', title)
        title = title.rstrip(';,').strip()
        title = _restaurar_paths_legibles(title)

    nuevo_tipo = corregir_tipo(node)
    nodo_temp = Node(
        id=node.id,
        type=nuevo_tipo,
        title=title,
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

    return Node(
        id=node.id,
        type=nuevo_tipo,
        title=title,
        summary=node.summary,
        tags=tags,
        source=node.source,
        status=node.status if es_documento else inferir_status(nodo_temp),
        version=node.version,
        evidence=inferir_evidence(node) or node.evidence,
        created_at=node.created_at,
        updated_at=node.updated_at,
        classification=classif_id,
        concept=concept_id,
    )


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
    "_restaurar_paths_legibles",
    "estandarizar_nodo",
    "estandarizar_nodos",
    "depurar_nodos_obsoletos",
    "dedup_nodes",
]

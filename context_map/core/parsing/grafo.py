"""Conversión de eventos normalizados en el grafo conceptual.

Transforma una lista de eventos en la dupla de nodos y aristas que
alimenta el modelo de contexto del proyecto.
"""

from __future__ import annotations

import re
from datetime import datetime

from context_map.core.generators import generar_summary
from context_map.core.models import Edge, Event, Node
from context_map.core.parsing.clasificacion import JSONL_TYPES


def _now() -> str:
    """Retorna la fecha y hora actual en ISO 8601.

    Returns:
        str: Timestamp actual.
    """
    return datetime.now().isoformat(timespec="seconds")


def events_to_model(
    events: list[Event], start_id: int = 1
) -> tuple[list[Node], list[Edge]]:
    """Transforma una lista de eventos normalizados en nodos y aristas del grafo conceptual.

    Args:
        events (List[Event]): Eventos a transformar.
        start_id (int): ID de inicio para los nodos generados.

    Returns:
        Tuple[List[Node], List[Edge]]: Dupla con la lista de nodos y la lista de aristas generadas.
    """
    nodes: list[Node] = []
    edges: list[Edge] = []
    counters: dict[str, int] = {}
    id_by_key: dict[tuple[str, str, str], str] = {}

    def _prefix(t: str) -> str:
        return t if t in JSONL_TYPES else "IDEA"

    for e in events:
        prefix = _prefix(e.type)
        counters[prefix] = counters.get(prefix, 0) + 1
        pid = f"{prefix}.{counters[prefix]:003d}"
        title = e.text.split("\n")[0][:200]

        summary = generar_summary(e.type, e.text, e.source, e.tags)

        node = Node(
            id=pid,
            type=prefix,
            title=title,
            summary=summary,
            tags=list(e.tags),
            source=e.source,
            created_at=e.timestamp or _now(),
            updated_at=e.timestamp or _now(),
        )
        nodes.append(node)
        id_by_key[(e.type, e.source, e.text)] = pid

        lowered = e.text.lower()
        if "termina en" in lowered or "=>" in e.text:
            parts = re.split(r"=>|termina en|\n", e.text)
            if len(parts) >= 2:
                target_text = parts[-1].strip()[:120]
                for k, tid in id_by_key.items():
                    if target_text and target_text.lower() in k[2].lower() and tid != pid:
                        edges.append(Edge(source=pid, target=tid, kind="depends_on"))
                        node.depends_on.append(tid)
                        break

    return nodes, edges

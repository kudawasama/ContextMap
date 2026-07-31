"""Desduplicación de eventos normalizados."""

from __future__ import annotations

from context_map.core.models import Event


def _dedup_events(events: list[Event]) -> list[Event]:
    """Elimina eventos duplicados preservando el orden cronológico.

    Args:
        events (List[Event]): Lista de eventos a desduplicar.

    Returns:
        List[Event]: Eventos únicos.
    """
    seen: set[tuple[str, str, str]] = set()
    out: list[Event] = []
    for e in sorted(
        events,
        key=lambda x: (x.timestamp or "", x.source, x.text[:40]),
    ):
        k = (e.type, e.text, e.source)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

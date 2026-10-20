"""Clasificación tipada de eventos no tipados (chats, JSONL y agentes).

Históricamente esta clasificación usaba una lista de patrones donde ganaba el
**primero** que coincidía: un ``feature`` en la frase anulaba el ``fix`` que
realmente describía el trabajo, y no había forma de saber cuán segura era la
etiqueta.

Ahora delega en el panel tipado (:mod:`context_map.core.normalization.paneles`),
que acumula evidencia ponderada, calcula una distribución de probabilidad y
expone la confianza. Cuando el texto recibe evidencia fuerte de dos tipos
distintos, el evento se marca con ``revision:clasificacion`` para que la
ambigüedad sea visible en el vault en lugar de resolverse en silencio.
"""

from __future__ import annotations

from context_map.core.models import Event
from context_map.core.normalization.paneles import (
    JSONL_TYPES,
    TAG_REVISION,
    decidir_tipo,
)

__all__ = ["JSONL_TYPES", "TAG_REVISION", "_heuristic_event"]


def _heuristic_event(raw: str, source_hint: str, timestamp: str = "") -> Event:
    """Clasifica texto libre usando el motor de decisiones tipadas.

    Args:
        raw (str): Texto plano del mensaje o línea.
        source_hint (str): Origen del evento.
        timestamp (str): Fecha ISO del origen (archivo de conversación). Vacío si
            la fuente no tiene fecha; sin ella el historial por día se pierde.

    Returns:
        Event: Evento clasificado, con la confianza del motor en ``meta`` y la
            etiqueta de revisión cuando hay evidencia en conflicto.
    """
    text = raw.strip()
    decision = decidir_tipo(text)

    tags: list[str] = [TAG_REVISION] if decision.en_conflicto() else []
    meta = {
        "clasificacion": {
            "motor": "lexico-calibrado",
            "confianza": round(decision.confianza, 4),
            "margen": round(decision.margen, 4),
            "evidencias": [str(ev) for ev in decision.evidencias[:3]],
        }
    }

    return Event(
        type=decision.eleccion,
        text=text,
        timestamp=timestamp,
        source=source_hint,
        tags=tags,
        meta=meta,
    )

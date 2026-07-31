"""Clasificación heurística de eventos no tipados.

Define los tipos normalizados y los patrones léxicos determinísticos
utilizados para inferir la categoría de eventos cuando el texto libre
no trae un tipo explícito.
"""

from __future__ import annotations

import re

from context_map.core.models import Event

JSONL_TYPES: set[str] = {"IDEA", "BASE", "PRUEBA", "FUTURO", "CORRECCION", "RIESGO", "CAMBIO", "HITO"}

# Patrones determinísticos para clasificación heurística del tipo de evento
_LINE_PATTERNS: list[tuple[str | re.Pattern[str], str]] = [
    (re.compile(r"\b(adding|added|feat|feature)\b", re.I), "IDEA"),
    (re.compile(r"\b(fix|fixing|correc|patch)\b", re.I), "CORRECCION"),
    (re.compile(r"\b(test|tested|pytest|spec|qa)\b", re.I), "PRUEBA"),
    (re.compile(r"\b(next|future|todo|planned|roadmap)\b", re.I), "FUTURO"),
    (re.compile(r"\b(risk|bug|issue|danger|blocked)\b", re.I), "RIESGO"),
    (re.compile(r"\b(change|changed|update|updated)\b", re.I), "CAMBIO"),
    (re.compile(r"\b(base|init|seed|bootstrap|setup)\b", re.I), "BASE"),
    (re.compile(r"\b(release|milestone|hit)\b", re.I), "HITO"),
]


def _heuristic_event(raw: str, source_hint: str) -> Event:
    """Clasifica texto libre usando patrones heurísticos léxicos.

    Args:
        raw (str): Texto plano del mensaje o línea.
        source_hint (str): Origen del evento.

    Returns:
        Event: Evento clasificado e instanciado.
    """
    text = raw.strip()
    kind = "IDEA"
    for pat, k in _LINE_PATTERNS:
        if isinstance(pat, re.Pattern) and pat.search(text):
            kind = k
            break
    return Event(type=kind, text=text, timestamp="", source=source_hint)

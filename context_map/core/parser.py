"""Parser de eventos normalizados desde JSONL agnóstico o chats sueltos.

Responsabilidades:
- Normalizar entradas heterogéneas.
- Clasificar heurísticamente eventos no tipados.
- Desduplicar eventos repetidos.
- Convertir eventos en grafo: `Node` y `Edge`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Tuple, Union

from context_map.core.models import Event, Node, Edge
from context_map.core.generadores import generar_summary

JSONL_TYPES = {"IDEA", "BASE", "PRUEBA", "FUTURO", "CORRECCION", "RIESGO", "CAMBIO", "HITO"}

# Patrones determinísticos para tipo de evento
_LINE_PATTERNS: List[Tuple[Union[str, re.Pattern[str]], str]] = [
    (re.compile(r"\b(adding|added|feat|feature)\b", re.I), "IDEA"),
    (re.compile(r"\b(fix|fixing|correc|patch)\b", re.I), "CORRECCION"),
    (re.compile(r"\b(test|tested|pytest|spec|qa)\b", re.I), "PRUEBA"),
    (re.compile(r"\b(next|future|todo|planned|roadmap)\b", re.I), "FUTURO"),
    (re.compile(r"\b(risk|bug|issue|danger|blocked)\b", re.I), "RIESGO"),
    (re.compile(r"\b(change|changed|update|updated)\b", re.I), "CAMBIO"),
    (re.compile(r"\b(base|init|seed|bootstrap|setup)\b", re.I), "BASE"),
    (re.compile(r"\b(release|milestone|hit)\b", re.I), "HITO"),
]


def _safe_jsonl(path: str) -> List[Dict[str, Any]]:
    """Lee objetos JSON desde un JSONL tolerando errores de parseo."""
    out: List[Dict[str, Any]] = []
    if not path or not isinstance(path, str):
        return out
    if not __import__("os").path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def load_events_from_jsonl(path: str) -> List[Event]:
    """Convierte líneas JSON tipadas en `Event`."""
    events: List[Event] = []
    for obj in _safe_jsonl(path):
        t = obj.get("type", "")
        if not isinstance(t, str):
            continue
        t = t.upper().strip()
        text = str(obj.get("text", "")).strip()
        if t in JSONL_TYPES and text:
            events.append(
                Event(
                    type=t,
                    text=text,
                    timestamp=str(obj.get("timestamp", "")),
                    source=str(obj.get("source", "")),
                    tags=list(obj.get("tags") or []),
                    meta=obj.get("meta") or {},
                )
            )
    return events


def _heuristic_event(raw: str, source_hint: str) -> Event:
    """Clasifica texto libre usando reglas léxicas."""
    text = raw.strip()
    kind = "IDEA"
    for pat, k in _LINE_PATTERNS:
        if isinstance(pat, re.Pattern) and pat.search(text):
            kind = k
            break
    return Event(type=kind, text=text, timestamp="", source=source_hint)


def load_events_from_chat_folder(folder: str) -> List[Event]:
    """Lee archivos de chat y produce eventos clasificados."""
    events: List[Event] = []
    if not folder or not __import__("os").path.isdir(folder):
        return events
    for name in sorted(__import__("os").listdir(folder)):
        path = __import__("os").path.join(folder, name)
        if not __import__("os").path.isfile(path):
            continue
        source = f"chat:{name}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    events.append(_heuristic_event(line, source))
        except Exception:
            continue
    return events


def _dedup_events(events: List[Event]) -> List[Event]:
    """Elimina duplicados preservando orden cronológico."""
    seen: set = set()
    out: List[Event] = []
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


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def events_to_model(
    events: List[Event], start_id: int = 1
) -> Tuple[List[Node], List[Edge]]:
    """Transforma eventos en nodos y aristas."""
    nodes: List[Node] = []
    edges: List[Edge] = []
    counters: Dict[str, int] = {}
    id_by_key: Dict[Tuple[str, str, str], str] = {}

    def _prefix(t: str) -> str:
        return t if t in JSONL_TYPES else "IDEA"

    for e in events:
        prefix = _prefix(e.type)
        counters[prefix] = counters.get(prefix, 0) + 1
        pid = f"{prefix}.{counters[prefix]:003d}"
        title = e.text.split("\n")[0][:90]

        # Generar summary con la función externa
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

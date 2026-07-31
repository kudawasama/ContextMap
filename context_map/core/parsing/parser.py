"""Parser de eventos normalizados desde JSONL agnóstico o chats sueltos.


Responsabilidades:
- Normalizar entradas heterogéneas.
- Clasificar heurísticamente eventos no tipados.
- Desduplicar eventos repetidos.
- Convertir eventos en el grafo conceptual (`Node` y `Edge`).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any

from context_map.core.generators import generar_summary
from context_map.core.models import Edge, Event, Node

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


def _safe_jsonl(path: str) -> list[dict[str, Any]]:
    """Lee objetos JSON desde un archivo JSONL tolerando errores de formato.

    Args:
        path (str): Ruta al archivo JSONL.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios parseados correctamente.
    """
    out: list[dict[str, Any]] = []
    if not path or not isinstance(path, str) or not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    out.append(json.loads(line_str))
                except Exception:
                    continue
    except Exception:
        pass
    return out


def load_events_from_jsonl(path: str) -> list[Event]:
    """Convierte líneas JSON tipadas en objetos Event.

    Args:
        path (str): Ruta del archivo JSONL.

    Returns:
        List[Event]: Lista de eventos normalizados.
    """
    events: list[Event] = []
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


def load_events_from_chat_folder(folder: str) -> list[Event]:
    """Lee archivos de conversaciones de chat y genera eventos clasificados.

    Args:
        folder (str): Ruta del directorio de chats.

    Returns:
        List[Event]: Eventos extraídos y clasificados.
    """
    events: list[Event] = []
    if not folder or not os.path.isdir(folder):
        return events
    try:
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            source = f"chat:{name}"
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str or len(line_str) < 8:
                            continue
                        events.append(_heuristic_event(line_str, source))
            except Exception:
                continue
    except Exception:
        pass
    return events


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

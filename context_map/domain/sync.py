from __future__ import annotations

"""Sincronización incremental del grafo de contexto.

Lee el estado existente, identifica eventos nuevos,
y solo agrega lo que falta. Nunca reescribe lo que ya existe.
"""

import json
import os
from typing import List, Set, Tuple

from context_map.core.models import Event, Node, Edge
from context_map.core.parser import (
    _dedup_events,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.store import append_jsonl, load_jsonl
from context_map.core.standardize import estandarizar_nodo


def _hash_evento(e: Event) -> str:
    """Hash simple para identificar un evento sin duplicar."""
    return f"{e.type}|{e.text[:80]}|{e.source}"


def _eventos_procesados(state_dir: str) -> Set[str]:
    """Lee los hashes de eventos ya procesados."""
    hash_file = os.path.join(state_dir, "processed_events.txt")
    if not os.path.exists(hash_file):
        return set()
    with open(hash_file, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def _guardar_evento_procesado(state_dir: str, evento_hash: str) -> None:
    """Marca un evento como procesado."""
    hash_file = os.path.join(state_dir, "processed_events.txt")
    with open(hash_file, "a", encoding="utf-8") as f:
        f.write(evento_hash + "\n")


def _cargar_estado_existente(state_dir: str) -> Tuple[List[Node], List[Edge]]:
    """Carga nodos y aristas existentes, estandarizando los nodos."""
    graph_file = os.path.join(state_dir, "graph.jsonl")
    edges_file = os.path.join(state_dir, "edges.jsonl")

    nodos_raw = [Node.from_dict(r) for r in load_jsonl(graph_file)]
    edges = [Edge.from_dict(r) for r in load_jsonl(edges_file)]

    # Estandarizar nodos existentes
    from context_map.core.standardize import estandarizar_nodo
    nodes = [estandarizar_nodo(n) for n in nodos_raw]

    return nodes, edges


def _encontrar_nodos_nuevos(
    eventos_nuevos: List[Event],
    nodos_existentes: List[Node],
) -> List[Event]:
    """Identifica eventos que no tienen nodo correspondiente.

    Compara por tipo + título para evitar que un evento de tipo
    diferente (ej. RIESGO vs IDEA) se considere duplicado aunque
    compartan texto similar.
    """
    existentes = {(n.type, n.title[:60].lower()) for n in nodos_existentes}

    nuevos = []
    for e in eventos_nuevos:
        titulo = e.text.split("\n")[0][:60].lower()
        if (e.type, titulo) not in existentes:
            nuevos.append(e)

    return nuevos


def sync_incremental(
    chats_dir: str,
    raw_dir: str,
    state_dir: str,
) -> dict:
    """Sincroniza eventos nuevos sin reescribir el estado existente.

    Retorna dict con estadísticas de la operación.
    """
    # 1. Cargar estado actual
    nodos_existentes, aristas_existentes = _cargar_estado_existente(state_dir)
    hashes_procesados = _eventos_procesados(state_dir)

    # 2. Recolectar todos los eventos de fuentes
    todos_eventos: List[Event] = []
    todos_eventos.extend(load_events_from_chat_folder(chats_dir))
    todos_eventos.extend(load_events_from_jsonl(os.path.join(raw_dir, "events.jsonl")))
    todos_eventos = _dedup_events(todos_eventos)

    # 3. Filtrar solo eventos nuevos
    eventos_nuevos = []
    for e in todos_eventos:
        h = _hash_evento(e)
        if h not in hashes_procesados:
            eventos_nuevos.append(e)

    # 4. Si no hay nada nuevo, salir
    if not eventos_nuevos:
        return {
            "nodos_existentes": len(nodos_existentes),
            "aristas_existentes": len(aristas_existentes),
            "eventos_nuevos": 0,
            "nodos_agregados": 0,
            "aristas_agregadas": 0,
        }

    # 5. Identificar qué eventos son realmente nuevos
    eventos_reales_nuevos = _encontrar_nodos_nuevos(eventos_nuevos, nodos_existentes)

    # 6. Convertir eventos nuevos a nodos
    if eventos_reales_nuevos:
        offset_id = len(nodos_existentes) + 1
        nodos_nuevos, aristas_nuevas = events_to_model(eventos_reales_nuevos, offset_id)

        # Estandarizar nodos nuevos
        nodos_nuevos = [estandarizar_nodo(n) for n in nodos_nuevos]

        # Agregar nodos al grafo
        append_jsonl(
            os.path.join(state_dir, "graph.jsonl"),
            [n.to_dict() for n in nodos_nuevos],
        )

        # Agregar aristas al grafo
        if aristas_nuevas:
            append_jsonl(
                os.path.join(state_dir, "edges.jsonl"),
                [e.to_dict() for e in aristas_nuevas],
            )
    else:
        nodos_nuevos = []
        aristas_nuevas = []

    # 7. Marcar todos los eventos como procesados
    for e in eventos_nuevos:
        _guardar_evento_procesado(state_dir, _hash_evento(e))

    # 8. Guardar TODOS los nodos estandarizados
    graph_file = os.path.join(state_dir, "graph.jsonl")
    import json
    todos_nodos = nodos_existentes + (nodos_nuevos if nodos_nuevos else [])
    with open(graph_file, "w", encoding="utf-8") as f:
        for n in todos_nodos:
            f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")

    return {
        "nodos_existentes": len(nodos_existentes),
        "aristas_existentes": len(aristas_existentes),
        "eventos_nuevos": len(eventos_nuevos),
        "nodos_agregados": len(nodos_nuevos),
        "aristas_agregadas": len(aristas_nuevas),
    }


def _hash_evento_str(evento_hash: str) -> str:
    """Wrapper para compatibilidad."""
    return evento_hash

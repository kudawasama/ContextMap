"""Sincronización incremental del grafo de contexto del dominio.


Responsable de procesar eventos entrantes preservando la idempotencia y evitando
duplicaciones o reescritura innecesaria del estado guardado.
"""

from __future__ import annotations

import json
import logging
import os
import re

from context_map.core.models import Edge, Event, Node
from context_map.core.normalization import dedup_nodes, estandarizar_nodo
from context_map.core.parsing import (
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.storage import append_jsonl, load_jsonl

logger = logging.getLogger(__name__)


def _hash_evento(e: Event) -> str:
    """Calcula un hash identitario simple para un evento.

    Args:
        e (Event): Evento a procesar.

    Returns:
        str: Identificador hash.
    """
    return f"{e.type}|{e.text[:80]}|{e.source}"


def _eventos_procesados(state_dir: str) -> set[str]:
    """Carga los hashes de eventos previamente procesados.

    Args:
        state_dir (str): Ruta al directorio de estado.

    Returns:
        Set[str]: Conjunto de hashes.
    """
    hash_file = os.path.join(state_dir, "processed_events.txt")
    if not os.path.exists(hash_file):
        return set()
    try:
        with open(hash_file, encoding="utf-8") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as err:
        logger.debug("No se pudo leer %s: %s", hash_file, err)
        return set()


def _guardar_evento_procesado(state_dir: str, evento_hash: str) -> None:
    """Persiste el hash de un evento para marcarlo como procesado.

    Args:
        state_dir (str): Directorio de estado.
        evento_hash (str): Hash del evento.
    """
    hash_file = os.path.join(state_dir, "processed_events.txt")
    os.makedirs(os.path.dirname(hash_file), exist_ok=True)
    try:
        with open(hash_file, "a", encoding="utf-8") as f:
            f.write(evento_hash + "\n")
    except Exception as err:
        logger.warning("No se pudo marcar evento como procesado en %s: %s", hash_file, err)


def _cargar_estado_existente(state_dir: str) -> tuple[list[Node], list[Edge]]:
    """Carga y estandariza los nodos y aristas existentes en el estado.

    Args:
        state_dir (str): Ruta del directorio de estado.

    Returns:
        Tuple[List[Node], List[Edge]]: Dupla con nodos y aristas.
    """
    graph_file = os.path.join(state_dir, "graph.jsonl")
    edges_file = os.path.join(state_dir, "edges.jsonl")

    nodos_raw = [Node.from_dict(r) for r in load_jsonl(graph_file)]
    edges = [Edge.from_dict(r) for r in load_jsonl(edges_file)]
    nodes = [estandarizar_nodo(n) for n in nodos_raw]

    return nodes, edges


def _encontrar_nodos_nuevos(
    eventos_nuevos: list[Event],
    nodos_existentes: list[Node],
) -> list[Event]:
    """Identifica eventos que aún no cuentan con un nodo en el grafo.

    Args:
        eventos_nuevos (List[Event]): Eventos recibidos.
        nodos_existentes (List[Node]): Nodos ya creados.

    Returns:
        List[Event]: Eventos no mapeados a nodos.
    """
    existentes = {(n.type, n.title[:60].lower()) for n in nodos_existentes}

    nuevos: list[Event] = []
    for e in eventos_nuevos:
        titulo = e.text.split("\n")[0][:60].lower()
        if (e.type, titulo) not in existentes:
            nuevos.append(e)

    return nuevos


def _depurar_nodos_obsoletos(nodos: list[Node], project_root: str = ".") -> list[Node]:
    """Filtra y elimina nodos de RIESGO obsoletos cuyos archivos referenciados ya no existen.

    Args:
        nodos (list[Node]): Nodos del grafo.
        project_root (str): Ruta raíz del proyecto.

    Returns:
        list[Node]: Lista de nodos purgada.
    """
    nodos_validos: list[Node] = []
    for n in nodos:
        if n.type == "RIESGO":
            if re.search(r"\(\d+\s+líneas\)", n.title) or re.search(r"\(\d+\s+líneas\)", n.summary):
                logger.info("Depurando nodo RIESGO con formato volátil obsoleto: %s", n.id)
                continue

            archivos = re.findall(r"([\w.\-/]+\.py)", n.title + " " + n.summary)
            if archivos:
                existe = False
                for fname in archivos:
                    if os.path.exists(os.path.join(project_root, fname)) or os.path.exists(fname):
                        existe = True
                        break
                    base = os.path.basename(fname)
                    for _root, dirs, files in os.walk(project_root):
                        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "venv", "node_modules", ".context-map")]
                        if base in files:
                            existe = True
                            break
                    if existe:
                        break
                if not existe:
                    logger.info("Depurando nodo RIESGO para archivo inexistente (%s): %s", archivos, n.id)
                    continue

        nodos_validos.append(n)
    return nodos_validos


def sync_incremental(
    chats_dir: str,
    raw_dir: str,
    state_dir: str,
) -> dict:
    """Ejecuta la sincronización incremental del grafo.

    Args:
        chats_dir (str): Ruta a carpeta de chats.
        raw_dir (str): Ruta a carpeta de JSONL crudos.
        state_dir (str): Ruta del estado del grafo.

    Returns:
        dict: Estadísticas de la sincronización.
    """
    nodos_existentes, aristas_existentes = _cargar_estado_existente(state_dir)
    nodos_existentes = _depurar_nodos_obsoletos(nodos_existentes)
    hashes_procesados = _eventos_procesados(state_dir)

    todos_eventos: list[Event] = []
    todos_eventos.extend(load_events_from_chat_folder(chats_dir))
    todos_eventos.extend(load_events_from_jsonl(os.path.join(raw_dir, "events.jsonl")))

    eventos_nuevos: list[Event] = []
    for e in todos_eventos:
        h = _hash_evento(e)
        if h not in hashes_procesados:
            eventos_nuevos.append(e)

    if not eventos_nuevos:
        graph_file = os.path.join(state_dir, "graph.jsonl")
        todos_nodos = dedup_nodes(_depurar_nodos_obsoletos(nodos_existentes))
        try:
            with open(graph_file, "w", encoding="utf-8") as f:
                for n in todos_nodos:
                    f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")
        except Exception as err:
            logger.error("No se pudo persistir el grafo limpio en %s: %s", graph_file, err)

        return {
            "nodos_existentes": len(todos_nodos),
            "aristas_existentes": len(aristas_existentes),
            "eventos_nuevos": 0,
            "nodos_agregados": 0,
            "aristas_agregadas": 0,
        }

    eventos_reales_nuevos = _encontrar_nodos_nuevos(eventos_nuevos, nodos_existentes)

    if eventos_reales_nuevos:
        offset_id = len(nodos_existentes) + 1
        nodos_nuevos, aristas_nuevas = events_to_model(eventos_reales_nuevos, offset_id)
        nodos_nuevos = [estandarizar_nodo(n) for n in nodos_nuevos]

        append_jsonl(
            os.path.join(state_dir, "graph.jsonl"),
            [n.to_dict() for n in nodos_nuevos],
        )

        if aristas_nuevas:
            append_jsonl(
                os.path.join(state_dir, "edges.jsonl"),
                [e.to_dict() for e in aristas_nuevas],
            )
    else:
        nodos_nuevos = []
        aristas_nuevas = []

    for e in eventos_nuevos:
        _guardar_evento_procesado(state_dir, _hash_evento(e))

    graph_file = os.path.join(state_dir, "graph.jsonl")
    todos_nodos = nodos_existentes + (nodos_nuevos if nodos_nuevos else [])

    # Depurar y deduplicar antes de persistir para eliminar acumulaciones históricas
    todos_nodos = _depurar_nodos_obsoletos(todos_nodos)
    todos_nodos = dedup_nodes(todos_nodos)

    try:
        with open(graph_file, "w", encoding="utf-8") as f:
            for n in todos_nodos:
                f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")
    except Exception as err:
        logger.error("No se pudo persistir el grafo en %s: %s", graph_file, err)

    return {
        "nodos_existentes": len(todos_nodos),
        "aristas_existentes": len(aristas_existentes),
        "eventos_nuevos": len(eventos_nuevos),
        "nodos_agregados": len(nodos_nuevos),
        "aristas_agregadas": len(aristas_nuevas),
    }

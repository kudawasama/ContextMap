"""Commands: Comandos del CLI unificados.

Todos los comandos están registrados aquí para evitar fragmentación.
Cada comando es una función que recibe argparse.Namespace.
"""

from __future__ import annotations

import os
import sys
from typing import List

from context_map.core.models import Event, Node, Edge
from context_map.core.parser import (
    _dedup_events,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.store import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)
from context_map.presentation.writer import render_active_map, render_obsidian_vault
from context_map.presentation.brief import generar_brief
from context_map.domain.sync import sync_incremental
from context_map.domain.scanner import escanear_y_generar_eventos, guardar_eventos_escaneados
from context_map.domain.checker import analizar_readiness, formatear_readiness
from context_map.domain.reporter import generar_semanal, guardar_reporte
from context_map.infrastructure.integrations.git import leer_historial_git
from context_map.infrastructure.integrations.hermes import importar_sesiones
from context_map.infrastructure.integrations.chat_export import importar_chat
from context_map.infrastructure.integrations.antigravity import importar_antigravity

# Constantes de directorios
CONTEXT_DIR = ".context-map"
STATE_DIR = os.path.join(CONTEXT_DIR, "state")
MAPS_DIR = os.path.join(CONTEXT_DIR, "maps")
HISTORY_DIR = os.path.join(CONTEXT_DIR, "maps", "HISTORY")
CHATS_DIR = os.path.join(CONTEXT_DIR, "chats")
RAW_DIR = os.path.join(CONTEXT_DIR, "raw")
VAULT_DIR = os.path.join(CONTEXT_DIR, "vault")


def _ahora() -> str:
    """Timestamp actual."""
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _ensure_dirs() -> None:
    """Prepara el árbol de directorios."""
    for p in [STATE_DIR, MAPS_DIR, HISTORY_DIR, CHATS_DIR, RAW_DIR, VAULT_DIR]:
        os.makedirs(p, exist_ok=True)


def _append_nodes_edges(nodes: List[Node], edges: List[Edge]) -> None:
    """Persiste nodos y aristas como JSONL."""
    append_jsonl(os.path.join(STATE_DIR, "graph.jsonl"), [n.to_dict() for n in nodes])
    append_jsonl(os.path.join(STATE_DIR, "edges.jsonl"), [e.to_dict() for e in edges])


def _collect_events():
    """Reune eventos desde carpetas."""
    events = []
    events.extend(load_events_from_chat_folder(CHATS_DIR))
    events.extend(load_events_from_jsonl(os.path.join(RAW_DIR, "events.jsonl")))
    return _dedup_events(events)


def _do_sync(args, project_name=None):
    """Ejecuta sync y regenera vault."""
    stats = sync_incremental(
        chats_dir=CHATS_DIR,
        raw_dir=RAW_DIR,
        state_dir=STATE_DIR,
    )

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(project_name or "Repo", nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(project_name or "Repo", nodes, edges, vault_dir)

    print(f"sync: nodos {stats['nodos_existentes']} → {stats['nodos_existentes'] + stats['nodos_agregados']}")
    print(f"vault: {vault_dir}")
    return nodes, edges


# === COMANDOS ===

def cmd_init(_args):
    """Crea el directorio .context-map."""
    _ensure_dirs()
    print("init:ok ->", os.path.abspath(CONTEXT_DIR))


def cmd_build(args):
    """Genera el mapa contextual y snapshot."""
    _ensure_dirs()
    extra_events = _collect_events()
    if extra_events:
        nodes, edges = events_to_model(extra_events)
        # Estandarizar nodos nuevos antes de persistir
        from context_map.core.standardize import estandarizar_nodos
        nodes = estandarizar_nodos(nodes)
        _append_nodes_edges(nodes, edges)

    # Cargar nodos y re-estandarizar todo (por si quedaron viejos)
    from context_map.core.standardize import estandarizar_nodo
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [estandarizar_nodo(Node.from_dict(r)) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(args.project or "Repo", nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(args.project or "Repo", nodes, edges, vault_dir)

    # Snapshot
    snapshot_name = getattr(args, "snapshot_name", "") or None
    snap = snapshot_map(nodes=nodes, edges=edges, name=snapshot_name)
    if snap:
        print(f"snapshot: {snap}")

    # Brief si se pide
    if getattr(args, "brief", False):
        brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
        readiness = analizar_readiness(".")
        generar_brief(args.project or "Repo", nodes, edges, readiness.score, brief_path)
        print(f"brief: {brief_path}")

    print("build:ok -> ACTIVE.md")
    print(f"vault:ok -> {vault_dir}")


def cmd_scan(args):
    """Escanea el proyecto y genera eventos."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Escaneando: {os.path.abspath(ruta)}")

    eventos = escanear_y_generar_eventos(ruta)

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        _do_sync(args, args.project)


def cmd_sync(args):
    """Sync incremental."""
    _ensure_dirs()
    _do_sync(args, args.project)


def cmd_check(args):
    """Verifica readiness del proyecto."""
    ruta = args.target or os.getcwd()
    resultado = analizar_readiness(ruta)
    print(formatear_readiness(resultado))


def cmd_import_git(args):
    """Importa historial de git."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Leyendo historial git de: {os.path.abspath(ruta)}")

    history = leer_historial_git(ruta, limite=args.limit or 50)

    if not history.commits:
        print("No se encontraron commits o no es un repositorio git")
        return

    print(f"Commits encontrados: {len(history.commits)}")
    print(f"Tags: {len(history.tags)}")

    eventos = [
        Event(
            type="BASE",
            text=f"Repositorio git con {history.total_commits} commits totales, branch: {history.branch_actual}",
            timestamp=_ahora(),
            source="git",
            tags=["git", "repo"],
        )
    ]

    for commit in history.commits[:20]:
        msg_lower = commit.mensaje.lower()
        if any(kw in msg_lower for kw in ["fix", "bug", "correc", "patch"]):
            tipo = "CORRECCION"
        elif any(kw in msg_lower for kw in ["feat", "add", "nuevo", "new"]):
            tipo = "IDEA"
        elif any(kw in msg_lower for kw in ["test", "qa"]):
            tipo = "PRUEBA"
        elif any(kw in msg_lower for kw in ["doc", "readme", "changelog"]):
            tipo = "CAMBIO"
        else:
            tipo = "CAMBIO"

        eventos.append(Event(
            type=tipo,
            text=f"[{commit.sha[:7]}] {commit.mensaje}",
            timestamp=commit.fecha or _ahora(),
            source="git",
            tags=["commit", tipo.lower()],
        ))

    for tag in history.tags[:10]:
        eventos.append(Event(
            type="HITO",
            text=f"Release tag: {tag}",
            timestamp=_ahora(),
            source="git",
            tags=["tag", "release"],
        ))

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        _do_sync(args, args.project)


def cmd_import_sessions(args):
    """Importa sesiones de Hermes."""
    _ensure_dirs()

    print("Buscando base de datos de sesiones...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_sesiones(
        db_path=args.db,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Sesiones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, args.project)


def cmd_import_chat(args):
    """Importa un archivo de chat."""
    _ensure_dirs()

    if not args.file:
        print("Error: especifica un archivo con --file")
        return

    print(f"Importando chat: {args.file}")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_chat(args.file, output)

    print(f"Eventos importados: {importados}")

    if importados > 0:
        _do_sync(args, args.project)


def cmd_weekly(args):
    """Genera reporte semanal."""
    _ensure_dirs()

    dias = args.days or 7
    output = os.path.join(MAPS_DIR, f"semanal-{dias}d.md")

    print(f"Generando reporte de los últimos {dias} días...")

    reporte = guardar_reporte(STATE_DIR, output, dias)

    print(f"Reporte generado: {reporte}")
    print("")
    with open(reporte, "r", encoding="utf-8") as f:
        lineas = f.readlines()[:30]
        print("".join(lineas))


def cmd_watch(args):
    """Observa cambios y regenera."""
    print(f"Observando cambios cada {args.interval} segundos... (Ctrl+C para salir)")

    import time
    last_mtime = 0

    while True:
        graph_path = os.path.join(STATE_DIR, "graph.jsonl")
        if os.path.exists(graph_path):
            current_mtime = os.path.getmtime(graph_path)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                print("Detectado cambio, regenerando...")
                try:
                    _do_sync(args, "Repo")
                except Exception as e:
                    print(f"Error: {e}")
        time.sleep(args.interval)


def cmd_brief(args):
    """Genera brief para agentes de IA."""
    _ensure_dirs()

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    if not nodes:
        print("No hay nodos. Ejecuta 'ctxmap build' primero.")
        return

    readiness = analizar_readiness(".")
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")

    generar_brief(args.project or "Repo", nodes, edges, readiness.score, brief_path)
    print(f"brief:ok -> {brief_path}")


def cmd_import_antigravity(args):
    """Importa chats de Antigravity IDE."""
    _ensure_dirs()

    print("Importando conversaciones de Antigravity IDE...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_antigravity(
        ide=True,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Conversaciones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, args.project)


def cmd_import_antigravity2(args):
    """Importa chats de Antigravity 2.0."""
    _ensure_dirs()

    print("Importando conversaciones de Antigravity 2.0...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_antigravity(
        ide=False,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Conversaciones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, args.project)

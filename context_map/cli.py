from __future__ import annotations

"""Entrada/salida principal del CLI `ctxmap`.

Comandos:
- init: crea el directorio del mapa contextual.
- build: ingesta eventos desde `chats/` y `raw/`, genera vista y snapshot.
- watch: recompila el mapa cuando cambia `graph.jsonl`.
"""

import argparse
import time
import os
from typing import List

from context_map.models import Event, Node, Edge
from context_map.parser import (
    _dedup_events,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.store import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)
from context_map.writer import render_active_map, render_obsidian_vault
from context_map.sync import sync_incremental
from context_map.scanner import escanear_y_generar_eventos, guardar_eventos_escaneados
from context_map.integrations.git import leer_historial_git, CommitInfo


def _ahora() -> str:
    """Timestamp actual."""
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


CONTEXT_DIR = ".context-map"
STATE_DIR = os.path.join(CONTEXT_DIR, "state")
MAPS_DIR = os.path.join(CONTEXT_DIR, "maps")
HISTORY_DIR = os.path.join(CONTEXT_DIR, "maps", "HISTORY")
CHATS_DIR = os.path.join(CONTEXT_DIR, "chats")
RAW_DIR = os.path.join(CONTEXT_DIR, "raw")
VAULT_DIR = os.path.join(CONTEXT_DIR, "vault")


def _ensure_dirs() -> None:
    """Prepara el árbol de directorios del mapa contextual."""
    for p in [STATE_DIR, MAPS_DIR, HISTORY_DIR, CHATS_DIR, RAW_DIR, VAULT_DIR]:
        os.makedirs(p, exist_ok=True)


def _append_nodes_edges(nodes: List[Node], edges: List[Edge]) -> None:
    """Persiste nodos y aristas como JSONL append-only."""
    append_jsonl(os.path.join(STATE_DIR, "graph.jsonl"), [n.to_dict() for n in nodes])
    append_jsonl(os.path.join(STATE_DIR, "edges.jsonl"), [e.to_dict() for e in edges])


def _collect_events() -> List[Event]:
    """Reune eventos desde carpetas de chat y JSONL, sin duplicados."""
    events: List[Event] = []
    events.extend(load_events_from_chat_folder(CHATS_DIR))
    events.extend(load_events_from_jsonl(os.path.join(RAW_DIR, "events.jsonl")))
    return _dedup_events(events)


def cmd_init(_args: argparse.Namespace) -> None:
    """Crea el directorio `.context-map` en el repo actual."""
    _ensure_dirs()
    print("init:ok ->", os.path.abspath(CONTEXT_DIR))


def cmd_build(args: argparse.Namespace) -> None:
    """Genera el mapa contextual activo y un snapshot histórico."""
    _ensure_dirs()
    extra_events = _collect_events()
    if extra_events:
        nodes, edges = events_to_model(extra_events)
        _append_nodes_edges(nodes, edges)
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]
    if not nodes:
        seed_events = [
            Event(
                type="BASE",
                text="Repositorio base para generador de mapa mental contextual",
                source="seed",
                timestamp="2026-07-24T00:00:00",
            ),
            Event(
                type="IDEA",
                text="Mapa mental conectado por nodos y aristas, separando ideas, pruebas, futuro y riesgos",
                source="seed",
                timestamp="2026-07-24T00:00:00",
            ),
            Event(
                type="CAMBIO",
                text="Formato agnóstico para múltiples agentes e IDEs",
                source="seed",
                timestamp="2026-07-24T00:00:00",
            ),
        ]
        nodes, edges = events_to_model(seed_events)
        _append_nodes_edges(nodes, edges)
    md = render_active_map(args.project or "Repo", nodes, edges)
    write_map(md)
    snapshot_path = snapshot_map(
        name=(args.snapshot_name or "").strip() or None,
        nodes=nodes,
        edges=edges,
    )

    # Generar vault Obsidian
    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(args.project or "Repo", nodes, edges, vault_dir)

    # Generar diagrama Mermaid si se pide
    if getattr(args, 'mermaid', False):
        from context_map.writer import render_mermaid
        mermaid_md = render_mermaid(nodes, edges)
        mermaid_path = os.path.join(vault_dir, "00-GRAPH.md")
        with open(mermaid_path, "w", encoding="utf-8") as f:
            f.write(f"---\ntype: graph\ntitle: Grafo de conexiones\n---\n\n# Grafo de conexiones\n\n{mermaid_md}\n")

    print("build:ok -> ACTIVE.md")
    print("vault:ok ->", vault_dir)
    if snapshot_path:
        print("snapshot:", os.path.relpath(snapshot_path))


def cmd_watch(args: argparse.Namespace) -> None:
    """Observa `graph.jsonl` y recompila cuando cambia."""
    print("watch: iniciando... Ctrl+C para salir")
    last = ""
    while True:
        try:
            path = os.path.join(STATE_DIR, "graph.jsonl")
            cur = ""
            if os.path.exists(path):
                cur = open(path, "rb").read().decode("utf-8", errors="ignore")[-1000:]
            if cur != last:
                cmd_build(args)
                last = cur
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nwatch:stop")
            break


def cmd_sync(args: argparse.Namespace) -> None:
    """Sincroniza eventos nuevos sin reescribir el estado existente."""
    _ensure_dirs()

    stats = sync_incremental(
        chats_dir=CHATS_DIR,
        raw_dir=RAW_DIR,
        state_dir=STATE_DIR,
    )

    if stats["eventos_nuevos"] == 0:
        print("sync: sin eventos nuevos")
        return

    # Regenerar vault con el estado actualizado
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(args.project or "Repo", nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(args.project or "Repo", nodes, edges, vault_dir)

    print(f"sync:ok -> {stats['eventos_nuevos']} eventos nuevos")
    print(f"  nodos: {stats['nodos_existentes']} → {stats['nodos_existentes'] + stats['nodos_agregados']}")
    print(f"  aristas: {stats['aristas_existentes']} → {stats['aristas_existentes'] + stats['aristas_agregadas']}")
    print(f"  vault: {vault_dir}")


def cmd_scan(args: argparse.Namespace) -> None:
    """Escanea el proyecto y genera eventos automáticamente."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Escaneando: {os.path.abspath(ruta)}")

    eventos = escanear_y_generar_eventos(ruta)
    print(f"Eventos generados: {len(eventos)}")

    # Guardar en events.jsonl
    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    # Ejecutar sync para procesarlos
    if guardados > 0:
        stats = sync_incremental(
            chats_dir=CHATS_DIR,
            raw_dir=RAW_DIR,
            state_dir=STATE_DIR,
        )

        # Regenerar vault
        records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
        e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
        nodes = [Node.from_dict(r) for r in records]
        edges = [Edge.from_dict(r) for r in e_records]

        md = render_active_map(args.project or "Repo", nodes, edges)
        write_map(md)

        vault_dir = os.path.join(CONTEXT_DIR, "vault")
        render_obsidian_vault(args.project or "Repo", nodes, edges, vault_dir)

        print(f"sync: nodos {stats['nodos_existentes']} -> {stats['nodos_existentes'] + stats['nodos_agregados']}")
        print(f"vault: {vault_dir}")
    else:
        print("Sin eventos nuevos")


def cmd_import_git(args: argparse.Namespace) -> None:
    """Importa historial de git como eventos."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Leyendo historial git de: {os.path.abspath(ruta)}")

    history = leer_historial_git(ruta, limite=args.limit or 50)

    if not history.commits:
        print("No se encontraron commits o no es un repositorio git")
        return

    print(f"Commits encontrados: {len(history.commits)}")
    print(f"Tags: {len(history.tags)}")

    # Convertir commits a eventos
    eventos = []

    # Evento BASE del repo
    eventos.append(Event(
        type="BASE",
        text=f"Repositorio git con {history.total_commits} commits totales, branch: {history.branch_actual}",
        timestamp=_ahora(),
        source="git",
        tags=["git", "repo"],
    ))

    # Eventos por commits recientes (últimos 20)
    for commit in history.commits[:20]:
        # Clasificar commit por mensaje
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

    # Eventos por tags
    for tag in history.tags[:10]:
        eventos.append(Event(
            type="HITO",
            text=f"Release tag: {tag}",
            timestamp=_ahora(),
            source="git",
            tags=["tag", "release"],
        ))

    # Guardar
    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    # Sync
    if guardados > 0:
        stats = sync_incremental(
            chats_dir=CHATS_DIR,
            raw_dir=RAW_DIR,
            state_dir=STATE_DIR,
        )

        records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
        e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
        nodes = [Node.from_dict(r) for r in records]
        edges = [Edge.from_dict(r) for r in e_records]

        md = render_active_map(args.project or "Repo", nodes, edges)
        write_map(md)

        vault_dir = os.path.join(CONTEXT_DIR, "vault")
        render_obsidian_vault(args.project or "Repo", nodes, edges, vault_dir)

        print(f"sync: nodos {stats['nodos_existentes']} → {stats['nodos_existentes'] + stats['nodos_agregados']}")
        print(f"vault: {vault_dir}")


def main() -> None:
    p = argparse.ArgumentParser(prog="ctxmap")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("init")

    s_build = sub.add_parser("build")
    s_build.add_argument("--project", default="Repo")
    s_build.add_argument("--snapshot-name", default="")
    s_build.add_argument("--mermaid", action="store_true", help="Generar diagrama Mermaid")

    s_sync = sub.add_parser("sync")
    s_sync.add_argument("--project", default="Repo")

    s_scan = sub.add_parser("scan")
    s_scan.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a escanear")
    s_scan.add_argument("--project", default="Repo")

    s_git = sub.add_parser("import-git")
    s_git.add_argument("target", nargs="?", default=".", help="Ruta del repositorio")
    s_git.add_argument("--project", default="Repo")
    s_git.add_argument("--limit", type=int, default=50, help="Máximo de commits")

    s_watch = sub.add_parser("watch")
    s_watch.add_argument("--interval", type=int, default=10)

    args = p.parse_args()
    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "build":
        cmd_build(args)
    elif args.cmd == "sync":
        cmd_sync(args)
    elif args.cmd == "scan":
        cmd_scan(args)
    elif args.cmd == "import-git":
        cmd_import_git(args)
    elif args.cmd == "watch":
        cmd_watch(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

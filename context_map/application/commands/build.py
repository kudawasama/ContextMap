"""Comando build: genera el mapa contextual, vault y snapshots.

Responsable de la construcción completa del vault Obsidian
a partir de eventos recopilados y nodos existentes.
"""

from __future__ import annotations

import os

from context_map.core.models import Node, Edge
from context_map.core.store import load_jsonl, snapshot_map, write_map
from context_map.core.parser import events_to_model
from context_map.presentation.writer import render_active_map, render_obsidian_vault
from context_map.presentation.brief import generar_brief
from context_map.domain.checker import analizar_readiness

from context_map.application.commands._helpers import (
    CONTEXT_DIR,
    STATE_DIR,
    ensure_dirs,
    resolve_vault_mode,
    clean_vault_dir,
    collect_events,
    append_nodes_edges,
    project_name,
)


def cmd_build(args) -> None:
    """Genera el mapa contextual completo y snapshot.

    Flujo:
        1. Recopilar eventos desde chats y raw
        2. Estandarizar nodos
        3. Generar ACTIVE.md y vault Obsidian
        4. Crear snapshot histórico
        5. Opcionalmente generar brief para agentes

    Args:
        args: Namespace de argparse con flags --mode, --raw, --clean, --brief, etc.
    """
    ensure_dirs()

    # Resolver modo del vault y aplicar limpieza si se solicitó
    vault_mode = resolve_vault_mode(args)
    if getattr(args, "clean", False):
        clean_vault_dir()

    extra_events = collect_events()
    if extra_events:
        nodes, edges = events_to_model(extra_events)
        # Estandarizar nodos nuevos antes de persistir
        from context_map.core.standardize import estandarizar_nodos
        nodes = estandarizar_nodos(nodes)
        append_nodes_edges(nodes, edges)

    # Cargar nodos y re-estandarizar todo (por si quedaron viejos)
    from context_map.core.standardize import estandarizar_nodo
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [estandarizar_nodo(Node.from_dict(r)) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(project_name(args), nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(project_name(args), nodes, edges, vault_dir, mode=vault_mode)

    # Snapshot
    snapshot_name = getattr(args, "snapshot_name", "") or None
    snap = snapshot_map(nodes=nodes, edges=edges, name=snapshot_name)
    if snap:
        print(f"snapshot: {snap}")

    # Brief si se pide
    if getattr(args, "brief", False):
        brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
        readiness = analizar_readiness(".")
        generar_brief(project_name(args), nodes, edges, readiness.score, brief_path)
        print(f"brief: {brief_path}")

    print("build:ok -> ACTIVE.md")
    print(f"vault ({vault_mode}):ok -> {vault_dir}")

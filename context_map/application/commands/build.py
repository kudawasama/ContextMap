"""Comando build: genera el mapa contextual, vault y snapshots.

Responsable de la construcción completa del vault Obsidian
a partir de eventos recopilados y nodos existentes.
"""

from __future__ import annotations

import json
import os

from context_map.application.commands._helpers import (
    CONTEXT_DIR,
    STATE_DIR,
    append_nodes_edges,
    clean_vault_dir,
    collect_events,
    ensure_dirs,
    project_name,
    resolve_vault_mode,
    vault_dir,
)
from context_map.core.models import Edge, Node
from context_map.core.parsing import events_to_model
from context_map.core.storage import load_jsonl, snapshot_map, write_map
from context_map.domain.analysis import analizar_readiness
from context_map.presentation.briefs import generar_brief, generar_instrucciones_agentes
from context_map.presentation.vault import render_active_map, render_obsidian_vault


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
    proj = project_name(args)
    ensure_dirs(proj)

    # Resolver modo del vault y aplicar limpieza si se solicitó
    vault_mode = resolve_vault_mode(args)
    if getattr(args, "clean", False):
        clean_vault_dir(proj)

    extra_events = collect_events()
    if extra_events:
        nodes, edges = events_to_model(extra_events)
        # Estandarizar nodos nuevos antes de persistir
        from context_map.core.normalization import estandarizar_nodo, estandarizar_nodos
        nodes = estandarizar_nodos(nodes)
        append_nodes_edges(nodes, edges)

    # Cargar nodos y re-estandarizar todo (por si quedaron viejos)
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [estandarizar_nodo(Node.from_dict(r)) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    # Deduplicar y re-persistir el estado limpio
    from context_map.core.normalization import dedup_nodes
    nodos_dedup = dedup_nodes(nodes)
    if len(nodos_dedup) < len(nodes):
        graph_file = os.path.join(STATE_DIR, "graph.jsonl")
        with open(graph_file, "w", encoding="utf-8") as f:
            for n in nodos_dedup:
                f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")
        print(f"dedup: {len(nodes)} -> {len(nodos_dedup)} nodos (eliminados {len(nodes) - len(nodos_dedup)})")
        nodes = nodos_dedup

    md = render_active_map(project_name(args), nodes, edges)
    write_map(md)

    vault_path = vault_dir(proj)
    render_obsidian_vault(proj, nodes, edges, vault_path, mode=vault_mode)

    # Snapshot
    snapshot_name = getattr(args, "snapshot_name", "") or None
    snap = snapshot_map(nodes=nodes, edges=edges, name=snapshot_name)
    if snap:
        print(f"snapshot: {snap}")

    # Brief y AGENTS.md si se pide
    if getattr(args, "brief", False):
        brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
        readiness = analizar_readiness(".")
        generar_brief(proj, nodes, edges, readiness.score, brief_path)
        agents_path = generar_instrucciones_agentes(proj, target_dir=".", overwrite_if_exists=False)
        print(f"brief: {brief_path}")
        print(f"agents: {agents_path}")

    print("build:ok -> ACTIVE.md")
    print(f"vault ({vault_mode}):ok -> {vault_path}")

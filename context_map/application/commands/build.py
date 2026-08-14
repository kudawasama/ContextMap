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
    registrar_build_info,
    resolve_vault_mode,
    vault_dir,
)
from context_map.core.models import Edge, Node
from context_map.core.parsing import events_to_model
from context_map.core.storage import load_jsonl, snapshot_map, write_map
from context_map.domain.analysis import analizar_readiness
from context_map.presentation.briefs import (
    generar_brief,
    generar_instrucciones_agentes,
    generar_skill_contextmap,
)
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

    # Punto de control de versión (2026-08-11): aviso pre-actualización.
    # refresh pasa aviso_pre=False para no duplicar (él ya lo imprime al inicio).
    if getattr(args, "aviso_pre", True) and not getattr(args, "quiet", False):
        from context_map.infrastructure.version_check import aviso_pre_actualizacion

        print(aviso_pre_actualizacion(), end="")

    # Memoria viva por commit (R2, 2026-08-14): si se pide --import-sessions
    # (el pre-commit hook lo usa), importa las sesiones recientes de Hermes
    # del proyecto antes de construir — idempotente y tolerante, nunca rompe
    # el build (misma lógica que refresh).
    if getattr(args, "import_sessions", False):
        try:
            from context_map.application.commands._helpers import project_name as _pn
            from context_map.infrastructure.integrations.hermes import importar_sesiones

            importados = importar_sesiones(
                db_path=None,
                limite=5,
                output_path=os.path.join(".context-map", "raw", "events.jsonl"),
                project=_pn(args),
            )
            if importados and not getattr(args, "quiet", False):
                print(f"[build] {importados} evento(s) de sesiones importados")
        except Exception as err:  # noqa: BLE001 — nunca romper el build por el import
            if not getattr(args, "quiet", False):
                print(f"[build] aviso: no se pudieron importar sesiones ({err})")

    # Resolver modo del vault y aplicar limpieza si se solicitó
    vault_mode = resolve_vault_mode(args)
    if getattr(args, "clean", False):
        manuales = clean_vault_dir(proj)
        registrar_build_info(proj, clean=True, manuales_preservadas=manuales)
    else:
        registrar_build_info(proj, clean=False)

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

    # Snippet CSS: etiquetas con color por contexto (se activa solo)
    from context_map.presentation.vault.consolidated.common import (
        generar_color_groups,
        generar_snippet_etiquetas,
    )

    try:
        snippet = generar_snippet_etiquetas(vault_path)
        if snippet:
            print(f"tags: {snippet}")
    except Exception as err:  # noqa: BLE001 — no romper el build por el snippet
        print(f"tags: (sin snippet) {err}")

    try:
        grafo = generar_color_groups(vault_path)
        if grafo:
            print(f"graph-groups: {grafo}")
    except Exception as err:  # noqa: BLE001
        print(f"graph-groups: (sin grupos) {err}")

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
        skill_path = generar_skill_contextmap(proj, target_dir=".")
        print(f"brief: {brief_path}")
        print(f"agents: {agents_path}")
        print(f"skill: {skill_path}")

    # Auto-adaptación del ecosistema agéntico tras cada build (solo crea reglas faltantes)
    from context_map.application.commands.adapt import do_adapt
    do_adapt(target=".", project_name=proj, modo="respect", quiet=True)

    print("build:ok -> ACTIVE.md")
    print(f"vault ({vault_mode}):ok -> {vault_path}")

    # Aviso de actualización pendiente (caché 24h, sin bloquear)
    from context_map.infrastructure.version_check import aviso_actualizacion

    print(aviso_actualizacion())

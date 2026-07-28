"""Comandos sync: sincronización incremental y migración.

Contiene la lógica compartida de sync (_do_sync) utilizada
por múltiples comandos, además de los comandos cmd_sync y cmd_sync_migrate.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional, Tuple

from context_map.core.models import Node, Edge
from context_map.core.store import load_jsonl, write_map
from context_map.presentation.writer import render_active_map, render_obsidian_vault
from context_map.presentation.brief import generar_brief
from context_map.domain.sync import sync_incremental
from context_map.domain.checker import analizar_readiness

from context_map.application.commands._helpers import (
    CONTEXT_DIR,
    STATE_DIR,
    CHATS_DIR,
    RAW_DIR,
    ensure_dirs,
    resolve_vault_mode,
    clean_vault_dir,
    project_name,
)


def do_sync(
    args,
    proj_name: Optional[str] = None,
    mode: str = "consolidated",
) -> Tuple[List[Node], List[Edge]]:
    """Ejecuta sincronización incremental y regenera vault.

    Función compartida utilizada por cmd_sync, cmd_scan y los importers.

    Args:
        args: Namespace de argparse (se usa para extraer --clean)
        proj_name: Nombre del proyecto (fallback: 'Repo')
        mode: Modo de generación del vault ('consolidated' o 'raw')

    Returns:
        Tupla con (nodos, aristas) resultantes
    """
    # Limpieza previa si se solicitó
    if getattr(args, "clean", False):
        clean_vault_dir()

    stats = sync_incremental(
        chats_dir=CHATS_DIR,
        raw_dir=RAW_DIR,
        state_dir=STATE_DIR,
    )

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(proj_name or "Repo", nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(proj_name or "Repo", nodes, edges, vault_dir, mode=mode)

    print(f"sync: nodos {stats['nodos_existentes']} -> {stats['nodos_existentes'] + stats['nodos_agregados']}")
    print(f"vault ({mode}): {vault_dir}")
    return nodes, edges


def cmd_sync(args) -> None:
    """Sync incremental del proyecto.

    Args:
        args: Namespace de argparse con flags --mode, --raw, --clean
    """
    ensure_dirs()
    vault_mode = resolve_vault_mode(args)
    do_sync(args, project_name(args), mode=vault_mode)


def cmd_sync_migrate(args) -> None:
    """Sincroniza un proyecto existente con la nueva versión de ContextMap.

    Aplica estandarización a todos los nodos y regenera vault y brief.

    Args:
        args: Namespace de argparse con atributo opcional ``project``
    """
    ensure_dirs()

    print("Sincronizando proyecto con nueva version...")
    print()

    # 1. Cargar estado actual
    graph_file = os.path.join(STATE_DIR, "graph.jsonl")
    edges_file = os.path.join(STATE_DIR, "edges.jsonl")

    if not os.path.exists(graph_file):
        print("No se encontro estado del proyecto.")
        print("   Ejecuta: ctxmap scan . && ctxmap build --project 'Nombre'")
        return

    # 2. Cargar nodos
    records = load_jsonl(graph_file)
    edges_records = load_jsonl(edges_file)

    if not records:
        print("No hay nodos en el estado.")
        return

    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in edges_records]

    print(f"Estado actual: {len(nodes)} nodos, {len(edges)} aristas")
    print()

    # 3. Aplicar estandarización
    from context_map.core.standardize import estandarizar_nodos
    nodes_estandarizados = estandarizar_nodos(nodes)

    # 4. Guardar cambios
    with open(graph_file, "w", encoding="utf-8") as f:
        for n in nodes_estandarizados:
            f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")

    print("Nodos estandarizados")
    print()

    # 5. Regenerar vault
    proj = getattr(args, "project", None) or "Repo"
    vault_dir = os.path.join(CONTEXT_DIR, "vault")

    render_obsidian_vault(proj, nodes_estandarizados, edges, vault_dir)
    print(f"Vault regenerado: {vault_dir}")

    # 6. Regenerar brief
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
    readiness = analizar_readiness(".")
    generar_brief(proj, nodes_estandarizados, edges, readiness.score, brief_path)
    print(f"Brief regenerado: {brief_path}")

    # 7. Resumen
    print()
    print("Resumen de cambios:")
    print(f"   - Nodos estandarizados: {len(nodes_estandarizados)}")
    print(f"   - Vault regenerado: {vault_dir}")
    print(f"   - Brief regenerado: {brief_path}")
    print()
    print("Para verificar: ctxmap check .")
    print("Para reconstruir completo: ctxmap build --project 'Nombre'")

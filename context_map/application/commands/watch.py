"""Comando CLI 'watch' para monitoreo continuo en segundo plano."""

from __future__ import annotations

import sys
from typing import Any

from context_map.domain.synchronization.watcher import iniciar_watcher


def cmd_watch(args: dict[str, Any]) -> None:
    """Manejador del comando CLI `ctxmap watch`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI.
    """
    target_dir = args.get("target_dir") or "."
    debounce_ms = int(args.get("debounce_ms") or 500)

    print(f"👀 [watcher] Iniciando monitoreo autónomo en segundo plano: {target_dir}")
    print(f"   Debounce: {debounce_ms}ms · Presiona Ctrl+C para salir.")

    try:
        iniciar_watcher(project_dir=target_dir, debounce_ms=debounce_ms)
    except KeyboardInterrupt:
        print("\n👋 [watcher] Monitoreo detenido.")
        sys.exit(0)

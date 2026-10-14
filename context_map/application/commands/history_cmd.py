"""Comando CLI 'history' para inspeccionar y podar `.context-map/maps/HISTORY/`.

Se añade tras el incidente 2026-10-13, cuando el historial de snapshots creció
sin cota (103.354 archivos / 148 GB) y llenó la raíz del servidor. Aunque
`snapshot_map` ya poda automáticamente, el comando da visibilidad y control
manual (dry-run incluido) sin depender de scripts externos.
"""

from __future__ import annotations

import json
import os
from typing import Any

from context_map.core.storage.config_loader import load_project_config
from context_map.core.storage.history import (
    HISTORY_DIR,
    KEEP_DEFAULT,
    MAX_MB_DEFAULT,
    estadisticas,
    podar,
)


def _dir_historial(target_dir: str) -> str:
    """Resuelve el directorio del historial para el proyecto indicado.

    Args:
        target_dir (str): Ruta del proyecto.

    Returns:
        str: Ruta al directorio `maps/HISTORY` del proyecto.
    """
    if not target_dir or target_dir == ".":
        return HISTORY_DIR
    return os.path.join(target_dir, HISTORY_DIR)


def cmd_history(args: dict[str, Any]) -> None:
    """Manejador del comando `ctxmap history <list|prune>`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI. Claves: `action`
            ('list' o 'prune'), `target_dir`, `keep`, `max_mb`, `dry_run`, `json`.
    """
    accion = (args.get("action") or "list").lower()
    as_json = bool(args.get("json", False))
    target_dir = args.get("target_dir") or "."
    hist_dir = _dir_historial(target_dir)
    cfg = load_project_config(target_dir)
    stats = estadisticas(hist_dir)

    if accion == "list":
        if as_json:
            print(json.dumps(
                {
                    "dir": hist_dir,
                    "files": stats.files,
                    "bytes": stats.bytes,
                    "mb": stats.mb,
                    "max_snapshots": cfg.max_snapshots,
                    "history_max_mb": cfg.history_max_mb,
                },
                indent=2,
                ensure_ascii=False,
            ))
            return
        print(f"\n🗂️  Historial: {hist_dir}")
        print(f"   Snapshots: {stats.files} · Tamaño: {stats.mb} MB")
        print(f"   Retención configurada: {cfg.max_snapshots} snapshots / {cfg.history_max_mb} MB")
        return

    if accion == "prune":
        keep = int(args.get("keep") or cfg.max_snapshots)
        max_mb = int(args.get("max_mb") or cfg.history_max_mb)
        dry_run = bool(args.get("dry_run", False))
        res = podar(hist_dir, keep=keep, max_mb=max_mb, dry_run=dry_run)
        if as_json:
            print(json.dumps(
                {
                    "dir": hist_dir,
                    "borrados": len(res.borrados),
                    "liberado_mb": res.liberado_mb,
                    "restantes": res.restantes,
                    "keep": keep,
                    "max_mb": max_mb,
                    "dry_run": dry_run,
                },
                indent=2,
                ensure_ascii=False,
            ))
            return
        etiqueta = "(simulación)" if dry_run else ""
        print(
            f"🧹 Poda {etiqueta}: {len(res.borrados)} snapshots · "
            f"{res.liberado_mb} MB liberados · {res.restantes} restantes "
            f"(tope {keep} / {max_mb} MB)"
        )
        return

    print(f"⚠️  Acción desconocida: {accion}. Usa 'list' o 'prune'.")

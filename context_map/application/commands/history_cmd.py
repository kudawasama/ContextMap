"""Comando CLI 'history' para inspeccionar y podar `.context-map/maps/HISTORY/`.

Se añade tras el incidente 2026-10-13 (103.354 archivos / 148 GB de historial en
el servidor «kudawa»): la retención existía en `snapshot_map` pero no había forma
de inspeccionarla ni de provocarla a mano sin esperar al siguiente `build`.
"""

from __future__ import annotations

import json
import os
from typing import Any

from context_map.core.storage.store import (
    SNAPSHOT_KEEP_DAYS_DEFAULT,
    SNAPSHOT_KEEP_DEFAULT,
    _listar_snapshots,
    purgar_snapshots,
)

ARCHIVE_DIRNAME = "archive"


def _dir_historial(target_dir: str) -> str:
    """Resuelve la carpeta del historial para el proyecto indicado.

    Args:
        target_dir (str): Ruta del proyecto (`.` para el directorio actual).

    Returns:
        str: Ruta a `maps/HISTORY`.
    """
    if not target_dir or target_dir == ".":
        return os.path.join(".context-map", "maps", "HISTORY")
    return os.path.join(target_dir, ".context-map", "maps", "HISTORY")


def _metricas(history_dir: str) -> dict[str, Any]:
    """Cuenta snapshots, tamaño activo y archivos comprimidos del historial.

    Args:
        history_dir (str): Carpeta `maps/HISTORY`.

    Returns:
        Dict[str, Any]: Snapshots activos, bytes/MB y estado del archivo tar.gz.
    """
    rutas = _listar_snapshots(history_dir)
    bytes_activos = 0
    for ruta in rutas:
        try:
            bytes_activos += os.path.getsize(ruta)
        except OSError:
            continue

    carpeta_archivo = os.path.join(os.path.dirname(history_dir), ARCHIVE_DIRNAME)
    tars: list[tuple[str, int]] = []
    if os.path.isdir(carpeta_archivo):
        for nombre in sorted(os.listdir(carpeta_archivo)):
            if not nombre.endswith(".tar.gz"):
                continue
            try:
                tars.append((nombre, os.path.getsize(os.path.join(carpeta_archivo, nombre))))
            except OSError:
                continue

    return {
        "dir": history_dir,
        "snapshots": len(rutas),
        "bytes": bytes_activos,
        "mb": round(bytes_activos / (1024 * 1024), 2),
        "archivos_comprimidos": len(tars),
        "archivos_mb": round(sum(tam for _, tam in tars) / (1024 * 1024), 2),
        "keep_default": SNAPSHOT_KEEP_DEFAULT,
        "keep_days_default": SNAPSHOT_KEEP_DAYS_DEFAULT,
    }


def cmd_history(args: dict[str, Any]) -> None:
    """Manejador del comando `ctxmap history <list|prune>`.

    Args:
        args (Dict[str, Any]): Argumentos parseados. Claves relevantes:
            `action` ('list' o 'prune'), `target_dir`, `keep`, `keep_days`,
            `delete` (borrar en vez de archivar), `dry_run` y `json`.
    """
    accion = (args.get("action") or "list").lower()
    as_json = bool(args.get("json", False))
    target_dir = args.get("target_dir") or "."
    hist_dir = _dir_historial(target_dir)
    datos = _metricas(hist_dir)

    if accion == "list":
        if as_json:
            print(json.dumps(datos, indent=2, ensure_ascii=False))
            return
        print(f"\n🗂️  Historial: {datos['dir']}")
        print(f"   Snapshots activos: {datos['snapshots']} · {datos['mb']} MB")
        if datos["archivos_comprimidos"]:
            print(
                f"   Archivados (.tar.gz): {datos['archivos_comprimidos']} · "
                f"{datos['archivos_mb']} MB"
            )
        print(
            f"   Retención: {datos['keep_default']} snapshots recientes + "
            f"1 por cada uno de los últimos {datos['keep_days_default']} días"
        )
        return

    if accion == "prune":
        archivar = not bool(args.get("delete", False))
        dry_run = bool(args.get("dry_run", False))
        res = purgar_snapshots(
            hist_dir,
            keep=args.get("keep"),
            keep_days=args.get("keep_days"),
            archivar=archivar,
            dry_run=dry_run,
        )
        if as_json:
            print(json.dumps({**res, "dry_run": dry_run, "archivar": archivar}, indent=2, ensure_ascii=False))
            return
        etiqueta = "(simulación)" if dry_run else ""
        accion_txt = "archivados" if archivar else "borrados"
        print(
            f"🧹 Poda {etiqueta}: {res['conservados']} conservados · "
            f"{res['archivados']} {accion_txt} · {res['eliminados']} eliminados"
            + (f" · archivo: {res['archivo']}" if res.get("archivo") else "")
        )
        return

    print(f"⚠️  Acción desconocida: {accion}. Usa 'list' o 'prune'.")

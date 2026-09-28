"""Comando ``inbox``: captura y clasificación PKM (Second Brain).

Expone el mundo conocimiento (``90-CONOCIMIENTO/00-INBOX``) desde la CLI:

- ``ctxmap inbox add "<texto>"``  → crea una nota cruda en el inbox.
- ``ctxmap inbox list``           → lista las notas pendientes.
- ``ctxmap inbox move <nota> <destino>`` → mueve una nota a PARA.
- ``ctxmap inbox purge``          → clasifica y vacía el inbox (heurística).
"""

from __future__ import annotations

import json
import os

from context_map.application.commands._helpers import project_name, vault_dir
from context_map.domain.knowledge import inbox as kb


def _resolver_vault(args) -> str:
    """Resuelve el directorio del vault del proyecto objetivo."""
    return vault_dir(project_name(args))


def cmd_inbox(args) -> None:
    """Despacha las acciones del subcomando ``inbox``.

    Args:
        args: Namespace de argparse con ``inbox_cmd`` y sus opciones.
    """
    accion = getattr(args, "inbox_cmd", None)
    if not accion:
        print("Uso: ctxmap inbox {add|list|move|purge} [opciones]")
        return

    vdir = _resolver_vault(args)

    if accion == "add":
        ruta = kb.crear_nota(
            vdir,
            getattr(args, "texto", ""),
            titulo=getattr(args, "title", None),
            tags=getattr(args, "tags", ""),
            fuente=getattr(args, "source", ""),
        )
        print(f"[inbox] 📥 Nota capturada: {ruta}")

    elif accion == "list":
        notas = kb.listar_notas(vdir, "inbox")
        if getattr(args, "json", False):
            print(json.dumps(notas, ensure_ascii=False, indent=2))
            return
        if not notas:
            print("[inbox] Vacío — no hay notas por clasificar.")
            return
        print(f"[inbox] {len(notas)} nota(s) en el inbox:")
        for n in notas:
            print(f"  - {n['titulo']}  ({os.path.basename(n['ruta'])})")

    elif accion == "move":
        destino = getattr(args, "destino", "")
        ruta = kb.mover_nota(vdir, getattr(args, "nota", ""), destino)
        print(f"[inbox] ➡️  Movida a {destino}: {ruta}")

    elif accion == "purge":
        dry = bool(getattr(args, "dry_run", False))
        decisiones = kb.purgar(vdir, dry_run=dry)
        if getattr(args, "json", False):
            print(json.dumps(decisiones, ensure_ascii=False, indent=2))
            return
        if not decisiones:
            print("[inbox] Nada para depurar (inbox vacío).")
            return
        etiqueta = " (dry-run, sin cambios)" if dry else ""
        print(f"[inbox] 🧹 Clasificando {len(decisiones)} nota(s){etiqueta}:")
        for d in decisiones:
            print(f"  - {d['nota']} → {d['destino']}")

    else:
        print(f"[inbox] Acción desconocida: {accion}")

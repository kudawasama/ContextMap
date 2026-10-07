"""Comando ``inbox``: captura y clasificación PKM (Second Brain).

Expone el mundo conocimiento (``90-CONOCIMIENTO/00-INBOX``) desde la CLI:

- ``ctxmap inbox add "<texto>"``  → crea una nota cruda en el inbox.
- ``ctxmap inbox add --clipboard`` → captura el portapapeles (Web Clipper).
- ``ctxmap inbox bookmarklet``  → imprime el bookmarklet del Web Clipper.
- ``ctxmap inbox list``           → lista las notas pendientes.
- ``ctxmap inbox move <nota> <destino>`` → mueve una nota a PARA.
- ``ctxmap inbox purge``          → clasifica y vacía el inbox (heurística).
"""

from __future__ import annotations

import json
import os

from context_map.application.commands._helpers import project_name, vault_dir
from context_map.domain.knowledge import clip
from context_map.domain.knowledge import inbox as kb


def _resolver_vault(args) -> str:
    """Resuelve el directorio del vault del proyecto objetivo."""
    return vault_dir(project_name(args))


def _texto_de_entrada(args) -> str:
    """Devuelve el texto de la nota, leyendo de stdin o del portapapeles.

    Permite capturar desde un bookmarklet, un pipe o el Web Clipper:
    ``pbpaste | ctxmap inbox add -``, ``ctxmap inbox add "" --stdin`` o
    ``ctxmap inbox add --clipboard``.

    Args:
        args: Namespace con ``texto``, ``stdin`` y ``clipboard``.

    Returns:
        str: Texto de la nota.
    """
    import sys

    if getattr(args, "clipboard", False):
        return clip.leer_portapapeles()
    texto = getattr(args, "texto", "") or ""
    if getattr(args, "stdin", False) or texto.strip() == "-":
        return sys.stdin.read()
    return texto


def cmd_inbox(args) -> None:
    """Despacha las acciones del subcomando ``inbox``.

    Args:
        args: Namespace de argparse con ``inbox_cmd`` y sus opciones.
    """
    accion = getattr(args, "inbox_cmd", None)
    if not accion:
        print("Uso: ctxmap inbox {add|list|move|purge|bookmarklet} [opciones]")
        return

    vdir = _resolver_vault(args)

    if accion == "add":
        texto = _texto_de_entrada(args)
        if not texto.strip() and not getattr(args, "title", None):
            print("[inbox] Nada que capturar: el portapapeles está vacío o no hay "
                  "herramienta disponible (usa `ctxmap inbox add \"<texto>\"`).")
            return
        titulo = getattr(args, "title", None)
        fuente = getattr(args, "source", "")
        if getattr(args, "clipboard", False):
            # El Web Clipper copia ``- [Título](url)``: se usa para titular y citar.
            titulo_auto, url_auto = clip.desglosar_markdown(texto)
            titulo = titulo or (titulo_auto or None)
            fuente = fuente or url_auto
        ruta = kb.crear_nota(
            vdir,
            texto,
            titulo=titulo,
            tags=getattr(args, "tags", ""),
            fuente=fuente,
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

    elif accion == "bookmarklet":
        generar_html = bool(getattr(args, "html", False))
        ruta_html = ""
        if generar_html:
            destino = getattr(args, "ruta", "") or os.path.join(
                ".context-map", "clip-bookmarklet.html"
            )
            ruta_html = clip.guardar_html(destino)
            if not getattr(args, "json", False):
                print(f"[inbox] 🔖 HTML del Web Clipper generado: {ruta_html}")
        if getattr(args, "json", False):
            print(json.dumps(
                {"bookmarklet": clip.bookmarklet(), "html": ruta_html},
                ensure_ascii=False, indent=2,
            ))
            return
        print("[inbox] 🔖 Web Clipper de ContextMap")
        print("  1. Arrastra este enlace a tu barra de favoritos:")
        print(f"     {clip.bookmarklet()}")
        print("  2. Al pulsarlo copia la página (título + URL + selección) al portapapeles.")
        print("  3. Captúralo en tu Second Brain:")
        print("     ctxmap inbox add --clipboard")
        if not generar_html:
            print("  (Genera el HTML arrastrable con: ctxmap inbox bookmarklet --html)")

    else:
        print(f"[inbox] Acción desconocida: {accion}")

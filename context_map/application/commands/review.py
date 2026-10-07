"""Comando ``review``: repaso espaciado (SM-2) de la wiki del mundo conocimiento.

- ``ctxmap review due``                 → páginas de la wiki para repasar hoy.
- ``ctxmap review grade "<página>" <0-5>`` → califica y reprograma (SM-2).
"""

from __future__ import annotations

import json

from context_map.application.commands._helpers import project_name, vault_dir
from context_map.domain.knowledge import review as rv


def cmd_review(args) -> None:
    """Despacha las acciones del subcomando ``review``.

    Args:
        args: Namespace de argparse con ``review_cmd`` y sus opciones.
    """
    vdir = vault_dir(project_name(args))
    accion = getattr(args, "review_cmd", None) or "due"

    if accion == "due":
        limite = int(getattr(args, "limite", 20))
        pendientes = rv.paginas_due(vdir, limite=limite)
        if getattr(args, "json", False):
            print(json.dumps(pendientes, ensure_ascii=False, indent=2))
            return
        if not pendientes:
            print("[review] Nada pendiente de repaso. 🎉")
            return
        print(f"[review] 🔁 {len(pendientes)} página(s) para repasar hoy:")
        for p in pendientes:
            print(f"  - {p['titulo']} ({p['due'] or 'nueva'}) · {p['cita']}")
        print('\n[review] Calificá 0-5: ctxmap review grade "<título>" <calidad>')
        return

    if accion == "grade":
        pagina = getattr(args, "pagina", "")
        calidad = int(getattr(args, "calidad", 0))
        try:
            res = rv.calificar(vdir, pagina, calidad)
        except ValueError as err:
            print(f"[review] {err}")
            return
        if getattr(args, "json", False):
            print(json.dumps(res, ensure_ascii=False, indent=2))
            return
        print(
            f"[review] ✅ {res['titulo']} → repeticiones={res['repetitions']}, "
            f"intervalo={res['interval']}d, ease={res['ease']}, próximo={res['due']}"
        )
        return

    print("Uso: ctxmap review {due|grade} [opciones]")

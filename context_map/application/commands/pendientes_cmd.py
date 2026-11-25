"""Comando ``pendientes``: cruza las cuatro fuentes antes de decir qué queda.

``REG-INI-004`` pide no responder «¿qué queda pendiente?» con un único
documento. El cruce es mecánico, así que lo hace el motor: backlog manual,
tareas, la última entrada del diario y los documentos que ninguna nota cita.
"""

from __future__ import annotations

import json

from context_map.domain.reporting.pendientes import cruzar_fuentes, fuentes_ausentes


def cmd_pendientes(args) -> None:
    """Imprime el cruce de pendientes de las cuatro fuentes.

    Args:
        args: Namespace de argparse con ``target``, ``limite`` y ``json``.
    """
    # `_dispatch_cmd` entrega un dict; el comando se usa también desde código con Namespace.
    def _opcion(nombre, defecto=None):
        if isinstance(args, dict):
            return args.get(nombre, defecto)
        return getattr(args, nombre, defecto)

    target = _opcion("target") or _opcion("target_dir") or "."
    limite = int(_opcion("limite", 12) or 12)
    cruce = cruzar_fuentes(target, limite=limite)

    if _opcion("json", False):
        print(json.dumps(cruce, ensure_ascii=False, indent=2))
        return

    if not cruce.get("vault"):
        print(f"[X] No hay vault en '{target}': nada que cruzar (ejecuta `ctxmap build`).")
        return

    print()
    print("📋 Pendientes cruzados (backlog · tareas · diario · documentos)")
    print("=" * 60)
    print(f"  proyecto: {cruce['proyecto']} · {cruce['total']} pendiente(s) en {len(cruce['fuentes'])} fuentes")

    for fuente in cruce["fuentes"]:
        print()
        if not fuente["presente"]:
            print(f"  ⚠️  {fuente['nombre']}: fuente ausente ({fuente['ruta']})")
            continue
        extra = f" · {fuente.get('entrada')}" if fuente.get("entrada") else ""
        print(f"  ── {fuente['nombre']} · {fuente['total']}{extra}")
        if not fuente["items"]:
            print("     (sin pendientes abiertos)")
            continue
        for item in fuente["items"]:
            print(f"    · {item[:120]}")
        resto = fuente["total"] - len(fuente["items"])
        if resto > 0:
            print(f"    … y {resto} más")

    ausentes = fuentes_ausentes(cruce)
    print()
    if ausentes:
        print(f"  ⚠️  Sin veredicto de: {', '.join(ausentes)} (la fuente no existe en el vault).")
    if cruce["total"] == 0:
        print("  ✅ Ninguna de las cuatro fuentes tiene pendientes abiertos.")

"""Comando wrap: cierre de sesión en 1 paso (R3, auditoría 2026-08-14).

Ejecuta ``refresh`` (scan + build preservando manuales + check) y luego
imprime un resumen de lo registrado: cuántos eventos hay en events.jsonl
y cuántas sesiones de Hermes quedan sin importar.

Es el "adiós" del agente: deja el contexto al día y muestra la cobertura
de la memoria viva para que el usuario sepa si quedó algo sin registrar.
"""

from __future__ import annotations

import os

from context_map.application.commands.refresh import cmd_refresh


def _sesiones_pendientes(ruta_raiz: str) -> int:
    """Cuenta sesiones de Hermes posteriores al último build sin importar.

    Reutiliza la lógica de frescura del checker (R1): compara el timestamp
    de ``last_build.json`` contra las sesiones recientes.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        int: Número de sesiones pendientes (0 si no se puede saber).
    """
    try:
        from context_map.domain.analysis.checker import _sesiones_posteriores

        return _sesiones_posteriores(ruta_raiz)
    except Exception:
        return 0


def _contar_eventos(ruta_raiz: str) -> int:
    """Cuenta los eventos importados en ``.context-map/raw/events.jsonl``.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        int: Número de líneas JSON válidas, o 0 si no existe el archivo.
    """
    ruta = os.path.join(ruta_raiz, ".context-map", "raw", "events.jsonl")
    if not os.path.isfile(ruta):
        return 0
    n = 0
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    n += 1
    except Exception:
        return 0
    return n


def cmd_wrap(args) -> None:
    """Cierra la sesión: refresh + resumen de memoria viva.

    Args:
        args: Namespace de argparse con ``target`` y ``project``.
    """
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)

    # 1) Actualizar el contexto completo (scan + build + check).
    cmd_refresh(args)

    if quiet:
        return

    # 2) Resumen de cobertura de la memoria viva.
    eventos = _contar_eventos(target)
    pendientes = _sesiones_pendientes(target)

    print()
    print("── Resumen de cierre de sesión ──")
    print(f"  · Eventos registrados en events.jsonl : {eventos}")
    print(f"  · Sesiones de Hermes sin importar     : {pendientes}")
    if pendientes:
        print("  ⚠️  Quedan sesiones sin importar — vuelve a ejecutar `ctxmap refresh .`")
        print("      cuando termines (o simplemente `ctxmap wrap`).")
    else:
        print("  ✅ Memoria viva al día. Hasta la próxima sesión.")
    print("─────────────────────────────────────")

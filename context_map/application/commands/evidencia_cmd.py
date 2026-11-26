"""Comando ``evidencia``: el informe de la sesión sale del registro, no de la memoria.

``REG-EJE-005`` pide verificar con la salida real de los comandos y nunca con el
autoreporte. En vez de auditar la prosa del agente —que marcaría redacción, no
conducta—, el motor imprime lo que efectivamente se ejecutó hoy.
"""

from __future__ import annotations

import json

from context_map.domain.reporting.evidencia import (
    construir_evidencia,
    formatear_evidencia_texto,
)


def _opcion(args, nombre, defecto=None):
    """Lee una opción venga como ``dict`` (CLI) o como ``Namespace``.

    Args:
        args: Argumentos del comando.
        nombre (str): Nombre de la opción.
        defecto: Valor por defecto.

    Returns:
        El valor de la opción o ``defecto``.
    """
    if isinstance(args, dict):
        return args.get(nombre, defecto)
    return getattr(args, nombre, defecto)


def cmd_evidencia(args) -> None:
    """Imprime la evidencia de la sesión (bitácora + huella de lecturas).

    Args:
        args: Namespace o ``dict`` con ``target``, ``dia``, ``limite`` y ``json``.
    """
    target = _opcion(args, "target") or _opcion(args, "target_dir") or "."
    limite = int(_opcion(args, "limite", 20) or 20)
    fecha = _opcion(args, "dia") or None

    reporte = construir_evidencia(target, fecha=fecha, limite=limite)

    if _opcion(args, "json", False):
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
        return

    print(formatear_evidencia_texto(reporte), end="")

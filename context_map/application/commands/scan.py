"""Comando scan: escaneo de proyecto y generación de eventos.

Analiza la estructura y contenido del proyecto para generar
eventos que alimentan el mapa de contexto.
"""

from __future__ import annotations

import os

from context_map.domain.scanner import escanear_y_generar_eventos, guardar_eventos_escaneados

from context_map.application.commands._helpers import (
    RAW_DIR,
    ensure_dirs,
    project_name,
)
from context_map.application.commands.sync import do_sync


def cmd_scan(args) -> None:
    """Escanea el proyecto y genera eventos para el mapa.

    Args:
        args: Namespace de argparse con ``target`` y ``project``
    """
    ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Escaneando: {os.path.abspath(ruta)}")

    eventos = escanear_y_generar_eventos(ruta)

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        do_sync(args, project_name(args))

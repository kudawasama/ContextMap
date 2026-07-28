"""Comandos utilitarios: init, check, weekly, watch, brief, doctor.

Agrupa comandos de administración y diagnóstico que no encajan
en los módulos de build, sync, scan o importación.
"""

from __future__ import annotations

import os
import time

from context_map.core.models import Node, Edge
from context_map.core.store import load_jsonl
from context_map.presentation.brief import generar_brief
from context_map.domain.checker import analizar_readiness, formatear_readiness
from context_map.domain.reporter import guardar_reporte
from context_map.domain.doctor import run as doctor_run

from context_map.application.commands._helpers import (
    CONTEXT_DIR,
    STATE_DIR,
    MAPS_DIR,
    ensure_dirs,
    project_name,
)
from context_map.application.commands.sync import do_sync


def cmd_init(_args) -> None:
    """Crea el directorio .context-map/ con toda su estructura."""
    ensure_dirs()
    print("init:ok ->", os.path.abspath(CONTEXT_DIR))


def cmd_check(args) -> None:
    """Verifica readiness del proyecto (score 0-100).

    Args:
        args: Namespace de argparse con ``target``
    """
    ruta = args.target or os.getcwd()
    resultado = analizar_readiness(ruta)
    print(formatear_readiness(resultado))


def cmd_weekly(args) -> None:
    """Genera reporte semanal del proyecto.

    Args:
        args: Namespace de argparse con ``days``
    """
    ensure_dirs()

    dias = args.days or 7
    output = os.path.join(MAPS_DIR, f"semanal-{dias}d.md")

    print(f"Generando reporte de los ultimos {dias} dias...")

    reporte = guardar_reporte(STATE_DIR, output, dias)

    print(f"Reporte generado: {reporte}")
    print("")
    with open(reporte, "r", encoding="utf-8") as f:
        lineas = f.readlines()[:30]
        print("".join(lineas))


def cmd_watch(args) -> None:
    """Observa cambios en el grafo y regenera automáticamente.

    Args:
        args: Namespace de argparse con ``interval``
    """
    print(f"Observando cambios cada {args.interval} segundos... (Ctrl+C para salir)")

    last_mtime = 0

    while True:
        graph_path = os.path.join(STATE_DIR, "graph.jsonl")
        if os.path.exists(graph_path):
            current_mtime = os.path.getmtime(graph_path)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                print("Detectado cambio, regenerando...")
                try:
                    do_sync(args, "Repo")
                except Exception as e:
                    print(f"Error: {e}")
        time.sleep(args.interval)


def cmd_brief(args) -> None:
    """Genera brief de contexto para agentes de IA.

    Args:
        args: Namespace de argparse con ``project``
    """
    ensure_dirs()

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    if not nodes:
        print("No hay nodos. Ejecuta 'ctxmap build' primero.")
        return

    readiness = analizar_readiness(".")
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")

    generar_brief(project_name(args), nodes, edges, readiness.score, brief_path)
    print(f"brief:ok -> {brief_path}")


def cmd_doctor(args) -> None:
    """Diagnostica el entorno y repara problemas conocidos.

    Args:
        args: Namespace de argparse (sin argumentos adicionales)
    """
    report = doctor_run()

    for check in report.checks:
        icon = "[OK]" if check.status == "OK" else "[WARN]" if check.status == "WARN" else "[ERR]"
        print(f"{icon} {check.name}: {check.message}")

        if check.fix_applied:
            print(f"   [fix] Reparacion: {check.fix_message}")

        print()

    if report.ok:
        print("Doctor: sin fallos detectados.")
    else:
        print("Doctor: se detectaron fallos.")
        if any(c.fix_applied for c in report.checks):
            print("   Algunos se intentaron reparar automaticamente.")
        print("   Revisa los mensajes anteriores y reejecuta 'ctxmap doctor' si es necesario.")

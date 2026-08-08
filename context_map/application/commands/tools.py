"""Comandos utilitarios: init, check, weekly, brief, doctor.

Agrupa comandos de administración y diagnóstico que no encajan
en los módulos de build, sync, scan o importación.
"""

from __future__ import annotations

import os

from context_map.application.commands._helpers import (
    CONTEXT_DIR,
    MAPS_DIR,
    STATE_DIR,
    ensure_dirs,
    project_name,
)
from context_map.core.models import Edge, Node
from context_map.core.storage import load_jsonl
from context_map.domain.analysis import analizar_readiness, formatear_readiness
from context_map.domain.health import run_doctor as doctor_run
from context_map.domain.reporting import guardar_reporte
from context_map.presentation.briefs import generar_brief, generar_instrucciones_agentes


def cmd_init(args) -> None:
    """Crea el directorio .context-map/ con toda su estructura y genera AGENTS.md."""
    proj = project_name(args)
    ensure_dirs(proj)
    agents_path = generar_instrucciones_agentes(proj, target_dir=".", overwrite_if_exists=False)
    print("init:ok ->", os.path.abspath(CONTEXT_DIR))
    print(f"agents:ok -> {agents_path}")

    # Auto-adaptación del ecosistema agéntico (solo crea reglas faltantes, no toca existentes)
    from context_map.application.commands.adapt import do_adapt
    do_adapt(target=".", project_name=proj, modo="respect", quiet=True)
    print("adapt:ok -> reglas agénticas generadas")


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
    with open(reporte, encoding="utf-8") as f:
        lineas = f.readlines()[:30]
        print("".join(lineas))


def cmd_brief(args) -> None:
    """Genera brief de contexto para agentes de IA y actualiza AGENTS.md.

    Args:
        args: Namespace de argparse con ``project``
    """
    proj = project_name(args)
    ensure_dirs(proj)

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    if not nodes:
        print("No hay nodos. Ejecuta 'ctxmap build' primero.")
        return

    readiness = analizar_readiness(".")
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")

    generar_brief(proj, nodes, edges, readiness.score, brief_path)
    agents_path = generar_instrucciones_agentes(proj, target_dir=".", overwrite_if_exists=False)
    print(f"brief:ok -> {brief_path}")
    print(f"agents:ok -> {agents_path}")


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

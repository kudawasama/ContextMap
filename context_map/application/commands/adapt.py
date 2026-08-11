"""Comando adapt: detecta el ecosistema del proyecto y adapta las reglas agénticas.

Analiza el stack técnico (lenguaje, framework, test runner, entrypoints)
y las herramientas agénticas presentes (VS Code, Cursor, Windsurf,
JetBrains, Claude Code, Copilot, Hermes), y genera/actualiza los archivos
de reglas correspondientes (AGENTS.md contextual, CLAUDE.md, .cursorrules,
.windsurfrules, copilot-instructions, .hermes/).
"""

from __future__ import annotations

import os

from context_map.application.commands._helpers import project_name
from context_map.domain.ecosystem import adaptar_ecosistema, detectar_ecosistema


def do_adapt(
    target: str = ".",
    project_name: str = "Repo",
    modo: str = "respect",
    quiet: bool = False,
) -> list[str]:
    """Detecta el ecosistema y genera las reglas agénticas adaptadas.

    Función reutilizable invocable desde el CLI (``ctxmap adapt``) o desde
    otros comandos (``init``, ``build``) para auto-adaptar el proyecto.

    Args:
        target (str): Ruta del proyecto a analizar.
        project_name (str): Nombre del proyecto.
        modo (str): 'respect' | 'merge' | 'overwrite'.
        quiet (bool): Si True, no imprime el reporte de detección.

    Returns:
        list[str]: Rutas de los archivos generados/actualizados.
    """
    eco = detectar_ecosistema(target)

    if not quiet:
        print()
        print(eco.resumen_texto())
        print()

    generados = adaptar_ecosistema(
        project_name=project_name,
        eco=eco,
        target_dir=target,
        modo=modo,
    )

    if generados and not quiet:
        print("✅ Reglas agénticas generadas/actualizadas:")
        for ruta in generados:
            print(f"   + {ruta}")
        print()
        print("💡 Reglas existentes que no se sobreescribieron (usa --overwrite para forzar):")
        print("   (ver 'Reglas existentes' en el reporte de arriba)")
    elif not generados and not quiet:
        print("⚠️ No se generaron reglas nuevas (todas ya existían).")

    return generados


def cmd_adapt(args) -> None:
    """Detecta el ecosistema y genera las reglas agénticas adaptadas.

    Args:
        args: Namespace de argparse con ``target``, ``--project``, ``--overwrite``.
    """
    target = getattr(args, "target", None) or "."
    proj = project_name(args)

    print(f"🔍 Analizando ecosistema de '{target}'...")
    if getattr(args, "overwrite", False):
        modo = "overwrite"
    elif getattr(args, "merge", False):
        modo = "merge"
    else:
        modo = "respect"

    do_adapt(
        target=target,
        project_name=proj,
        modo=modo,
        quiet=False,
    )

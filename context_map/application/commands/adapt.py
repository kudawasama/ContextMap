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


def cmd_adapt(args) -> None:
    """Detecta el ecosistema y genera las reglas agénticas adaptadas.

    Args:
        args: Namespace de argparse con ``target``, ``--project``, ``--overwrite``.
    """
    target = getattr(args, "target", None) or "."
    proj = project_name(args)

    print(f"🔍 Analizando ecosistema de '{target}'...")
    eco = detectar_ecosistema(target)

    print()
    print(eco.resumen_texto())
    print()

    generados = adaptar_ecosistema(
        project_name=proj,
        eco=eco,
        target_dir=target,
        overwrite=bool(getattr(args, "overwrite", False)),
        modo="merge" if getattr(args, "merge", False) else "respect",
    )

    if generados:
        print("✅ Reglas agénticas generadas/actualizadas:")
        for ruta in generados:
            print(f"   + {ruta}")
        print()
        print("💡 Reglas existentes que no se sobreescribieron (usa --overwrite para forzar):")
        print("   (ver 'Reglas existentes' en el reporte de arriba)")
    else:
        print("⚠️ No se generaron reglas nuevas (todas ya existían).")

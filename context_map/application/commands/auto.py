"""Comando auto: Orquestación completa en 1 solo paso.

Ejecuta secuencialmente:
1. Escaneo estático del proyecto (scan)
2. Importación del historial Git (import-git, si existe .git)
3. Construcción limpia del Vault y Briefs para Agentes (build --clean --brief)
"""

from __future__ import annotations

import os

from context_map.application.commands.build import cmd_build
from context_map.application.commands.importers import cmd_import_git
from context_map.application.commands.scan import cmd_scan


def cmd_auto(args) -> None:
    """Orquesta el flujo completo de escaneo, ingesta git y generación del vault.

    Args:
        args: Namespace de argparse con atributo ``target``.
    """
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)
    abs_target = os.path.abspath(target)
    old_cwd = os.getcwd()

    if not quiet:
        print(f"[auto] Iniciando automatizacion completa para: {target}")

    try:
        if abs_target != old_cwd:
            os.chdir(abs_target)

        cmd_scan(args)

        git_dir = os.path.join(abs_target, ".git")
        if os.path.exists(git_dir):
            try:
                if not hasattr(args, "limit"):
                    args.limit = 50
                cmd_import_git(args)
            except Exception as err:
                if not quiet:
                    print(f"[auto] [WARN] No se pudo importar el historial Git ({err})")

        args.clean = True
        args.brief = True
        cmd_build(args)

        if not quiet:
            print(f"[auto] [OK] Automatizacion finalizada exitosamente para {target}")
    finally:
        if abs_target != old_cwd:
            os.chdir(old_cwd)

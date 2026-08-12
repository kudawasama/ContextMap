"""Comando refresh: actualiza el contexto en 1 solo paso, sin destruir lo manual.

Ejecuta secuencialmente:
1. Escaneo estático del proyecto (scan)
2. Construcción del Vault + Brief (build --brief, SIN --clean: preserva notas manuales)
3. Verificación de readiness (check)

Reemplaza el protocolo de 4 comandos del AGENTS.md: el agente solo necesita
`python -m pytest && ctxmap refresh` para dejar el contexto al día.
"""

from __future__ import annotations

import os
import types

from context_map.application.commands.build import cmd_build
from context_map.application.commands.scan import cmd_scan
from context_map.application.commands.tools import cmd_check


def cmd_refresh(args) -> None:
    """Orquesta scan + build (sin clean) + check en un solo paso.

    Args:
        args: Namespace de argparse con atributo ``target`` y ``project``.
    """
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)
    abs_target = os.path.abspath(target)
    old_cwd = os.getcwd()

    if not quiet:
        print(f"[refresh] Actualizando contexto de: {target}")

    # Punto de control de versión (2026-08-11): antes de actualizar el CONTEXTO,
    # verificar si el PROGRAMA (binario ctxmap) está desactualizado y solicitarlo.
    # Aviso accionable y NO bloqueante: el agente/usuario decide actualizar.
    if not quiet:
        from context_map.infrastructure.version_check import aviso_pre_actualizacion

        print(aviso_pre_actualizacion(), end="")

    try:
        if abs_target != old_cwd:
            os.chdir(abs_target)

        cmd_scan(args)

        # Clonar args para build con target="." y SIN --clean (preserva manuales).
        # Pitfall documentado: reutilizar el namespace original contamina
        # project_name() y genera vault con el nombre del target.
        build_args = types.SimpleNamespace(
            target=".",
            project=getattr(args, "project", "Repo"),
            snapshot_name="",
            brief=True,
            mode=getattr(args, "mode", "hierarchical"),
            raw=False,
            clean=False,
            quiet=quiet,
        )
        cmd_build(build_args)

        check_args = types.SimpleNamespace(target=".", json=False)
        cmd_check(check_args)

        if not quiet:
            print(f"[refresh] [OK] Contexto actualizado para {target}")
    finally:
        if abs_target != old_cwd:
            os.chdir(old_cwd)

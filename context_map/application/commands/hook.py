"""Comando de instalación de Git Pre-Commit Hook.


Inyecta un script pre-commit ejecutable en .git/hooks/ para sincronizar
automáticamente la bóveda de Obsidian y briefs antes de cada commit.
"""

from __future__ import annotations

import os
import stat


def cmd_hook_install(args=None) -> None:
    """Instala el hook pre-commit de ContextMap en el directorio objetivo."""
    target_dir = getattr(args, "target", ".") if args else "."
    git_dir = os.path.join(target_dir, ".git")

    if not os.path.exists(git_dir) or not os.path.isdir(git_dir):
        print(f"[X] No se encontró un directorio .git en '{target_dir}'. Inicializa git antes de instalar el hook.")
        return

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)
    hook_file = os.path.join(hooks_dir, "pre-commit")

    script_content = """#!/bin/sh
# ContextMap Auto-Sync Pre-Commit Hook
if command -v ctxmap >/dev/null 2>&1; then
    ctxmap build --clean --brief --quiet
elif command -v python >/dev/null 2>&1; then
    python -m context_map.cli build --clean --brief --quiet
fi
"""

    try:
        with open(hook_file, "w", encoding="utf-8", newline="\n") as f:
            f.write(script_content)

        # Otorgar permisos de ejecución en entornos Unix/Linux/macOS/Git Bash
        current_perm = os.stat(hook_file).st_mode
        os.chmod(hook_file, current_perm | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        print(f"[OK] Pre-commit hook de ContextMap instalado en: {hook_file}")
    except Exception as err:
        print(f"[X] Error al instalar pre-commit hook: {err}")

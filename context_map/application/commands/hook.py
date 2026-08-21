"""Comando CLI 'hook' para gestionar la instalación de Git Hooks."""

from __future__ import annotations

from typing import Any

from context_map.domain.ecosystem.hooks import (
    PRE_COMMIT_SCRIPT,
    desinstalar_git_hooks,
    instalar_git_hooks,
)


def _script_hook() -> str:
    """Retorna el contenido del pre-commit script para retrocompatibilidad."""
    return PRE_COMMIT_SCRIPT


def cmd_hook_install(args=None) -> None:
    """Alias de retrocompatibilidad para cmd_hook."""
    target_dir = getattr(args, "target", ".") if args else "."
    res = instalar_git_hooks(target_dir, force=True)
    if res.get("status") == "FAIL":
        print(f"[X] No se encontró un directorio .git en '{target_dir}'. Inicializa git antes de instalar el hook.")
    else:
        print(f"[OK] Pre-commit hook de ContextMap instalado en: {target_dir}/.git/hooks/pre-commit")


def cmd_hook(args: dict[str, Any]) -> None:
    """Manejador del comando CLI `ctxmap hook`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI.
    """
    target_dir = args.get("target_dir") or args.get("target") or "."
    action = args.get("action") or "install"
    force = bool(args.get("force", False))

    if action == "uninstall":
        res = desinstalar_git_hooks(target_dir)
        print(f"⚓ [hooks] Desinstalando Git Hooks en {target_dir}:")
        for k, v in res.items():
            if k != "status":
                print(f"  - {k}: {v}")
    else:
        res = instalar_git_hooks(target_dir, force=force)
        if res.get("status") == "FAIL":
            print(f"❌ [hooks] Error: {res.get('message')}")
            return
        print(f"⚓ [hooks] Instalación de Git Hooks en {target_dir}:")
        for k, v in res.items():
            if k != "status":
                print(f"  - {k}: {v}")

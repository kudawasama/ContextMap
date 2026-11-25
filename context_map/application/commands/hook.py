"""Comando CLI 'hook': Git hooks y receptor de lecturas (``REG-INI-006``)."""

from __future__ import annotations

import json
import sys
from typing import Any

from context_map.core.audit.lecturas import extraer_ruta, registrar_lectura
from context_map.domain.ecosystem.hooks import (
    PRE_COMMIT_SCRIPT,
    desinstalar_git_hooks,
    instalar_git_hooks,
)
from context_map.domain.ecosystem.hooks_lectura import (
    instalar_hook_lectura,
    ya_instalado,
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

    if action == "lectura":
        cmd_hook_lectura(args)
        return

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


def cmd_hook_lectura(args: Any = None) -> None:
    """Receptor de ``PreToolUse``: anota la ruta que el harness acaba de abrir.

    El harness manda un JSON por stdin; si no lo manda (o manda basura), se
    intenta leer la ruta de los argumentos. **Nunca bloquea ni falla**: un hook
    que rompe la sesión por no poder escribir una línea es peor que no tenerlo.

    Args:
        args (Any): Argumentos de la CLI (dict o Namespace).
    """
    def _opcion(nombre, defecto=None):
        if isinstance(args, dict):
            return args.get(nombre, defecto)
        return getattr(args, nombre, defecto)

    target = _opcion("target") or _opcion("target_dir") or "."
    origen = str(_opcion("origen") or "hook")

    if _opcion("instalar"):
        resultado = instalar_hook_lectura(target)
        prefijo = "✅" if resultado["status"] == "OK" else "❌"
        print(f"{prefijo} [lecturas] {resultado['message']}")
        return

    datos: Any = _opcion("ruta") or ""
    if not datos:
        try:
            crudo = sys.stdin.read()
        except (OSError, ValueError):
            crudo = ""
        crudo = crudo.strip()
        if crudo:
            try:
                datos = json.loads(crudo)
            except json.JSONDecodeError:
                datos = crudo

    ruta = extraer_ruta(datos)
    if ruta:
        registrar_lectura(ruta, target, origen=origen)
    if not _opcion("quiet"):
        print(f"[lecturas] {'anotada: ' + ruta if ruta else 'sin ruta que anotar'}")

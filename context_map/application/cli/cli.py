"""Punto de entrada principal del CLI.

Despacha el comando solicitado al handler correspondiente.
"""

from __future__ import annotations

import sys
from pathlib import Path

from context_map.application.cli.parser import create_parser
from context_map.application.commands import (
    cmd_auto,
    cmd_brief,
    cmd_build,
    cmd_check,
    cmd_doctor,
    cmd_hook,
    cmd_import_antigravity,
    cmd_import_chat,
    cmd_import_git,
    cmd_import_sessions,
    cmd_init,
    cmd_refresh,
    cmd_scan,
    cmd_sync,
    cmd_sync_migrate,
    cmd_update,
    cmd_watch,
    cmd_weekly,
    cmd_wrap,
    cmd_enrich,
)
from context_map.application.commands.adapt import cmd_adapt
from context_map.application.commands.export import exportar_contexto
from context_map.application.commands.ingest import cmd_ingest
from context_map.application.commands.personal import cmd_personal
from context_map.core.logging_setup import setup_logging


def cmd_mcp(args=None) -> None:
    """Arranca el servidor MCP de ContextMap (stdio)."""
    from context_map.infrastructure.mcp_server import run

    run()


def cmd_export(args) -> None:
    """Ejecuta la exportación portable del contexto en formato XML/JSON/Markdown."""
    project_path = Path(getattr(args, "target", ".")).resolve()
    fmt = getattr(args, "format", "xml")
    out = Path(args.output).resolve() if getattr(args, "output", None) else None
    brief_only = bool(getattr(args, "brief_only", False))
    model_name = getattr(args, "model", "gpt-4o")

    out_path = exportar_contexto(
        project_path=project_path,
        format_type=fmt,
        output_file=out,
        brief_only=brief_only,
        model_name=model_name,
    )
    print(f"[export] [OK] Contexto exportado exitosamente en ({fmt.upper()}): {out_path}")


def _dispatch_cmd(cmd_func, args) -> None:
    """Invoca el handler del comando convirtiendo args de Namespace a dict si es necesario."""
    if hasattr(args, "__dict__"):
        arg_dict = vars(args)
        arg_dict["target_dir"] = getattr(args, "target", ".")
        cmd_func(arg_dict)
    else:
        cmd_func(args)


def _configurar_utf8_consola() -> None:
    """Fuerza la codificación UTF-8 en stdout y stderr para evitar fallos de encodificación en Windows."""
    if sys.platform == "win32":
        try:
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def main() -> None:
    """Punto de entrada principal de la CLI."""
    _configurar_utf8_consola()
    p = create_parser()
    args = p.parse_args()

    if not args.cmd:
        p.print_help()
        return

    quiet = bool(getattr(args, "quiet", False))
    setup_logging(quiet=quiet, verbose=bool(args.verbose))

    commands = {
        "auto": cmd_auto,
        "init": cmd_init,
        "build": cmd_build,
        "scan": cmd_scan,
        "refresh": cmd_refresh,
        "wrap": cmd_wrap,
        "check": cmd_check,
        "import-git": cmd_import_git,
        "import-sessions": cmd_import_sessions,
        "import-chat": cmd_import_chat,
        "import-antigravity": cmd_import_antigravity,
        "weekly": cmd_weekly,
        "brief": cmd_brief,
        "update": cmd_update,
        "doctor": lambda a: _dispatch_cmd(cmd_doctor, a),
        "hook": lambda a: _dispatch_cmd(cmd_hook, a),
        "watch": lambda a: _dispatch_cmd(cmd_watch, a),
        "ingest": cmd_ingest,
        "adapt": cmd_adapt,
        "personal": cmd_personal,
        "export": cmd_export,
        "enrich": cmd_enrich,
        "mcp": cmd_mcp,
    }

    if args.cmd == "sync":
        if getattr(args, "migrate", False):
            cmd_sync_migrate(args)
        else:
            cmd_sync(args)
    else:
        cmd_func = commands.get(args.cmd)
        if cmd_func:
            cmd_func(args)
        else:
            p.print_help()


if __name__ == "__main__":
    main()

"""Punto de entrada principal del CLI.

Despacha el comando solicitado al handler correspondiente.
"""

from __future__ import annotations

from context_map.application.cli.parser import create_parser
from context_map.application.commands import (
    cmd_auto,
    cmd_brief,
    cmd_build,
    cmd_check,
    cmd_doctor,
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
    cmd_weekly,
)
from context_map.application.commands.adapt import cmd_adapt
from context_map.application.commands.hook import cmd_hook_install
from context_map.application.commands.ingest import cmd_ingest
from context_map.core.logging_setup import setup_logging


def cmd_mcp(args=None) -> None:
    """Arranca el servidor MCP de ContextMap (stdio)."""
    from context_map.infrastructure.mcp_server import run

    run()


def main() -> None:
    """Punto de entrada principal de la CLI."""
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
        "check": cmd_check,
        "import-git": cmd_import_git,
        "import-sessions": cmd_import_sessions,
        "import-chat": cmd_import_chat,
        "import-antigravity": cmd_import_antigravity,
        "weekly": cmd_weekly,
        "brief": cmd_brief,
        "update": cmd_update,
        "doctor": cmd_doctor,
        "hook": cmd_hook_install,
        "ingest": cmd_ingest,
        "adapt": cmd_adapt,
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

"""CLI principal de Context Map.

Punto de entrada que registra todos los comandos disponibles.
"""

from __future__ import annotations

import argparse
import sys

from context_map.application.commands import (
    cmd_init,
    cmd_build,
    cmd_scan,
    cmd_sync,
    cmd_check,
    cmd_import_git,
    cmd_import_sessions,
    cmd_import_chat,
    cmd_import_antigravity,
    cmd_import_antigravity2,
    cmd_weekly,
    cmd_watch,
    cmd_brief,
)


def create_parser() -> argparse.ArgumentParser:
    """Crea el parser principal con todos los comandos."""
    p = argparse.ArgumentParser(
        prog="ctxmap",
        description="Mapa mental narrativo de proyectos para agentes de IA",
    )
    sub = p.add_subparsers(dest="cmd", help="Comandos disponibles")

    # init
    sub.add_parser("init", help="Crea estructura .context-map/")

    # build
    s_build = sub.add_parser("build", help="Genera vault completo")
    s_build.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_build.add_argument("--snapshot-name", default="", help="Nombre del snapshot")
    s_build.add_argument("--mermaid", action="store_true", help="Generar diagrama Mermaid")
    s_build.add_argument("--brief", action="store_true", help="Generar brief para agentes")

    # scan
    s_scan = sub.add_parser("scan", help="Escanea proyecto y genera eventos")
    s_scan.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_scan.add_argument("--project", default="Repo", help="Nombre del proyecto")

    # sync
    s_sync = sub.add_parser("sync", help="Sync incremental (solo nuevos)")
    s_sync.add_argument("--project", default="Repo", help="Nombre del proyecto")

    # check
    s_check = sub.add_parser("check", help="Verifica readiness (0-100)")
    s_check.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_check.add_argument("--json", action="store_true", help="Salida JSON")

    # import-git
    s_git = sub.add_parser("import-git", help="Importa historial de commits")
    s_git.add_argument("target", nargs="?", default=".", help="Ruta del repositorio")
    s_git.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_git.add_argument("--limit", type=int, default=50, help="Máximo de commits")

    # import-sessions
    s_sessions = sub.add_parser("import-sessions", help="Importa sesiones de Hermes")
    s_sessions.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_sessions.add_argument("--db", default=None, help="Ruta a sessions.db")
    s_sessions.add_argument("--limit", type=int, default=5, help="Máximo de sesiones")

    # import-chat
    s_chat = sub.add_parser("import-chat", help="Importa chats externos")
    s_chat.add_argument("file", help="Ruta al archivo de chat")
    s_chat.add_argument("--project", default="Repo", help="Nombre del proyecto")

    # weekly
    s_weekly = sub.add_parser("weekly", help="Genera reporte semanal")
    s_weekly.add_argument("--days", type=int, default=7, help="Días a reportar")

    # watch
    s_watch = sub.add_parser("watch", help="Observa cambios automáticamente")
    s_watch.add_argument("--interval", type=int, default=10, help="Segundos entre checks")

    # brief
    s_brief = sub.add_parser("brief", help="Genera brief para agentes de IA")
    s_brief.add_argument("--project", default="Repo", help="Nombre del proyecto")

    # import-antigravity
    s_antigravity = sub.add_parser("import-antigravity", help="Importa chats de Antigravity IDE")
    s_antigravity.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_antigravity.add_argument("--limit", type=int, default=5, help="Máximo de conversaciones")

    # import-antigravity2
    s_antigravity2 = sub.add_parser("import-antigravity2", help="Importa chats de Antigravity 2.0")
    s_antigravity2.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_antigravity2.add_argument("--limit", type=int, default=5, help="Máximo de conversaciones")

    return p


def main() -> None:
    """Punto de entrada principal."""
    p = create_parser()
    args = p.parse_args()

    if not args.cmd:
        p.print_help()
        return

    # Mapa de comandos
    commands = {
        "init": cmd_init,
        "build": cmd_build,
        "scan": cmd_scan,
        "sync": cmd_sync,
        "check": cmd_check,
        "import-git": cmd_import_git,
        "import-sessions": cmd_import_sessions,
        "import-chat": cmd_import_chat,
        "import-antigravity": cmd_import_antigravity,
        "import-antigravity2": cmd_import_antigravity2,
        "weekly": cmd_weekly,
        "watch": cmd_watch,
        "brief": cmd_brief,
    }

    cmd_func = commands.get(args.cmd)
    if cmd_func:
        cmd_func(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()

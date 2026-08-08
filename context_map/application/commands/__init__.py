"""Commands: re-exportación pública de los comandos del CLI.

La lógica vive en módulos separados para mantener cada archivo chico
y enfocado. Este paquete solo existe como punto de entrada y como
historial de cambios.
"""

from __future__ import annotations

from context_map.application.commands.auto import cmd_auto
from context_map.application.commands.build import cmd_build
from context_map.application.commands.importers import (
    cmd_import_antigravity,
    cmd_import_chat,
    cmd_import_git,
    cmd_import_sessions,
)
from context_map.application.commands.ingest import cmd_ingest
from context_map.application.commands.adapt import cmd_adapt
from context_map.application.commands.scan import cmd_scan
from context_map.application.commands.sync import cmd_sync, cmd_sync_migrate, do_sync
from context_map.application.commands.tools import (
    cmd_brief,
    cmd_check,
    cmd_doctor,
    cmd_init,
    cmd_weekly,
)
from context_map.application.commands.update import cmd_update

__all__ = [
    "cmd_auto",
    "cmd_build",
    "cmd_sync",
    "cmd_sync_migrate",
    "do_sync",
    "cmd_scan",
    "cmd_import_git",
    "cmd_import_sessions",
    "cmd_import_chat",
    "cmd_import_antigravity",
    "cmd_init",
    "cmd_check",
    "cmd_weekly",
    "cmd_brief",
    "cmd_doctor",
    "cmd_update",
    "cmd_ingest",
    "cmd_adapt",
]

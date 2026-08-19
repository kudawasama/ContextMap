"""Commands: re-exportación pública de los comandos del CLI.

La lógica vive en módulos separados para mantener cada archivo chico
y enfocado. Este paquete solo existe como punto de entrada y como
historial de cambios.
"""

from __future__ import annotations

from context_map.application.commands.adapt import cmd_adapt
from context_map.application.commands.auto import cmd_auto
from context_map.application.commands.build import cmd_build
from context_map.application.commands.doctor_cmd import cmd_doctor
from context_map.application.commands.hook import cmd_hook
from context_map.application.commands.importers import (
    cmd_import_antigravity,
    cmd_import_chat,
    cmd_import_git,
    cmd_import_sessions,
)
from context_map.application.commands.ingest import cmd_ingest
from context_map.application.commands.personal import cmd_personal
from context_map.application.commands.refresh import cmd_refresh
from context_map.application.commands.scan import cmd_scan
from context_map.application.commands.sync import cmd_sync, cmd_sync_migrate, do_sync
from context_map.application.commands.tools import (
    cmd_brief,
    cmd_check,
    cmd_init,
    cmd_weekly,
)
from context_map.application.commands.update import cmd_update
from context_map.application.commands.watch import cmd_watch
from context_map.application.commands.wrap import cmd_wrap
from context_map.application.commands.enrich import cmd_enrich
from context_map.application.commands.pack import cmd_pack, cmd_unpack

__all__ = [
    "cmd_pack",
    "cmd_unpack",
    "cmd_enrich",
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
    "cmd_refresh",
    "cmd_personal",
    "cmd_wrap",
    "cmd_watch",
    "cmd_hook",
]

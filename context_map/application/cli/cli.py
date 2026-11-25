"""Punto de entrada principal del CLI.

Despacha el comando solicitado al handler correspondiente.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from context_map.application.cli.parser import create_parser
from context_map.core.audit.bitacora import COMANDOS_CON_PERMISO, registrar
from context_map.application.commands import (
    cmd_auto,
    cmd_brief,
    cmd_build,
    cmd_check,
    cmd_doctor,
    cmd_enrich,
    cmd_hook,
    cmd_import_antigravity,
    cmd_import_chat,
    cmd_import_git,
    cmd_import_sessions,
    cmd_inbox,
    cmd_init,
    cmd_pack,
    cmd_refresh,
    cmd_reglas,
    cmd_review,
    cmd_scan,
    cmd_search,
    cmd_sync,
    cmd_sync_migrate,
    cmd_unpack,
    cmd_update,
    cmd_watch,
    cmd_weekly,
    cmd_wiki,
    cmd_wrap,
)
from context_map.application.commands.adapt import cmd_adapt
from context_map.application.commands.export import exportar_contexto
from context_map.application.commands.history_cmd import cmd_history
from context_map.application.commands.ingest import cmd_ingest
from context_map.application.commands.personal import cmd_personal
from context_map.application.commands.secrets import cmd_secret
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


def _flags_relevantes(args) -> list[str]:
    """Banderas de la ejecución que merece la pena dejar en la bitácora.

    Se anotan solo las que cambian el significado del comando (``strict-warn``,
    ``fix``, ``confirmar``…), nunca valores de ruta: la bitácora no copia datos
    del proyecto.

    Args:
        args: Namespace de argumentos de la CLI.

    Returns:
        List[str]: Nombres de banderas activas.
    """
    interesantes = (
        "fix", "confirmar", "strict", "strict_warn", "overwrite", "merge",
        "revisar", "verificar", "clean", "brief", "json",
    )
    activas = []
    for nombre in interesantes:
        if getattr(args, nombre, False):
            activas.append(nombre.replace("_", "-"))
    return activas


def _contar_notas(project_dir: str) -> int | None:
    """Cuenta las notas Markdown del vault activo (para detectar historia perdida).

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Optional[int]: Número de notas, o ``None`` si no hay vault.
    """
    base = os.path.join(project_dir, ".context-map")
    if not os.path.isdir(base):
        return None
    try:
        total = 0
        for nombre in os.listdir(base):
            if not nombre.startswith("vault-"):
                continue
            for _raiz, _dirs, archivos in os.walk(os.path.join(base, nombre)):
                total += sum(1 for a in archivos if a.endswith(".md"))
        return total or None
    except OSError:
        return None


def _registrar_ejecucion(args, inicio: float, codigo: int) -> None:
    """Anota la ejecución en la bitácora del proyecto (nunca falla).

    Args:
        args: Namespace de argumentos de la CLI.
        inicio (float): ``perf_counter`` tomado antes de despachar el comando.
        codigo (int): Código de salida con el que terminó.
    """
    try:
        comando = str(getattr(args, "cmd", "") or "")
        if not comando:
            return
        destino = str(getattr(args, "target", None) or ".")
        duracion = time.perf_counter() - inicio
        autorizado = None
        if comando in COMANDOS_CON_PERMISO:
            autorizado = bool(getattr(args, "confirmar", False))
        elif comando == "doctor" and getattr(args, "fix", False):
            autorizado = bool(getattr(args, "confirmar", False))
        notas = _contar_notas(destino) if comando in ("build", "refresh") else None
        registrar(
            comando=comando,
            exit_code=codigo,
            duracion_s=duracion,
            flags=_flags_relevantes(args),
            notas=notas,
            autorizado=autorizado,
            project_dir=destino,
        )
    except Exception:  # noqa: BLE001 - registrar no puede romper el comando
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
        "search": cmd_search,
        "update": cmd_update,
        "doctor": lambda a: _dispatch_cmd(cmd_doctor, a),
        "reglas": lambda a: _dispatch_cmd(cmd_reglas, a),
        "hook": lambda a: _dispatch_cmd(cmd_hook, a),
        "inbox": cmd_inbox,
        "watch": lambda a: _dispatch_cmd(cmd_watch, a),
        "history": lambda a: _dispatch_cmd(cmd_history, a),
        "wiki": cmd_wiki,
        "review": cmd_review,
        "ingest": cmd_ingest,
        "adapt": cmd_adapt,
        "secret": cmd_secret,
        "personal": cmd_personal,
        "export": cmd_export,
        "enrich": cmd_enrich,
        "pack": cmd_pack,
        "unpack": cmd_unpack,
        "mcp": cmd_mcp,
    }

    if args.cmd == "sync":
        inicio = time.perf_counter()
        try:
            if getattr(args, "migrate", False):
                cmd_sync_migrate(args)
            else:
                cmd_sync(args)
        except SystemExit as salida:
            _registrar_ejecucion(args, inicio, int(salida.code or 0))
            raise
        _registrar_ejecucion(args, inicio, 0)
    else:
        cmd_func = commands.get(args.cmd)
        if cmd_func:
            inicio = time.perf_counter()
            try:
                cmd_func(args)
            except SystemExit as salida:
                _registrar_ejecucion(args, inicio, int(salida.code or 0))
                raise
            _registrar_ejecucion(args, inicio, 0)
        else:
            p.print_help()


if __name__ == "__main__":
    main()

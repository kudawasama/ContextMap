"""Comandos de importación: git, sesiones, chats y Antigravity.

Agrupa todos los comandos que importan datos desde fuentes externas
y los convierten en eventos del mapa de contexto.
"""

from __future__ import annotations

import os

from context_map.application.commands._helpers import (
    RAW_DIR,
    ahora,
    ensure_dirs,
    project_name,
)
from context_map.application.commands.sync import do_sync
from context_map.core.models import Event
from context_map.domain.scanning import guardar_eventos_escaneados
from context_map.infrastructure.integrations.antigravity import importar_antigravity
from context_map.infrastructure.integrations.chat_export import importar_chat
from context_map.infrastructure.integrations.git import leer_historial_git
from context_map.infrastructure.integrations.hermes import importar_sesiones


def cmd_import_git(args) -> None:
    """Importa historial de commits de git como eventos.

    Clasifica commits por tipo: fix->CORRECCION, feat->IDEA, test->PRUEBA, etc.

    Args:
        args: Namespace de argparse con ``target``, ``project``, ``limit``
    """
    ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Leyendo historial git de: {os.path.abspath(ruta)}")

    history = leer_historial_git(ruta, limite=args.limit or 50)

    if not history.commits:
        print("No se encontraron commits o no es un repositorio git")
        return

    print(f"Commits encontrados: {len(history.commits)}")
    print(f"Tags: {len(history.tags)}")

    eventos = [
        Event(
            type="BASE",
            text=f"Repositorio git con {history.total_commits} commits totales, branch: {history.branch_actual}",
            timestamp=ahora(),
            source="git",
            tags=["git", "repo"],
        )
    ]

    for commit in history.commits[:20]:
        msg_lower = commit.mensaje.lower()
        if any(kw in msg_lower for kw in ["fix", "bug", "correc", "patch"]):
            tipo = "CORRECCION"
        elif any(kw in msg_lower for kw in ["feat", "add", "nuevo", "new"]):
            tipo = "IDEA"
        elif any(kw in msg_lower for kw in ["test", "qa"]):
            tipo = "PRUEBA"
        elif any(kw in msg_lower for kw in ["doc", "readme", "changelog"]):
            tipo = "CAMBIO"
        else:
            tipo = "CAMBIO"

        eventos.append(Event(
            type=tipo,
            text=f"[{commit.sha[:7]}] {commit.mensaje}",
            timestamp=commit.fecha or ahora(),
            source="git",
            tags=["commit", tipo.lower()],
        ))

    for tag in history.tags[:10]:
        eventos.append(Event(
            type="HITO",
            text=f"Release tag: {tag}",
            timestamp=ahora(),
            source="git",
            tags=["tag", "release"],
        ))

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        do_sync(args, project_name(args))


def cmd_import_sessions(args) -> None:
    """Importa sesiones de Hermes.

    Args:
        args: Namespace de argparse con ``db``, ``limit``, ``project``
    """
    ensure_dirs()

    print("Buscando base de datos de sesiones...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_sesiones(
        db_path=args.db,
        limite=args.limit or 5,
        output_path=output,
        project=project_name(args),
    )

    print(f"Sesiones importadas: {importados} eventos nuevos")

    if importados > 0:
        do_sync(args, project_name(args))


def cmd_import_chat(args) -> None:
    """Importa un archivo de chat externo.

    Args:
        args: Namespace de argparse con ``file``, ``project``
    """
    ensure_dirs()

    if not args.file:
        print("Error: especifica un archivo con --file")
        return

    print(f"Importando chat: {args.file}")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_chat(args.file, output)

    print(f"Eventos importados: {importados}")

    if importados > 0:
        do_sync(args, project_name(args))


def cmd_import_antigravity(args) -> None:
    """Importa chats de Antigravity IDE.

    Args:
        args: Namespace de argparse con ``limit``, ``project``
    """
    ensure_dirs()

    print("Importando conversaciones de Antigravity IDE...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_antigravity(
        ide=True,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Conversaciones importadas: {importados} eventos nuevos")

    if importados > 0:
        do_sync(args, project_name(args))

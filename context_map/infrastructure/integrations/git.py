"""Lector de historial git para Context Map Generator.

Extrae contexto de commits, tags, y ramas.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CommitInfo:
    """Información de un commit."""
    sha: str
    mensaje: str
    autor: str
    fecha: str
    archivos_modificados: list[str] = field(default_factory=list)


@dataclass
class GitHistory:
    """Historial git de un proyecto."""
    ruta_raiz: str
    branch_actual: str = ""
    commits: list[CommitInfo] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    total_commits: int = 0


def _ejecutar_git(ruta: str, args: list[str]) -> str:
    """Ejecuta un comando git y retorna la salida."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=ruta,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as err:
        logger.debug("Fallo al ejecutar git %s en %s: %s", args, ruta, err)
    return ""


def _parsear_commits(salida: str) -> list[CommitInfo]:
    """Parsea la salida de git log."""
    commits: list[CommitInfo] = []
    if not salida:
        return commits

    bloques = salida.split("\n\n")
    for bloque in bloques:
        if not bloque.strip():
            continue

        lineas = bloque.strip().split("\n")
        if len(lineas) < 2:
            continue

        # Primera línea: sha y mensaje
        primera = lineas[0]
        match = re.match(r"^([a-f0-9]+)\s+(.*)", primera)
        if not match:
            continue

        sha = match.group(1)
        mensaje = match.group(2)

        # Buscar autor y fecha
        autor = ""
        fecha = ""
        for linea in lineas[1:]:
            if linea.startswith("Author:"):
                autor = linea.replace("Author:", "").strip()
            elif linea.startswith("Date:"):
                fecha = linea.replace("Date:", "").strip()

        commits.append(CommitInfo(
            sha=sha,
            mensaje=mensaje,
            autor=autor,
            fecha=fecha,
        ))

    return commits


def leer_historial_git(
    ruta_raiz: str,
    limite: int = 50,
    desde: str | None = None,
) -> GitHistory:
    """Lee el historial git de un proyecto.

    Args:
        ruta_raiz: Ruta raíz del proyecto
        limite: Máximo de commits a leer
        desde: Fecha desde (ej: "2026-01-01")

    Returns:
        GitHistory con la información
    """
    history = GitHistory(ruta_raiz=ruta_raiz)

    # Verificar que es un repo git
    if not os.path.exists(os.path.join(ruta_raiz, ".git")):
        return history

    # Branch actual
    history.branch_actual = _ejecutar_git(ruta_raiz, ["branch", "--show-current"])

    # Tags
    tags_salida = _ejecutar_git(ruta_raiz, ["tag", "--list"])
    if tags_salida:
        history.tags = [t.strip() for t in tags_salida.split("\n") if t.strip()]

    # Commits
    args_log = [
        "log",
        f"--max-count={limite}",
        "--format=%H %s%nAuthor: %an%nDate: %ad%n",
        "--date=short",
    ]

    if desde:
        args_log.append(f"--since={desde}")

    log_salida = _ejecutar_git(ruta_raiz, args_log)
    history.commits = _parsear_commits(log_salida)
    history.total_commits = len(history.commits)

    # Contar commits totales (sin límite)
    total_salida = _ejecutar_git(ruta_raiz, ["rev-list", "--count", "HEAD"])
    if total_salida.isdigit():
        history.total_commits = int(total_salida)

    return history

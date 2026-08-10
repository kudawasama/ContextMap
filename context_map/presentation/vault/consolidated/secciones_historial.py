"""Renderizado de la sección 6.0-HISTORIAL para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import logging
import os
import subprocess
from collections import defaultdict

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown

logger = logging.getLogger(__name__)


def _render_versiones(project_name: str, fecha_actual: str, historial_dir: str, cabecera_fn, pie_fn) -> None:
    """Renderiza 6.3-Versiones.md con el changelog obtenido desde git.

    Args:
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        historial_dir (str): Directorio de la sección de historial.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    partes = cabecera_fn(
        "versiones", None, project_name, fecha_actual,
        ["context-map", "versiones", "changelog"],
        "# 6.3 Versiones",
    )
    partes.extend([
        "Registro de versiones del proyecto, generado a partir del historial git.",
        "",
    ])

    project_root = os.getcwd()
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, cwd=project_root,
            timeout=10
        )
        all_tags_list = [t.strip() for t in result.stdout.split("\n")
                         if t.strip() and "desktop.ini" not in t]

        if all_tags_list:
            partes.append("## Versiones publicadas")
            partes.append("")

            prev_tag = None
            for tag in all_tags_list:
                date_result = subprocess.run(
                    ["git", "log", "-1", "--format=%ai", tag],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_date = date_result.stdout.strip()[:10] if date_result.stdout.strip() else "?"

                msg_result = subprocess.run(
                    ["git", "tag", "-l", tag, "--format=%(contents)"],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_msg = msg_result.stdout.strip()

                if prev_tag:
                    log_result = subprocess.run(
                        ["git", "log", "--oneline", f"{tag}..{prev_tag}"],
                        capture_output=True, text=True, cwd=project_root,
                        timeout=10
                    )
                else:
                    log_result = subprocess.run(
                        ["git", "log", "--oneline", tag],
                        capture_output=True, text=True, cwd=project_root,
                        timeout=10
                    )

                commits = log_result.stdout.strip()
                commit_lines = [c for c in commits.split("\n") if c.strip()]
                commit_count = len(commit_lines)

                partes.append(f"### {tag} ({tag_date})")
                partes.append("")
                if tag_msg:
                    partes.append(tag_msg)
                    partes.append("")
                if commit_lines:
                    partes.append(f"**{commit_count} commits** desde la versión anterior:")
                    partes.append("")
                    for c in commit_lines[:20]:
                        partes.append(f"- `{c}`")
                    if commit_count > 20:
                        partes.append(f"- ... y {commit_count - 20} commits más")
                    partes.append("")

                prev_tag = tag
        else:
            partes.append("## Historial por Meses")
            partes.append("")

            log_result = subprocess.run(
                ["git", "log", "--oneline", "--format=%ai | %s"],
                capture_output=True, text=True, cwd=project_root,
                timeout=10
            )
            all_commits = log_result.stdout.strip().split("\n")

            meses: dict[str, list[str]] = defaultdict(list)
            for line in all_commits:
                if " | " in line:
                    date_part, msg = line.split(" | ", 1)
                    month_key = date_part[:7]
                    meses[month_key].append(msg)

            for mes in sorted(meses.keys(), reverse=True):
                items = meses[mes]
                partes.append(f"### {mes} ({len(items)} commits)")
                partes.append("")
                for msg in items[:15]:
                    partes.append(f"- {msg}")
                if len(items) > 15:
                    partes.append(f"- ... y {len(items) - 15} commits más")
                partes.append("")

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as err:
        logger.warning("No se pudo obtener el historial de versiones: %s", err)
        partes.append("_(No se pudo obtener el historial de versiones)_")
        partes.append("")

    partes.extend(pie_fn("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.3-Versiones.md", partes)


def _render_seccion_historial(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 6.0-HISTORIAL (6.0, 6.1, 6.2, 6.3).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    historial_dir = os.path.join(output_dir, "6.0-HISTORIAL")
    os.makedirs(historial_dir, exist_ok=True)

    cambio_only = [n for n in clasificados["CAMBIO"] if n.type == "CAMBIO"]
    correccion_only = [n for n in clasificados["CAMBIO"] if n.type == "CORRECCION"]

    partes = cabecera_fn(
        "seccion", "historial", project_name, fecha_actual,
        ["context-map", "historial"],
        f"# 6.0 Historial — {project_name}",
    )
    partes.extend([
        "Registro de cambios, correcciones y decisiones arquitectónicas del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        f"- [[6.1-Cambios|6.1 Cambios]] ({len(cambio_only)} registros)",
        f"- [[6.2-Correcciones|6.2 Correcciones]] ({len(correccion_only)} registros)",
        "- [[6.3-Versiones|6.3 Versiones / Changelog]]",
        "",
    ])
    if clasificados["HITO"]:
        partes.append("## 🎯 Hitos")
        partes.append("")
        for n in clasificados["HITO"]:
            partes.append(f"- 🎯 **{n.title}**: {n.summary or 'Hito alcanzado'}")
        partes.append("")
        partes.append("---")
        partes.append("")

    partes.extend(pie_fn("[[00-INDICE|⬅ Volver al índice]]"))
    _escribir_markdown(historial_dir, "6.0-HISTORIAL.md", partes)

    cambios_parts = cabecera_fn(
        "cambios", None, project_name, fecha_actual,
        ["context-map", "cambios"],
        "# 6.1 Cambios",
    )
    cambios_parts.extend([
        "Registro de cambios realizados en el proyecto.",
        "",
        "---",
        "",
    ])
    if cambio_only:
        from context_map.core.generators.generadores import _titulo_limpio

        for n in cambio_only:
            fecha = (n.created_at or "")[:10]
            cambios_parts.append(f"## 🔄 {_titulo_limpio(n.title)} ({fecha})")
            cambios_parts.append("")
            if n.summary and n.summary != n.title:
                cambios_parts.append(_titulo_limpio(n.summary))
                cambios_parts.append("")
    else:
        cambios_parts.append("_(No se registraron cambios)_")
        cambios_parts.append("")

    cambios_parts.extend(pie_fn("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.1-Cambios.md", cambios_parts)

    correcciones_parts = cabecera_fn(
        "correcciones", None, project_name, fecha_actual,
        ["context-map", "correcciones"],
        "# 6.2 Correcciones",
    )
    correcciones_parts.extend([
        "Registro de correcciones aplicadas al proyecto.",
        "",
        "---",
        "",
    ])
    if correccion_only:
        from context_map.core.generators.generadores import _titulo_limpio
        from context_map.presentation.vault.consolidated.secciones_backlog import (
            _es_todo_codigo,
        )

        for n in correccion_only:
            if _es_todo_codigo(n):
                continue  # TODO con código crudo no es una corrección del proyecto
            fecha = (n.created_at or "")[:10]
            correcciones_parts.append(f"## 🔧 {_titulo_limpio(n.title)} ({fecha})")
            correcciones_parts.append("")
            if n.summary and n.summary != n.title:
                correcciones_parts.append(_titulo_limpio(n.summary))
                correcciones_parts.append("")
        if len(correcciones_parts) <= 7:
            correcciones_parts.append("_(Correcciones de código (TODOs) filtradas — no son correcciones del proyecto)_")
            correcciones_parts.append("")
    else:
        correcciones_parts.append("_(No se registraron correcciones)_")
        correcciones_parts.append("")

    correcciones_parts.extend(pie_fn("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.2-Correcciones.md", correcciones_parts)

    _render_versiones(project_name, fecha_actual, historial_dir, cabecera_fn, pie_fn)

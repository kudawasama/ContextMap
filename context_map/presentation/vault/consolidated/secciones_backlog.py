"""Renderizado de la sección 5.0-BACKLOG para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown


def _render_seccion_backlog(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 5.0-BACKLOG (5.0, 5.1).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    backlog_dir = os.path.join(output_dir, "5.0-BACKLOG")
    os.makedirs(backlog_dir, exist_ok=True)

    partes = cabecera_fn(
        "seccion", "backlog", project_name, fecha_actual,
        ["context-map", "backlog"],
        f"# 5.0 Backlog — {project_name}",
    )
    partes.extend([
        "Tareas pendientes, TODOs e iniciativas registradas para el futuro del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        "- [[5.1-Tareas|5.1 Tareas]]",
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(backlog_dir, "5.0-BACKLOG.md", partes)

    tareas_parts = cabecera_fn(
        "tareas", None, project_name, fecha_actual,
        ["context-map", "tareas", "backlog"],
        "# 5.1 Tareas",
    )
    tareas_parts.extend([
        "Lista de tareas futuras y pendientes del proyecto.",
        "",
        "---",
        "",
    ])
    if clasificados["FUTURO"]:
        from context_map.core.generators import generar_contexto_narrativo
        for n in clasificados["FUTURO"]:
            estado_mark = "[x]" if n.status == "completado" else "[ ]"
            tareas_parts.append(f"## {estado_mark} {n.title}")
            tareas_parts.append("")
            if n.summary:
                tareas_parts.append(n.summary)
                tareas_parts.append("")
            tareas_parts.append(generar_contexto_narrativo(n))
            tareas_parts.append("")
    else:
        tareas_parts.append("- [x] No hay tareas pendientes en el backlog actual.")
        tareas_parts.append("")

    tareas_parts.extend(pie_fn("[[5.0-BACKLOG/5.0-BACKLOG|⬅ Volver a 5.0 Backlog]]"))
    _escribir_markdown(backlog_dir, "5.1-Tareas.md", tareas_parts)

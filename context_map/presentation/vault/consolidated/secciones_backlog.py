"""Renderizado de la sección 5.0-BACKLOG para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.escritura import _escribir_markdown


def _es_todo_scanner(n) -> bool:
    """True si el nodo es un TODO del scanner (con path 'TODO (ruta.py:...)').

    Aunque el texto sea legible, un TODO del código NO es una idea del
    proyecto: es deuda técnica. Se excluye de las secciones de ideas (2.x)
    para que el vault no muestre pendientes de código como ideas.

    Args:
        n (Node): Nodo FUTURO/IDEA del scanner.

    Returns:
        bool: True si debe excluirse de las ideas.
    """
    import re

    return bool(re.match(r"^TODO\s*\(", (n.title or "").strip()))


def _es_todo_codigo(n: Node) -> bool:
    """True si el nodo FUTURO es código crudo, un test o ruido de chat.

    Un TODO del código cuyo texto es código fuente (docstring, return, assert...),
    un archivo de pruebas o un mensaje de chat informal NO es una tarea del
    proyecto: se excluye del backlog para mantener limpias las tareas.

    Args:
        n (Node): Nodo FUTURO/IDEA a evaluar.

    Returns:
        bool: True si debe excluirse del backlog.
    """
    t = (n.title or "").strip()
    if "__tests__" in t or "/tests/" in t or "test_" in t:
        return True
    if "(◕‿◕)" in t or "~ ♪" in t or "sigo con todo" in t.lower() or "¡perfecto!" in t.lower():
        return True
    if not t.lower().startswith("todo"):
        return False
    marcas_codigo = (
        '"""', "return ", 'f"', "def ", "class ", "import ", "self.",
        "if ", "for ", "=>", "\\n", "print(", "pass", "None", "True", "False",
        "await ", "async ", "yield ", "logger.", "add_argument", "rest(",
        "todos =", "texto =", "cursor.", "conn.", "assert ",
        # Strings literales, listas de keywords y tipos
        '"', "= [", "if any(", "(Node)", "Nodo de tipo",
    )
    return any(m in t for m in marcas_codigo)


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
        from context_map.core.generators.generadores import _titulo_limpio

        tareas_agregadas = False
        for n in clasificados["FUTURO"]:
            if _es_todo_codigo(n):
                continue  # deuda técnica cruda: no es tarea del proyecto
            tareas_agregadas = True
            estado_mark = "[x]" if n.status == "completado" else "[ ]"
            tareas_parts.append(f"## {estado_mark} {_titulo_limpio(n.title)}")
            tareas_parts.append("")
            if n.summary:
                tareas_parts.append(_titulo_limpio(n.summary))
                tareas_parts.append("")
            tareas_parts.append(generar_contexto_narrativo(n))
            tareas_parts.append("")
        if not tareas_agregadas:
            tareas_parts.append("- [x] No hay tareas técnicas pendientes en el código. El backlog de trabajo vive en [[7.0-MANUAL/BACKLOG|7.0-MANUAL/BACKLOG.md]].")
            tareas_parts.append("")
    else:
        tareas_parts.append("- [x] No hay tareas pendientes en el backlog actual.")
        tareas_parts.append("")

    tareas_parts.extend(pie_fn("[[5.0-BACKLOG/5.0-BACKLOG|⬅ Volver a 5.0 Backlog]]"))
    _escribir_markdown(backlog_dir, "5.1-Tareas.md", tareas_parts)

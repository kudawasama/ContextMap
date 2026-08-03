"""Renderizado de la sección 3.0-ESTRUCTURA para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown


def _render_seccion_estructura(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 3.0-ESTRUCTURA (3.0, 3.1).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    estructura_dir = os.path.join(output_dir, "3.0-ESTRUCTURA")
    os.makedirs(estructura_dir, exist_ok=True)

    partes = cabecera_fn(
        "seccion", "estructura", project_name, fecha_actual,
        ["context-map", "estructura"],
        f"# 3.0 Estructura — {project_name}",
    )
    partes.extend([
        "Componentes base, entrypoints, documentación e identidad del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        "- [[3.1-Fundamentos|3.1 Fundamentos]]",
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(estructura_dir, "3.0-ESTRUCTURA.md", partes)

    fund_parts = cabecera_fn(
        "fundamentos", None, project_name, fecha_actual,
        ["context-map", "fundamentos", "estructura"],
        "# 3.1 Fundamentos",
    )
    fund_parts.extend([
        "Componentes base del proyecto con sus descripciones y orígenes.",
        "",
        "---",
        "",
    ])
    if clasificados["BASE"]:
        from context_map.core.generators import generar_contexto_narrativo
        seen_base: set[str] = set()
        for n in clasificados["BASE"]:
            key = n.title[:80]
            if key in seen_base:
                continue
            seen_base.add(key)
            fund_parts.append(f"## 📦 {n.title}")
            fund_parts.append("")
            if n.summary:
                fund_parts.append(n.summary)
                fund_parts.append("")
            fund_parts.append(generar_contexto_narrativo(n))
            fund_parts.append("")
    else:
        fund_parts.append("_(No se registraron componentes base)_")
        fund_parts.append("")

    fund_parts.extend(pie_fn("[[3.0-ESTRUCTURA/3.0-ESTRUCTURA|⬅ Volver a 3.0 Estructura]]"))
    _escribir_markdown(estructura_dir, "3.1-Fundamentos.md", fund_parts)

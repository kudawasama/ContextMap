"""Renderizado de la sección 4.0-RIESGOS para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown
from context_map.presentation.vault.templates import _normalize_tags, _safe_filename


def _render_nota_riesgo(
    n: Node,
    project_name: str,
    fecha_actual: str,
    directorio: str,
    pie_fn,
) -> None:
    """Renderiza una nota atómica de tipo RIESGO con contexto narrativo.

    Args:
        n (Node): Nodo RIESGO a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
        pie_fn (Callable): Generador de pie.
    """
    from context_map.core.generators import generar_contexto_narrativo

    filename = _safe_filename(n.title) + ".md"
    tags_list = _normalize_tags(n.tags, n.type)
    tags_str = ", ".join(f'"{t}"' for t in tags_list)
    partes = [
        "---",
        "type: riesgo",
        f"status: {n.status}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        f'source: "{n.source}"' if n.source else "source: ''",
        "---",
        "",
        f"# ⚠️ {n.title}",
        "",
    ]
    if n.summary:
        partes.append(n.summary)
        partes.append("")

    partes.append("## 🧠 Contexto Narrativo con Alma")
    partes.append("")
    partes.append(generar_contexto_narrativo(n))
    partes.append("")
    if n.evidence:
        partes.append("## 📋 Evidencia")
        partes.append("")
        for ev in n.evidence:
            partes.append(f"- {ev}")
        partes.append("")
    partes.extend(pie_fn("[[4.0-RIESGOS/4.0-RIESGOS|⬅ Volver a 4.0 Riesgos]]"))

    _escribir_markdown(directorio, filename, partes)


def _render_seccion_riesgos(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 4.0-RIESGOS (4.0 + notas atómicas de riesgo).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    riesgos_dir = os.path.join(output_dir, "4.0-RIESGOS")
    os.makedirs(riesgos_dir, exist_ok=True)

    partes = cabecera_fn(
        "seccion", "riesgos", project_name, fecha_actual,
        ["context-map", "riesgos"],
        f"# 4.0 Riesgos — {project_name}",
    )
    partes.extend([
        "Identificación de puntos de alta complejidad, alertas y riesgos del proyecto.",
        "",
        "---",
        "",
    ])
    if clasificados["RIESGO"]:
        partes.append("## Riesgos Identificados")
        partes.append("")
        seen_riesgo_idx: set[str] = set()
        for n in clasificados["RIESGO"]:
            key = n.title[:80]
            if key in seen_riesgo_idx:
                continue
            seen_riesgo_idx.add(key)
            slug = _safe_filename(n.title)
            partes.append(f"- [[{slug}|⚠️ {n.title}]]")
        partes.append("")
    else:
        partes.append("✅ **Sin riesgos o alertas críticas detectadas.**")
        partes.append("")

    partes.extend(pie_fn("[[00-INDICE|⬅ Volver al índice]]"))
    _escribir_markdown(riesgos_dir, "4.0-RIESGOS.md", partes)

    if clasificados["RIESGO"]:
        seen_riesgo_file: set[str] = set()
        for n in clasificados["RIESGO"]:
            key_file = n.title[:80]
            if key_file in seen_riesgo_file:
                continue
            seen_riesgo_file.add(key_file)
            _render_nota_riesgo(n, project_name, fecha_actual, riesgos_dir, pie_fn)

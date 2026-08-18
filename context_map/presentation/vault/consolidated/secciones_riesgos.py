"""Renderizado de la sección 4.0-RIESGOS para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import (
    _escribir_markdown,
    _linea_tags_inline,
)
from context_map.presentation.vault.templates import _normalize_tags, _safe_filename


def _render_nota_riesgo(
    n: Node,
    project_name: str,
    fecha_actual: str,
    directorio: str,
    pie_fn,
    todos_nodos: list[Node] | None = None,
) -> None:
    """Renderiza una nota atómica de tipo RIESGO con contexto narrativo.

    Args:
        n (Node): Nodo RIESGO a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
        pie_fn (Callable): Generador de pie.
        todos_nodos (list[Node] | None): Todos los nodos del mapa (conexiones).
    """
    from context_map.core.generators import generar_contexto_narrativo
    from context_map.core.generators.generadores import _titulo_limpio

    filename = _safe_filename(n.title) + ".md"
    tags_list = _normalize_tags(n.tags, n.type)
    tags_str = ", ".join(f'"{t}"' for t in tags_list)
    titulo_limpio = _titulo_limpio(n.title)
    summary_limpio = _titulo_limpio(n.summary)
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
        f"# ⚠️ {titulo_limpio}",
        "",
    ]
    linea_tags = _linea_tags_inline(n)
    if linea_tags:
        partes.append(linea_tags)
        partes.append("")
    if summary_limpio:
        partes.append(summary_limpio)
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

    if todos_nodos:
        from context_map.presentation.vault.consolidated.rutas import (
            conexiones_de_nodo,
            ruta_archivo_nodo,
            titulo_legible,
        )

        conexiones = conexiones_de_nodo(n, todos_nodos)
        partes.append("## 🔗 Conexiones")
        partes.append("")
        if conexiones:
            for rel in conexiones:
                destino = ruta_archivo_nodo(rel)
                if destino:
                    partes.append(f"- [[{destino}|{titulo_legible(rel)}]]")
        else:
            partes.append("_(Sin conexiones registradas aún)_")
        partes.append("")

    partes.extend(pie_fn("[[4.0-RIESGOS/4.0-RIESGOS|⬅ Volver a 4.0 Riesgos]]"))

    _escribir_markdown(directorio, filename, partes)


def _clave_dedup_riesgo(n) -> str:
    """Clave de dedup para riesgos: paths ordenados (mismo riesgo con distinto orden).

    'Archivos de alta complejidad: b.py, a.py' y 'Archivos de alta complejidad:
    a.py, b.py' son EL MISMO riesgo (scanner lo crea con orden variable).
    """
    import re

    paths = re.findall(r"[A-Za-z_][\w/\\]*\.(?:py|js|ts|md|json)", n.title or "")
    if paths:
        return "|".join(sorted(p.replace("\\", "/").strip() for p in paths))
    return (n.title or "")[:80]


def _es_riesgo_real(n) -> bool:
    """True si el nodo es realmente un RIESGO (no un IDEA mal clasificado)."""
    t = (n.title or "").strip().lower()
    if t.startswith("idea") or t.startswith("todo") or t.startswith("feature"):
        return False
    return n.type != "IDEA"


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
        from context_map.domain.normalization.similarity import deduplicar_elementos_similares

        partes.append("## Riesgos Identificados")
        partes.append("")
        seen_riesgo_idx: set[str] = set()
        riesgos_filtrados = [n for n in clasificados["RIESGO"] if _es_riesgo_real(n)]
        riesgos_unicos = deduplicar_elementos_similares(riesgos_filtrados, lambda r: r.title, umbral=0.85)

        for n in riesgos_unicos:
            key = _clave_dedup_riesgo(n)
            if key in seen_riesgo_idx:
                continue  # mismo riesgo con paths en distinto orden
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
        todos_nodos: list[Node] = [
            n for grupo in clasificados.values() for n in grupo
        ]
        for n in clasificados["RIESGO"]:
            if not _es_riesgo_real(n):
                continue  # IDEA/TODO mal clasificado como riesgo
            key_file = _clave_dedup_riesgo(n)
            if key_file in seen_riesgo_file:
                continue  # mismo riesgo con paths en distinto orden
            seen_riesgo_file.add(key_file)
            _render_nota_riesgo(
                n, project_name, fecha_actual, riesgos_dir, pie_fn,
                todos_nodos=todos_nodos,
            )

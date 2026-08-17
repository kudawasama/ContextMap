"""Renderizado de notas atómicas e índices de conceptos para la sección de Ideas.

Proporciona funciones para generar los nombres de archivo, estructuras de
notas atómicas `idea_{id}_{ACCION}.md`, batches de ideas completadas e índices
de concepto por estado.
"""

from __future__ import annotations

import os
import re

from context_map.core.models import Node
from context_map.core.normalization.standardize import inferir_concepto
from context_map.presentation.vault.consolidated.common import (
    _escribir_markdown,
    _linea_tags_inline,
)
from context_map.presentation.vault.templates import _normalize_tags

ICONOS_STATUS = {"completado": "✅", "pendiente": "⏳", "activo": "🔄"}

# Acción descriptiva por clasificación (para nombre de archivo)
ACCION_POR_CLASIFICACION: dict[str, str] = {
    "feature": "NUEVA_FUNCIONALIDAD",
    "fix": "CORRECCION_BUG",
    "refactor": "REFACTOR",
    "update": "MEJORA",
    "chore": "MANTENIMIENTO",
    "docs": "DOCUMENTACION",
    "test": "TEST",
    "style": "ESTILO",
    "perf": "PERFORMANCE",
    "security": "SEGURIDAD",
    "other": "GENERAL",
}


def _accion_nodo(n: Node) -> str:
    """Devuelve la acción descriptiva del nodo para el nombre de archivo."""
    clasif = getattr(n, "classification", "") or ""
    return ACCION_POR_CLASIFICACION.get(clasif, "GENERAL")


def _concepto_nodo(n: Node) -> str:
    """Devuelve el concepto del nodo, infiriéndolo si no está seteado."""
    if getattr(n, "concept", ""):
        return n.concept
    return inferir_concepto(n)


def _nombre_nota_idea(n: Node) -> str:
    """Genera el nombre de archivo de una idea, garantizado ÚNICO.

    Formato: idea_{id}_{ACCION}.md
    Ej: idea_FUTURO001_MANTENIMIENTO.md
    """
    id_limpio = re.sub(r"[^a-zA-Z0-9_-]", "", n.id or "")[:40] or "sin-id"
    accion = _accion_nodo(n)
    return f"idea_{id_limpio}_{accion}.md"


def _agrupar_por_concepto(nodos: list[Node]) -> dict[str, list[Node]]:
    """Agrupa nodos por concepto técnico.

    Returns:
        dict con concepto → lista de nodos.
    """
    grupos: dict[str, list[Node]] = {}
    for n in nodos:
        concepto = _concepto_nodo(n)
        grupos.setdefault(concepto, []).append(n)
    return dict(sorted(grupos.items()))


def _nombre_batch_idea(idx: int, total: int, concepto: str, batch_size: int = 10) -> str:
    """Genera el nombre de archivo del batch que contiene la idea completada.

    Las ideas completadas se agrupan en archivos batch numerados
    ``NN-CONCEPTO-INICIO-FIN.md`` para evitar decenas de notas sueltas.
    """
    batch_num = idx // batch_size + 1
    start_num = idx // batch_size * batch_size + 1
    end_num = min(start_num + batch_size - 1, total)
    return f"{batch_num:02d}-{concepto}-{start_num:02d}-{end_num:02d}.md"


def _render_nota_idea(
    n: Node,
    project_name: str,
    fecha_actual: str,
    directorio: str,
    status: str,
    backlink: str,
    pie_fn,
    todos_nodos: list[Node] | None = None,
) -> None:
    """Renderiza una nota atómica de tipo IDEA con contexto narrativo estructurado."""
    from context_map.core.generators import generar_contexto_narrativo
    from context_map.core.generators.generadores import _titulo_limpio

    filename = _nombre_nota_idea(n)
    tags_list = _normalize_tags(n.tags, n.type)
    tags_str = ", ".join(f'"{t}"' for t in tags_list)
    concepto = _concepto_nodo(n)
    clasif = getattr(n, "classification", "") or "idea"
    titulo_limpio = _titulo_limpio(n.title)
    summary_limpio = _titulo_limpio(n.summary)

    partes = [
        "---",
        "type: idea",
        f"status: {status}",
        f"concept: {concepto}",
        f"class: {clasif}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        f'source: "{n.source}"' if n.source else "source: ''",
        "---",
        "",
        f"# 📋 {titulo_limpio}",
        "",
        f"> **Concepto:** `{concepto}` · **Clasificación:** `{clasif}` · **Estado:** {ICONOS_STATUS.get(status, '💡')} {status}",
        "",
        "---",
        "",
        "## 💡 IDEA",
        "",
    ]
    linea_tags = _linea_tags_inline(n)
    if linea_tags:
        partes.append(linea_tags)
        partes.append("")
    if summary_limpio:
        partes.append(summary_limpio)
        partes.append("")

    partes.append("## 🧠 LÓGICA")
    partes.append("")
    partes.append(generar_contexto_narrativo(n))
    partes.append("")

    partes.append("## 🔧 MEJORA")
    partes.append("")
    if status == "pendiente":
        partes.append("- [ ] Pendiente de implementar")
    else:
        partes.append("- Implementada / en curso")
    partes.append("")

    partes.append("## ✅ CONCLUSIÓN")
    partes.append("")
    if status == "completado":
        partes.append(f"Esta idea fue implementada y forma parte de **{project_name}**.")
    else:
        partes.append(f"Idea registrada en el contexto de **{project_name}**.")
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
            partes.append("_(Sin conexiones registradas aún — se conecta al trabajar la historia)_")
        partes.append("")

    partes.extend(pie_fn(backlink))

    _escribir_markdown(directorio, filename, partes)


def _render_indice_concepto(
    concepto: str,
    nodos: list[Node],
    project_name: str,
    fecha_actual: str,
    directorio: str,
    status: str,
    status_label: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza el índice de un concepto dentro de una sección de estado."""
    seccion_dir = os.path.basename(os.path.dirname(directorio))
    archivo_padre_por_dir: dict[str, str] = {
        "2.1-Ideas-Pendientes": "2.1-Ideas-Pendientes",
        "2.2-Ideas-Futuras": "2.2-Ideas-Futuras",
        "2.3-Ideas-Completas-e-Implementadas": "2.3-Ideas-Completas",
    }
    archivo_padre = archivo_padre_por_dir.get(seccion_dir, seccion_dir)
    backlink = f"[[{archivo_padre}|⬅ Volver a {seccion_dir}]]"
    index_parts = cabecera_fn(
        "seccion", f"ideas-{status}-{concepto.lower()}", project_name, fecha_actual,
        ["context-map", "ideas", status, concepto.lower()],
        f"# {concepto} — {status_label} ({len(nodos)})",
    )
    index_parts.extend([
        f"Ideas **{concepto}** en estado **{status_label}**: **{len(nodos)}**",
        "",
        "---",
        "",
        "## Lista de Ideas",
        "",
    ])
    for i, n in enumerate(nodos):
        if status == "completado":
            slug = _nombre_batch_idea(i, len(nodos), concepto)
        else:
            slug = _nombre_nota_idea(n)
        icono = ICONOS_STATUS.get(n.status, "💡")
        index_parts.append(f"- {icono} [[{slug}|{n.title}]]")
    index_parts.extend(pie_fn(backlink))
    _escribir_markdown(directorio, f"{concepto}-{status_label}.md", index_parts)

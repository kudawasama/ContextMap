"""Renderizado de la sección 2.0-IDEAS para la bóveda Obsidian jerárquica.

Organiza las ideas por estado (pendiente, activo, completado) y dentro de
cada estado por CONCEPTO técnico (BASEDEDATOS, TUI, CLI, ETL, ...).

Cada idea es una nota atómica con nombre:
    idea_{timestamp}_{CONCEPTO}_{CLASIFICACION}.md

y contenido estructurado:
    IDEA → LÓGICA → MEJORA → CONCLUSIÓN
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

    Usa el ``id`` del nodo (único por definición) en lugar del timestamp:
    dos ideas del mismo concepto creadas el mismo segundo generaban el
    mismo nombre (idea_{ts}_{ACCION}.md), y Obsidian fusiona archivos con
    el mismo nombre base mezclando estados (pendientes/futuras/completas).
    """
    id_limpio = re.sub(r"[^a-zA-Z0-9_-]", "", n.id or "")[:40] or "sin-id"
    accion = _accion_nodo(n)
    return f"idea_{id_limpio}_{accion}.md"


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
    """Renderiza una nota atómica de tipo IDEA con contexto narrativo estructurado.

    Args:
        n (Node): Nodo IDEA a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
        status (str): Estado de la idea ('pendiente' | 'activo').
        backlink (str): Wikilink de regreso a la sección padre.
        pie_fn (Callable): Función generadora del cierre pie.
        todos_nodos (list[Node] | None): Todos los nodos del mapa (para la
            sección de conexiones). Si None, no se genera la sección.
    """
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
        # Mapa mental conectado: sección de conexiones con archivos reales
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

    Args:
        idx (int): Índice de la idea dentro de la lista del concepto (0-based).
        total (int): Cantidad total de ideas del concepto.
        concepto (str): Concepto técnico al que pertenece la idea.
        batch_size (int): Máximo de ideas por batch.

    Returns:
        str: Nombre del archivo batch que contiene la idea.
    """
    batch_num = idx // batch_size + 1
    start_num = idx // batch_size * batch_size + 1
    end_num = min(start_num + batch_size - 1, total)
    return f"{batch_num:02d}-{concepto}-{start_num:02d}-{end_num:02d}.md"


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
    # El archivo índice de la sección no siempre coincide con el nombre de la
    # carpeta (ej: 2.3-Ideas-Completas-e-Implementadas/ -> 2.3-Ideas-Completas.md)
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


def _render_seccion_ideas(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 2.0-IDEAS (2.0, 2.1, 2.2, 2.3, 2.4).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    ideas_dir = os.path.join(output_dir, "2.0-IDEAS")
    os.makedirs(ideas_dir, exist_ok=True)

    idea_nodes = clasificados["IDEA"]
    completadas = [n for n in idea_nodes if n.status == "completado"]
    pendientes = [n for n in idea_nodes if n.status == "pendiente"]
    activas = [n for n in idea_nodes if n.status == "activo"]

    # Filtrar TODOs del scanner (deuda técnica — no son ideas del proyecto)
    from context_map.presentation.vault.consolidated.secciones_backlog import (
        _es_todo_scanner,
    )

    completadas = [n for n in completadas if not _es_todo_scanner(n)]
    pendientes = [n for n in pendientes if not _es_todo_scanner(n)]
    activas = [n for n in activas if not _es_todo_scanner(n)]

    # Todos los nodos del mapa (para la sección de conexiones de cada nota)
    todos_nodos: list[Node] = [
        n for grupo in clasificados.values() for n in grupo
    ]

    partes = cabecera_fn(
        "seccion", "ideas", project_name, fecha_actual,
        ["context-map", "ideas"],
        f"# 2.0 Ideas — {project_name}",
    )
    partes.extend([
        f"Total de ideas registradas: **{len(idea_nodes)}**",
        "",
        "### Contadores por Estado",
        "",
        f"- ✅ Completadas: **{len(completadas)}**",
        f"- ⏳ Pendientes: **{len(pendientes)}**",
        f"- 🔄 Activas/Futuras: **{len(activas)}**",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
    ])
    sub_secciones = []
    if pendientes:
        sub_secciones.append("- [[2.1-Ideas-Pendientes/2.1-Ideas-Pendientes|2.1 Ideas Pendientes]]")
    if activas:
        sub_secciones.append("- [[2.2-Ideas-Futuras/2.2-Ideas-Futuras|2.2 Ideas Futuras]]")
    if completadas:
        sub_secciones.append("- [[2.3-Ideas-Completas-e-Implementadas/2.3-Ideas-Completas|2.3 Ideas Completas]]")
    sub_secciones.append("- [[2.4-Ideas-Relevantes|2.4 Ideas Relevantes]]")
    partes.extend(sub_secciones)
    partes.extend([
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(ideas_dir, "2.0-IDEAS.md", partes)

    # ============================================================
    # 2.1 Ideas Pendientes — agrupadas por concepto
    # ============================================================
    if pendientes:
        pendientes_dir = os.path.join(ideas_dir, "2.1-Ideas-Pendientes")
        os.makedirs(pendientes_dir, exist_ok=True)

        index_parts = cabecera_fn(
            "seccion", "ideas-pendientes", project_name, fecha_actual,
            ["context-map", "ideas", "pendientes"],
            f"# 2.1 Ideas Pendientes — {project_name}",
        )
        index_parts.extend([
            f"Ideas pendientes por implementar: **{len(pendientes)}**",
            "",
            "---",
            "",
            "## Conceptos",
            "",
        ])
        grupos = _agrupar_por_concepto(pendientes)
        for concepto, nodos in grupos.items():
            # Filtrar TODOs con código crudo (deuda técnica, no ideas del proyecto)
            from context_map.presentation.vault.consolidated.secciones_backlog import (
                _es_todo_codigo,
            )

            nodos_limpios = [n for n in nodos if not _es_todo_codigo(n)]
            nodos = nodos_limpios
            if not nodos:
                continue
            index_parts.append(f"- [[{concepto}-Pendientes|{concepto}]] ({len(nodos)})")
            concepto_dir = os.path.join(pendientes_dir, concepto)
            os.makedirs(concepto_dir, exist_ok=True)
            for n in nodos:
                _render_nota_idea(
                    n, project_name, fecha_actual, concepto_dir, "pendiente",
                    f"[[{concepto}-Pendientes|⬅ Volver a {concepto}]]",
                    pie_fn,
                    todos_nodos=todos_nodos,
                )
            _render_indice_concepto(
                concepto, nodos, project_name, fecha_actual, concepto_dir,
                "pendiente", "Pendientes", cabecera_fn, pie_fn,
            )
        index_parts.extend(pie_fn("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
        _escribir_markdown(pendientes_dir, "2.1-Ideas-Pendientes.md", index_parts)

    # ============================================================
    # 2.2 Ideas Futuras/Activas — agrupadas por concepto
    # ============================================================
    if activas:
        futuras_dir = os.path.join(ideas_dir, "2.2-Ideas-Futuras")
        os.makedirs(futuras_dir, exist_ok=True)

        index_parts = cabecera_fn(
            "seccion", "ideas-futuras", project_name, fecha_actual,
            ["context-map", "ideas", "futuras"],
            f"# 2.2 Ideas Futuras — {project_name}",
        )
        index_parts.extend([
            f"Ideas futuras registradas: **{len(activas)}**",
            "",
            "---",
            "",
            "## Conceptos",
            "",
        ])
        grupos = _agrupar_por_concepto(activas)
        for concepto, nodos in grupos.items():
            from context_map.presentation.vault.consolidated.secciones_backlog import (
                _es_todo_codigo,
            )

            nodos_limpios = [n for n in nodos if not _es_todo_codigo(n)]
            nodos = nodos_limpios
            if not nodos:
                continue
            index_parts.append(f"- [[{concepto}-Futuras|{concepto}]] ({len(nodos)})")
            concepto_dir = os.path.join(futuras_dir, concepto)
            os.makedirs(concepto_dir, exist_ok=True)
            for n in nodos:
                _render_nota_idea(
                    n, project_name, fecha_actual, concepto_dir, "activo",
                    f"[[{concepto}-Futuras|⬅ Volver a {concepto}]]",
                    pie_fn,
                    todos_nodos=todos_nodos,
                )
            _render_indice_concepto(
                concepto, nodos, project_name, fecha_actual, concepto_dir,
                "activo", "Futuras", cabecera_fn, pie_fn,
            )
        index_parts.extend(pie_fn("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
        _escribir_markdown(futuras_dir, "2.2-Ideas-Futuras.md", index_parts)

    # ============================================================
    # 2.3 Ideas Completas — agrupadas por concepto (batches)
    # ============================================================
    if completadas:
        completadas_dir = os.path.join(ideas_dir, "2.3-Ideas-Completas-e-Implementadas")
        os.makedirs(completadas_dir, exist_ok=True)

        index_parts = cabecera_fn(
            "seccion", "ideas-completas", project_name, fecha_actual,
            ["context-map", "ideas", "completadas"],
            f"# 2.3 Ideas Completas e Implementadas — {project_name}",
        )
        index_parts.extend([
            f"Ideas completadas acumuladas: **{len(completadas)}**",
            "",
            "---",
            "",
            "## Conceptos",
            "",
        ])
        grupos = _agrupar_por_concepto(completadas)
        for concepto, nodos in grupos.items():
            index_parts.append(f"- [[{concepto}-Completas|{concepto}]] ({len(nodos)})")
            concepto_dir = os.path.join(completadas_dir, concepto)
            os.makedirs(concepto_dir, exist_ok=True)

            batch_size = 10
            for batch_idx in range(0, len(nodos), batch_size):
                batch = nodos[batch_idx:batch_idx + batch_size]
                batch_num = batch_idx // batch_size + 1
                start_num = batch_idx + 1
                end_num = min(batch_idx + batch_size, len(nodos))
                filename = f"{batch_num:02d}-{concepto}-{start_num:02d}-{end_num:02d}.md"
                tags_str = ', '.join(f'"{t}"' for t in ["context-map", "ideas", "completadas", concepto.lower()])
                batch_parts = [
                    "---",
                    "type: ideas-completadas",
                    f"concept: {concepto}",
                    f"created: {fecha_actual}",
                    f'project: "{project_name}"',
                    f"tags: [{tags_str}]",
                    "---",
                    "",
                    f"# ✅ {concepto} — Ideas Completadas ({start_num}-{end_num} de {len(nodos)})",
                    "",
                ]
                for n in batch:
                    from context_map.core.generators.generadores import _titulo_limpio

                    batch_parts.append(f"## 🔧 {_titulo_limpio(n.title)}")
                    batch_parts.append("")
                    if n.summary:
                        batch_parts.append(_titulo_limpio(n.summary))
                        batch_parts.append("")
                batch_parts.extend(pie_fn(
                    f"[[{concepto}-Completas|⬅ Volver a {concepto}]]",
                ))
                _escribir_markdown(concepto_dir, filename, batch_parts)

            _render_indice_concepto(
                concepto, nodos, project_name, fecha_actual, concepto_dir,
                "completado", "Completas", cabecera_fn, pie_fn,
            )
        index_parts.extend(pie_fn("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
        _escribir_markdown(completadas_dir, "2.3-Ideas-Completas.md", index_parts)

    # ============================================================
    # 2.4 Ideas Relevantes
    # ============================================================
    seen_ideas_top: set[str] = set()
    top_ideas: list[Node] = []
    for n in idea_nodes:
        key = n.title[:80]
        if key not in seen_ideas_top and len(top_ideas) < 20:
            seen_ideas_top.add(key)
            top_ideas.append(n)
    # T6: orden cronológico por fecha de ingreso (created_at)
    top_ideas.sort(key=lambda n: (n.created_at or ""))

    ideas_top_parts = cabecera_fn(
        "ideas-relevantes", None, project_name, fecha_actual,
        ["context-map", "ideas", "relevantes"],
        "# 2.4 Ideas Relevantes",
    )
    ideas_top_parts.extend([
        "Las ideas más importantes y transversales del proyecto, ordenadas por fecha de ingreso.",
        "",
        "---",
        "",
    ])
    if top_ideas:
        for n in top_ideas:
            status_icon = ICONOS_STATUS.get(n.status, "💡")
            concepto = _concepto_nodo(n)
            fecha = (n.created_at or "")[:10] or "—"
            ideas_top_parts.append(
                f"- {status_icon} **{n.title}** ({n.status}) · `{concepto}` · 🗓️ {fecha}"
            )
            if n.summary:
                ideas_top_parts.append(f"  - {n.summary}")
        ideas_top_parts.append("")
    else:
        ideas_top_parts.append("_(No se registraron ideas)_")
        ideas_top_parts.append("")

    # T7: Base de ideas (Dataview) con fallback estático arriba
    ideas_top_parts.extend([
        "## 📊 Base de Ideas (Dataview)",
        "",
        "```dataview",
        "TABLE created AS \"Ingreso\", concept AS \"Concepto\", status AS \"Estado\"",
        "FROM \"2.0-IDEAS\"",
        "SORT created ASC",
        "```",
        "",
        "> Si no tienes el plugin Dataview, la lista ordenada de arriba es la fuente.",
        "",
    ])

    ideas_top_parts.extend(pie_fn("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
    _escribir_markdown(ideas_dir, "2.4-Ideas-Relevantes.md", ideas_top_parts)

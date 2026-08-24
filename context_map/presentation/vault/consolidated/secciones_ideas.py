"""Renderizado de la sección 2.0-IDEAS para la bóveda Obsidian jerárquica.

Organiza las ideas por estado (pendiente, activo, completado) y dentro de
cada estado por CONCEPTO técnico (BASEDEDATOS, TUI, CLI, ETL, ...).

Utiliza los helpers de renderizado de notas e índices definidos en
``notas_ideas.py``.
"""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown
from context_map.presentation.vault.consolidated.notas_ideas import (
    ACCION_POR_CLASIFICACION,
    ICONOS_STATUS,
    _accion_nodo,
    _agrupar_por_concepto,
    _concepto_nodo,
    _nombre_batch_idea,
    _nombre_nota_idea,
    _render_indice_concepto,
    _render_nota_idea,
)
from context_map.presentation.vault.consolidated.secciones_backlog import (
    _es_todo_codigo,
    _es_todo_scanner,
)

# Configuración declarativa de cada sub-sección de estado (2.1/2.2/2.3):
# - dir/archivo: rutas del índice del estado.
# - sufijo: el nombre único del índice de concepto ({CONCEPTO}-{sufijo}.md).
# - estado: el estado del nodo que agrupa.
# - titulo/descripcion: textos exactos históricos del índice del estado.
# - tags: etiquetas de la sub-sección (frente a los tags del nodo).
_SUB_SECCION_ESTADO: dict[str, dict[str, str]] = {
    "pendiente": {
        "dir": "2.1-Ideas-Pendientes",
        "archivo": "2.1-Ideas-Pendientes.md",
        "sufijo": "Pendientes",
        "estado": "pendiente",
        "titulo": "# 2.1 Ideas Pendientes — ",
        "descripcion": "Ideas pendientes por implementar: ",
        "tags": "ideas-pendientes",
        "tag_nodo": "pendientes",
        "batch": "false",
    },
    "activo": {
        "dir": "2.2-Ideas-Futuras",
        "archivo": "2.2-Ideas-Futuras.md",
        "sufijo": "Futuras",
        "estado": "activo",
        "titulo": "# 2.2 Ideas Futuras — ",
        "descripcion": "Ideas futuras registradas: ",
        "tags": "ideas-futuras",
        "tag_nodo": "futuras",
        "batch": "false",
    },
    "completado": {
        "dir": "2.3-Ideas-Completas-e-Implementadas",
        "archivo": "2.3-Ideas-Completas.md",
        "sufijo": "Completas",
        "estado": "completado",
        "titulo": "# 2.3 Ideas Completas e Implementadas — ",
        "descripcion": "Ideas completadas acumuladas: ",
        "tags": "ideas-completadas",
        "tag_nodo": "completadas",
        "batch": "true",
    },
}


def _filtrar_todos_idea(nodos: list[Node]) -> list[Node]:
    """Descarta los nodos que son TODOs del scanner (deuda técnica).

    Los TODOs del scanner no son ideas del proyecto: se filtran para que no
    contaminen los contadores ni los índices de conceptos.

    Args:
        nodos (list[Node]): Nodos IDEA candidatos.

    Returns:
        list[Node]: Nodos que no son TODOs del scanner.
    """
    return [n for n in nodos if not _es_todo_scanner(n)]


def _tags_batch_idea(concepto: str) -> str:
    """Construye el string YAML de tags para un batch de ideas completadas.

    Args:
        concepto (str): Concepto técnico del batch.

    Returns:
        str: Lista de tags formateada, p. ej. ``"context-map", "ideas"``.
    """
    tags = ["context-map", "ideas", "completadas", concepto.lower()]
    return ', '.join(f'"{t}"' for t in tags)


def _cargar_grupos(nodos: list[Node]) -> dict[str, list[Node]]:
    """Agrupa nodos por concepto descartando TODOs de código.

    Args:
        nodos (list[Node]): Nodos IDEA de un mismo estado.

    Returns:
        dict[str, list[Node]]: Mapeo concepto -> nodos limpios (no vacíos).
    """
    grupos = _agrupar_por_concepto(nodos)
    limpios: dict[str, list[Node]] = {}
    for concepto, grupo in grupos.items():
        nodos_limpios = [n for n in grupo if not _es_todo_codigo(n)]
        if nodos_limpios:
            limpios[concepto] = nodos_limpios
    return limpios


def _render_concepto_estado(
    estado: str,
    concepto: str,
    nodos: list[Node],
    project_name: str,
    fecha_actual: str,
    estado_dir: str,
    pie_fn,
    todos_nodos: list[Node] | None = None,
) -> None:
    """Renderiza un concepto dentro de la sub-sección de estado.

    Para ideas completadas escribe los batches ``NN-CONCEPTO-INICIO-FIN.md``
    (agrupados de 10) que el índice de concepto debe enlazar — nunca notas
    sueltas, para evitar nodos fantasma en el grafo. Para pendientes/activas
    escribe una nota atómica por idea.

    Args:
        estado (str): Estado de las ideas ('pendiente', 'activo', 'completado').
        concepto (str): Concepto técnico.
        nodos (list[Node]): Nodos limpios del concepto.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        estado_dir (str): Directorio de la sub-sección de estado.
        pie_fn (Callable): Generador de pie.
        todos_nodos (list[Node] | None): Todos los nodos del mapa (conexiones).
    """
    concepto_dir = os.path.join(estado_dir, concepto)
    os.makedirs(concepto_dir, exist_ok=True)

    if _SUB_SECCION_ESTADO[estado]["batch"] == "true":
        batch_size = 10
        for batch_idx in range(0, len(nodos), batch_size):
            batch = nodos[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            start_num = batch_idx + 1
            end_num = min(batch_idx + batch_size, len(nodos))
            filename = f"{batch_num:02d}-{concepto}-{start_num:02d}-{end_num:02d}.md"
            tags_str = _tags_batch_idea(concepto)
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
        return

    for n in nodos:
        _render_nota_idea(
            n, project_name, fecha_actual, concepto_dir, _SUB_SECCION_ESTADO[estado]["estado"],
            f"[[{concepto}-{_SUB_SECCION_ESTADO[estado]['sufijo']}|⬅ Volver a {concepto}]]",
            pie_fn,
            todos_nodos=todos_nodos,
        )


def _render_estado_ideas(
    estado: str,
    nodos: list[Node],
    project_name: str,
    fecha_actual: str,
    ideas_dir: str,
    cabecera_fn,
    pie_fn,
    todos_nodos: list[Node],
) -> None:
    """Renderiza la sub-sección completa de un estado de ideas (2.1/2.2/2.3).

    Escribe el índice del estado (``2.1-Ideas-Pendientes.md``, etc.), las
    notas/batches por concepto y los índices de concepto correspondientes.

    Args:
        estado (str): Estado de las ideas ('pendiente', 'activo', 'completado').
        nodos (list[Node]): Nodos IDEA del estado (ya filtrados).
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        ideas_dir (str): Directorio ``2.0-IDEAS`` de salida.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
        todos_nodos (list[Node]): Todos los nodos del mapa (conexiones).
    """
    cfg = _SUB_SECCION_ESTADO[estado]
    estado_dir = os.path.join(ideas_dir, cfg["dir"])
    os.makedirs(estado_dir, exist_ok=True)

    index_parts = cabecera_fn(
        "seccion", cfg["tags"], project_name, fecha_actual,
        ["context-map", "ideas", cfg["tag_nodo"]],
        f"{cfg['titulo'].rstrip()} {project_name}",
    )
    index_parts.extend([
        f"{cfg['descripcion']}**{len(nodos)}**",
        "",
        "---",
        "",
        "## Conceptos",
        "",
    ])
    grupos = _cargar_grupos(nodos)
    for concepto, grupo in grupos.items():
        index_parts.append(f"- [[{concepto}-{cfg['sufijo']}|{concepto}]] ({len(grupo)})")
        _render_concepto_estado(
            estado, concepto, grupo, project_name, fecha_actual,
            estado_dir, pie_fn, todos_nodos=todos_nodos,
        )
        _render_indice_concepto(
            concepto, grupo, project_name, fecha_actual,
            os.path.join(estado_dir, concepto),
            cfg["estado"], cfg["sufijo"], cabecera_fn, pie_fn,
        )
    index_parts.extend(pie_fn("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
    _escribir_markdown(estado_dir, cfg["archivo"], index_parts)


def _seleccionar_top_ideas(idea_nodes: list[Node], max_top: int = 20) -> list[Node]:
    """Selecciona las ideas más relevantes sin duplicar títulos.

    Deduplica por los primeros 80 caracteres del título y conserva hasta
    ``max_top`` ideas, ordenadas por fecha de ingreso ascendente.

    Args:
        idea_nodes (list[Node]): Todos los nodos IDEA del mapa.
        max_top (int): Máximo de ideas a incluir.

    Returns:
        list[Node]: Ideas seleccionadas ordenadas por fecha.
    """
    seen_ideas_top: set[str] = set()
    top_ideas: list[Node] = []
    for n in idea_nodes:
        key = n.title[:80]
        if key not in seen_ideas_top and len(top_ideas) < max_top:
            seen_ideas_top.add(key)
            top_ideas.append(n)
    top_ideas.sort(key=lambda n: (n.created_at or ""))
    return top_ideas


def _render_top_ideas(idea_nodes: list[Node], project_name: str, fecha_actual: str, ideas_dir: str, cabecera_fn, pie_fn) -> None:
    """Renderiza 2.4-Ideas-Relevantes con las 20 ideas más transversales.

    Args:
        idea_nodes (list[Node]): Todos los nodos IDEA del mapa.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        ideas_dir (str): Directorio ``2.0-IDEAS`` de salida.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    top_ideas = _seleccionar_top_ideas(idea_nodes)

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
    completadas = _filtrar_todos_idea([n for n in idea_nodes if n.status == "completado"])
    pendientes = _filtrar_todos_idea([n for n in idea_nodes if n.status == "pendiente"])
    activas = _filtrar_todos_idea([n for n in idea_nodes if n.status == "activo"])

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

    groups_nodos: list[Node] = [
        n for grupo in clasificados.values() for n in grupo
    ]
    if pendientes:
        _render_estado_ideas(
            "pendiente", pendientes, project_name, fecha_actual,
            ideas_dir, cabecera_fn, pie_fn, groups_nodos,
        )
    if activas:
        _render_estado_ideas(
            "activo", activas, project_name, fecha_actual,
            ideas_dir, cabecera_fn, pie_fn, groups_nodos,
        )
    if completadas:
        _render_estado_ideas(
            "completado", completadas, project_name, fecha_actual,
            ideas_dir, cabecera_fn, pie_fn, groups_nodos,
        )

    _render_top_ideas(idea_nodes, project_name, fecha_actual, ideas_dir, cabecera_fn, pie_fn)


__all__ = [
    "_render_seccion_ideas",
    "ICONOS_STATUS",
    "ACCION_POR_CLASIFICACION",
    "_accion_nodo",
    "_concepto_nodo",
    "_nombre_nota_idea",
    "_agrupar_por_concepto",
    "_nombre_batch_idea",
    "_render_nota_idea",
    "_render_indice_concepto",
]
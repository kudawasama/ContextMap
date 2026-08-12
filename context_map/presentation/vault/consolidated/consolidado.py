"""Renderizado de la bóveda Obsidian en modo consolidado.

Genera 8 notas temáticas sintéticas (índice MOC, propósito, ideas, estructura,
riesgos, backlog, historial y conexiones) a partir del grafo de contexto para
un consumo eficiente por parte de agentes de IA.
"""

from __future__ import annotations

import os
from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.common import (
    _clasificar_nodos,
    _escribir_markdown,
    _extract_project_purpose,
    _mencion_nodo_en_lista,
    _render_grafo_conexiones,
)

SECCIONES_MOC = [
    ("01-PROPOSITO", "01. Propósito del Proyecto"),
    ("02-IDEAS", "02. Ideas y Características"),
    ("03-ESTRUCTURA", "03. Estructura del Proyecto"),
    ("04-RIESGOS_Y_COMPLEJIDAD", "04. Riesgos y Complejidad"),
    ("05-BACKLOG_Y_TODOS", "05. Backlog y Tareas Pendientes"),
    ("06-HISTORIAL_Y_DECISIONES", "06. Historial y Decisiones"),
    ("00-CONEXIONES", "07. Grafo Completo de Conexiones"),
]


def _cabecera_nota(tipo: str, project_name: str, fecha_actual: str, tags: str, titulo: str) -> list[str]:
    """Construye el frontmatter YAML y encabezado estándar de una nota.

    Args:
        tipo (str): Valor del campo 'type' del frontmatter.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO de creación.
        tags (str): Lista de tags en formato YAML.
        titulo (str): Título principal de la nota.

    Returns:
        list[str]: Líneas iniciales de la nota (frontmatter + título).
    """
    return [
        "---",
        f"type: {tipo}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: {tags}",
        "---",
        "",
        titulo,
        "",
    ]


def _pie_nota(backlink: str = "[[00-INDICE|⬅ Volver al índice]]") -> list[str]:
    """Construye el cierre estándar de una nota con su wikilink de retorno.

    Args:
        backlink (str): Wikilink de navegación de regreso.

    Returns:
        list[str]: Líneas finales de la nota.
    """
    return [
        "---",
        backlink,
        "",
    ]


def _render_indice(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 00-INDICE.md con métricas, secciones y tags.

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista de aristas/relaciones.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = [
        "---",
        "type: moc",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"total_nodes: {len(nodes)}",
        f"total_edges: {len(edges)}",
        "tags: [context-map, indice, moc]",
        "---",
        "",
        f"# 🗺️ Índice MOC — {project_name}",
        "",
        "> Bóveda consolidada bajo el paradigma Obsidian Skills. Bóveda sin atomización para consumo eficiente de contexto en agentes de IA.",
        "",
        "---",
        "",
        "## 📊 Métricas Generales del Grafo",
        "",
        f"- 📦 Nodos Totales: **{len(nodes)}**",
        f"- 🔗 Conexiones (Edges): **{len(edges)}**",
        f"- 🧱 Estructura (BASE): **{len(clasificados['BASE'])}**",
        f"- 💡 Ideas (IDEA): **{len(clasificados['IDEA'])}**",
        f"- ⚠️ Riesgos (RIESGO): **{len(clasificados['RIESGO'])}**",
        f"- 🔮 Tareas (FUTURO): **{len(clasificados['FUTURO'])}**",
        f"- 🔄 Cambios (CAMBIO/CORRECCION): **{len(clasificados['CAMBIO'])}**",
        f"- 🎯 Hitos (HITO): **{len(clasificados['HITO'])}**",
        f"- 🧪 Pruebas (PRUEBA): **{len(clasificados['PRUEBA'])}**",
        "",
        "---",
        "",
        "## 📂 Secciones Consolidadas",
        "",
    ]
    for ruta, nombre in SECCIONES_MOC:
        partes.append(f"- [[{ruta}|{nombre}]]")
    partes.extend([
        "",
        "---",
        "",
        "## 🏷️ Tags Principales",
        "",
    ])

    all_tags: set[str] = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])
    partes.append(tags_badges or "`#context-map`")
    partes.append("")

    _escribir_markdown(output_dir, "00-INDICE.md", partes)


def _render_proposito(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 01-PROPOSITO.md con el propósito y datos clave del proyecto.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    proposito_texto = _extract_project_purpose(os.getcwd())
    partes = _cabecera_nota(
        "proposito", project_name, fecha_actual,
        "[context-map, proposito, proyecto]",
        f"# 🎯 Propósito del Proyecto — {project_name}",
    )
    if proposito_texto:
        partes.extend(["> " + proposito_texto, ""])

    partes.append("## 📋 Datos Clave")
    partes.append("")
    identidad_nodes = [n for n in clasificados["BASE"] if any(
        kw in (n.title + " " + (n.summary or "")).lower()
        for kw in ["proyecto", "identidad", "readme", "package", "setup", "entry"]
    )]
    if identidad_nodes:
        vistos: set[str] = set()
        for n in identidad_nodes:
            if _mencion_nodo_en_lista(n, vistos):
                continue
            partes.append(f"- **{n.title}**: {n.summary or '(sin descripcion)'}")
    else:
        partes.append("_(No se encontraron nodos de identidad del proyecto)_")
    partes.append("")
    partes.extend(_pie_nota())

    _escribir_markdown(output_dir, "01-PROPOSITO.md", partes)


def _render_ideas(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 02-IDEAS.md agrupando ideas por estado.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = _cabecera_nota(
        "ideas", project_name, fecha_actual,
        "[context-map, ideas, caracteristicas]",
        f"# 💡 Ideas y Características — {project_name}",
    )
    partes.extend([
        "Listado de ideas, features y conceptos registrados en el proyecto.",
        "",
        "---",
        "",
    ])

    idea_nodes = clasificados["IDEA"]
    if idea_nodes:
        completadas = [n for n in idea_nodes if n.status == "completado"]
        pendientes = [n for n in idea_nodes if n.status == "pendiente"]
        activas = [n for n in idea_nodes if n.status == "activo"]

        seen_total: set[str] = set()

        def _agrupar(partes_lista: list[str], titulo: str, icono: str,
                     nodos_lista: list[Node], emoji: str) -> None:
            if not nodos_lista:
                return
            partes_lista.append(f"## {icono} {titulo}")
            partes_lista.append("")
            vistos: set[str] = set()
            for n in nodos_lista:
                if _mencion_nodo_en_lista(n, vistos):
                    continue
                seen_total.add(n.title[:80])
                prefijo = emoji if n.source == "git" else "📝"
                partes_lista.append(f"### {prefijo} {n.title}")
                if n.summary and n.summary != n.title:
                    partes_lista.append(n.summary)
                partes_lista.append("")

        _agrupar(partes, "Completadas", "✅", completadas, "🔧")
        _agrupar(partes, "Pendientes", "⏳", pendientes, "📋")
        _agrupar(partes, "Activas", "🔄", activas, "⚡")

        if not seen_total:
            partes.append("_(No se registraron ideas o características)_")
            partes.append("")
    else:
        partes.append("_(No se registraron ideas o características)_")
        partes.append("")

    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "02-IDEAS.md", partes)


def _render_estructura(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 03-ESTRUCTURA.md con los componentes base del proyecto.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = _cabecera_nota(
        "estructura", project_name, fecha_actual,
        "[context-map, estructura]",
        f"# 🧱 Estructura del Proyecto — {project_name}",
    )
    partes.extend([
        "Componentes base, entrypoints, documentación e identidad del proyecto.",
        "",
        "---",
        "",
    ])
    if clasificados["BASE"]:
        vistos: set[str] = set()
        for n in clasificados["BASE"]:
            if _mencion_nodo_en_lista(n, vistos):
                continue
            partes.append(f"- **{n.title}**")
            if n.summary:
                partes.append(f"  - {n.summary}")
            if n.source:
                partes.append(f"  - *Origen*: `{n.source}`")
            partes.append("")
    else:
        partes.append("_(No se registraron componentes base)_")
        partes.append("")

    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "03-ESTRUCTURA.md", partes)


def _render_riesgos(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 04-RIESGOS_Y_COMPLEJIDAD.md con alertas y cobertura de pruebas.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = _cabecera_nota(
        "riesgos", project_name, fecha_actual,
        "[context-map, riesgo, complejidad]",
        f"# ⚠️ Riesgos y Complejidad — {project_name}",
    )
    partes.extend([
        "Identificación de puntos de alta complejidad, alertas de mantenimiento y cobertura de pruebas.",
        "",
        "---",
        "",
        "## 🚨 Alertas de Riesgo y Alta Complejidad",
        "",
    ])
    if clasificados["RIESGO"]:
        vistos: set[str] = set()
        for n in clasificados["RIESGO"]:
            if _mencion_nodo_en_lista(n, vistos):
                continue
            partes.append(f"### ⚠️ {n.title}")
            partes.append(f"{n.summary or 'Punto de atención técnica'}")
            if n.evidence:
                partes.append("- **Evidencia**:")
                for ev in n.evidence:
                    partes.append(f"  - {ev}")
            partes.append("")
    else:
        partes.append("✅ **Sin riesgos o alertas críticas detectadas.**")
        partes.append("")

    if clasificados["PRUEBA"]:
        partes.append("## 🧪 Cobertura de Pruebas Detectadas")
        partes.append("")
        vistos_prueba: set[str] = set()
        for n in clasificados["PRUEBA"]:
            if _mencion_nodo_en_lista(n, vistos_prueba):
                continue
            partes.append(f"- **{n.title}**: {n.summary or 'Test'}")
        partes.append("")

    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "04-RIESGOS_Y_COMPLEJIDAD.md", partes)


def _render_backlog(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 05-BACKLOG_Y_TODOS.md con las tareas futuras del proyecto.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = _cabecera_nota(
        "backlog", project_name, fecha_actual,
        "[context-map, backlog, todos]",
        f"# 🔮 Backlog y Tareas Pendientes — {project_name}",
    )
    partes.extend([
        "Listado consolidado de tareas futuras, TODOs e iniciativas registradas en el proyecto.",
        "",
        "---",
        "",
        "## 📋 Checklists de Tareas (TODOs / FUTURO)",
        "",
    ])
    if clasificados["FUTURO"]:
        vistos: set[str] = set()
        for n in clasificados["FUTURO"]:
            if _mencion_nodo_en_lista(n, vistos):
                continue
            estado_mark = "[x]" if n.status == "completado" else "[ ]"
            partes.append(f"- {estado_mark} **{n.title}**")
            if n.summary:
                partes.append(f"  - _{n.summary}_")
    else:
        partes.append("- [x] No hay tareas pendientes en el backlog actual.")

    partes.append("")
    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "05-BACKLOG_Y_TODOS.md", partes)


def _render_historial(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 06-HISTORIAL_Y_DECISIONES.md con hitos, cambios y correcciones.

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    partes = _cabecera_nota(
        "historial", project_name, fecha_actual,
        "[context-map, historial, cambios]",
        f"# 🔄 Historial y Decisiones — {project_name}",
    )
    partes.extend([
        "Registro consolidado de cambios, correcciones y decisiones arquitectónicas.",
        "",
        "---",
        "",
        "## 🎯 Hitos",
        "",
    ])
    if clasificados["HITO"]:
        for n in clasificados["HITO"]:
            partes.append(f"- 🎯 **{n.title}**: {n.summary or 'Hito alcanzado'}")
        partes.append("")
    else:
        partes.append("_(Sin hitos registrados)_")
        partes.append("")

    partes.append("## 🔄 Registro de Cambios y Correcciones")
    partes.append("")
    if clasificados["CAMBIO"]:
        vistos: set[str] = set()
        for n in clasificados["CAMBIO"][:50]:
            if _mencion_nodo_en_lista(n, vistos):
                continue
            icono = "🔧" if n.type == "CORRECCION" else "🔄"
            partes.append(f"- {icono} **{n.title}** ({n.created_at or 'Fecha no esp.'})")
            if n.summary and n.summary != n.title:
                partes.append(f"  - {n.summary}")
        partes.append("")
    else:
        partes.append("_(Sin registros de cambios)_")
        partes.append("")

    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "06-HISTORIAL_Y_DECISIONES.md", partes)


def _render_consolidated_vault(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo consolidado (8 notas temáticas sintéticas)."""
    # Limpiar el vault SIN destruir el trabajo manual (.manual/ + preserve:true)
    from context_map.presentation.vault.preservar import limpiar_vault

    limpiar_vault(output_dir)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    clasificados = _clasificar_nodos(nodes)

    _render_indice(project_name, nodes, edges, clasificados, fecha_actual, output_dir)
    _render_proposito(project_name, clasificados, fecha_actual, output_dir)
    _render_ideas(project_name, clasificados, fecha_actual, output_dir)
    _render_estructura(project_name, clasificados, fecha_actual, output_dir)
    _render_riesgos(project_name, clasificados, fecha_actual, output_dir)
    _render_backlog(project_name, clasificados, fecha_actual, output_dir)
    _render_historial(project_name, clasificados, fecha_actual, output_dir)
    _render_grafo_conexiones(output_dir, nodes, edges)

    return output_dir

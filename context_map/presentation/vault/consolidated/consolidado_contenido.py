"""Notas consolidadas de contenido: ideas, riesgos, backlog e historial.

Son las cuatro notas que describen **qué se está haciendo** y **qué duele**:
ideas agrupadas por estado, alertas de complejidad con su cobertura de pruebas,
tareas pendientes y el registro de cambios.
"""

from __future__ import annotations

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.consolidado_base import (
    _cabecera_nota,
    _pie_nota,
)
from context_map.presentation.vault.consolidated.escritura import _escribir_markdown
from context_map.presentation.vault.consolidated.nodos import _mencion_nodo_en_lista


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


def _render_lista_riesgos(clasificados: dict[str, list[Node]], partes: list[str]) -> None:
    """Añade los bloques de nodos de RIESGO al listado de la sección de riesgos.

    Args:
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        partes (list[str]): Acumulador de líneas Markdown.
    """
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


def _render_lista_pruebas(clasificados: dict[str, list[Node]], partes: list[str]) -> None:
    """Añade la lista de nodos PRUEBA detectados a la sección de riesgos.

    Args:
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        partes (list[str]): Acumulador de líneas Markdown.
    """
    partes.append("## 🧪 Cobertura de Pruebas Detectadas")
    partes.append("")
    vistos_prueba: set[str] = set()
    for n in clasificados["PRUEBA"]:
        if _mencion_nodo_en_lista(n, vistos_prueba):
            continue
        partes.append(f"- **{n.title}**: {n.summary or 'Test'}")
    partes.append("")


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
        _render_lista_riesgos(clasificados, partes)
    else:
        partes.append("✅ **Sin riesgos o alertas críticas detectadas.**")
        partes.append("")

    if clasificados["PRUEBA"]:
        _render_lista_pruebas(clasificados, partes)

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


def _render_lista_cambios(clasificados: dict[str, list[Node]], partes: list[str]) -> None:
    """Añade el registro de cambios y correcciones a la sección de historial.

    Args:
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        partes (list[str]): Acumulador de líneas Markdown.
    """
    vistos: set[str] = set()
    for n in clasificados["CAMBIO"][:50]:
        if _mencion_nodo_en_lista(n, vistos):
            continue
        icono = "🔧" if n.type == "CORRECCION" else "🔄"
        partes.append(f"- {icono} **{n.title}** ({n.created_at or 'Fecha no esp.'})")
        if n.summary and n.summary != n.title:
            partes.append(f"  - {n.summary}")
    partes.append("")


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
        _render_lista_cambios(clasificados, partes)
    else:
        partes.append("_(Sin registros de cambios)_")
        partes.append("")

    partes.extend(_pie_nota())
    _escribir_markdown(output_dir, "06-HISTORIAL_Y_DECISIONES.md", partes)

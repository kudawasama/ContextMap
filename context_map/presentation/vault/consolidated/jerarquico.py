"""Renderizado de la bóveda Obsidian en modo jerárquico en árbol.

Genera la estructura temática en árbol con 6 secciones raíz (1.0-6.0), sus
sub-secciones y notas atómicas, respetando la topología estricta: el índice
enlaza solo a secciones raíz, cada sección raíz a sus sub-nodos, y las hojas
únicamente a su sección padre.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.common import (
    _clasificar_nodos,
    _escribir_markdown,
    _extract_project_purpose,
    _render_grafo_conexiones,
)
from context_map.presentation.vault.templates import _normalize_tags, _safe_filename

logger = logging.getLogger(__name__)

TAG_FIXTOS: dict[str, list[str]] = {}


def _cabecera(
    tipo: str, subtype: str | None, project_name: str, fecha_actual: str,
    tags: list[str], titulo: str,
) -> list[str]:
    """Construye frontmatter YAML y encabezado para notas jerárquicas.

    Args:
        tipo (str): Valor del campo 'type'.
        subtype (str | None): Valor del campo 'subtype' si corresponde.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        tags (list[str]): Lista de tags.
        titulo (str): Título principal de la nota.

    Returns:
        list[str]: Líneas iniciales de la nota.
    """
    tags_str = ", ".join(tags)
    partes = [
        "---",
        f"type: {tipo}",
    ]
    if subtype:
        partes.append(f"subtype: {subtype}")
    partes.extend([
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        "---",
        "",
        titulo,
        "",
    ])
    return partes


def _pie(backlink: str) -> list[str]:
    """Construye el cierre estándar con wikilink de retorno.

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


def _render_nota_idea(
    n: Node, project_name: str, fecha_actual: str,
    directorio: str, status: str, backlink: str,
) -> None:
    """Renderiza una nota atómica de tipo IDEA con contexto narrativo.

    Args:
        n (Node): Nodo IDEA a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
        status (str): Estado de la idea ('pendiente' | 'activo').
        backlink (str): Wikilink de regreso a la sección padre.
    """
    from context_map.core.generators import generar_contexto_narrativo

    filename = _safe_filename(n.title) + ".md"
    tags_list = _normalize_tags(n.tags, n.type)
    tags_str = ", ".join(f'"{t}"' for t in tags_list)
    partes = [
        "---",
        "type: idea",
        f"status: {status}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        f'source: "{n.source}"' if n.source else "source: ''",
        "---",
        "",
        f"# 📋 {n.title}",
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
    partes.extend(_pie(backlink))

    _escribir_markdown(directorio, filename, partes)


def _render_nota_riesgo(
    n: Node, project_name: str, fecha_actual: str, directorio: str,
) -> None:
    """Renderiza una nota atómica de tipo RIESGO con contexto narrativo.

    Args:
        n (Node): Nodo RIESGO a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
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
    partes.extend(_pie("[[4.0-RIESGOS/4.0-RIESGOS|⬅ Volver a 4.0 Riesgos]]"))

    _escribir_markdown(directorio, filename, partes)


def _render_seccion_proposito(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 1.0-PROPOSITO (1.0, 1.1, 1.2, 1.3).

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista de aristas/relaciones.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    proposito_dir = os.path.join(output_dir, "1.0-PROPOSITO")
    os.makedirs(proposito_dir, exist_ok=True)

    partes = _cabecera(
        "seccion", "proposito", project_name, fecha_actual,
        ["context-map", "proposito"],
        f"# 1.0 Propósito — {project_name}",
    )
    partes.extend([
        "Sección que define la identidad, el propósito y los datos clave del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        "- [[1.1-Mapa-Mental-Narrativo|1.1 Mapa Mental Narrativo]]",
        "- [[1.2-Datos-Clave|1.2 Datos Clave]]",
        "- [[1.3-Proposito|1.3 Propósito]]",
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(proposito_dir, "1.0-PROPOSITO.md", partes)

    proposito_texto = _extract_project_purpose(os.getcwd())

    readme_content = ""
    readme_path = os.path.join(os.getcwd(), "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, encoding="utf-8") as rf:
                readme_content = rf.read().strip()
        except Exception as err:
            logger.warning("No se pudo leer README.md: %s", err)
            readme_content = ""

    narrativa_parts = _cabecera(
        "narrativa", None, project_name, fecha_actual,
        ["context-map", "narrativa", "mapa-mental"],
        "# 1.1 Mapa Mental Narrativo",
    )
    if proposito_texto:
        narrativa_parts.extend(["> " + proposito_texto, ""])

    if readme_content:
        narrativa_parts.extend([
            "## 📖 Documentación Principal (README)",
            "",
            readme_content,
            "",
        ])
    else:
        narrativa_parts.extend([
            "## 📖 Dominio del Proyecto",
            "",
            f"El proyecto **{project_name}** captura el dominio contextual del sistema a través de {len(nodes)} nodos de arquitectura, decisiones y tareas.",
            "",
        ])

    narrativa_parts.extend(_pie("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.1-Mapa-Mental-Narrativo.md", narrativa_parts)

    datos_clave_parts = _cabecera(
        "datos-clave", None, project_name, fecha_actual,
        ["context-map", "datos-clave", "metricas"],
        "# 1.2 Datos Clave",
    )
    datos_clave_parts.extend([
        "Métricas y estadísticas del proyecto extraídas del análisis.",
        "",
        "---",
        "",
        "## 📊 Métricas del Proyecto",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Nodos totales | {len(nodes)} |",
        f"| Conexiones | {len(edges)} |",
        f"| Componentes BASE | {len(clasificados['BASE'])} |",
        f"| Ideas registradas | {len(clasificados['IDEA'])} |",
        f"| Riesgos identificados | {len(clasificados['RIESGO'])} |",
        f"| Tareas FUTURO | {len(clasificados['FUTURO'])} |",
        f"| Cambios y Correcciones | {len(clasificados['CAMBIO'])} |",
        f"| Hitos | {len(clasificados['HITO'])} |",
        "",
    ])
    metric_nodes = [n for n in clasificados["BASE"] if any(
        kw in (n.title + " " + (n.summary or "")).lower()
        for kw in ["archivo", "linea", "file", "line", "metric", "métrica"]
    )]
    if metric_nodes:
        datos_clave_parts.extend([
            "## 📁 Métricas de Archivos",
            "",
            "| Archivo | Descripción |",
            "|---------|-------------|",
        ])
        for n in metric_nodes[:10]:
            datos_clave_parts.append(f"| {n.title} | {n.summary or '—'} |")
        datos_clave_parts.append("")

    datos_clave_parts.extend(_pie("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.2-Datos-Clave.md", datos_clave_parts)

    identidad_parts = _cabecera(
        "identidad", None, project_name, fecha_actual,
        ["context-map", "identidad", "proposito"],
        "# 1.3 Propósito",
    )
    identidad_parts.extend([
        "Identidad y configuración fundamental del proyecto.",
        "",
        "---",
        "",
    ])
    identidad_nodes = [n for n in clasificados["BASE"] if any(
        kw in (n.title + " " + (n.summary or "")).lower()
        for kw in ["proyecto", "identidad", "readme", "package", "setup", "entry", "config", "doc"]
    )]
    if identidad_nodes:
        for n in identidad_nodes:
            identidad_parts.append(f"- **{n.title}**: {n.summary or '(sin descripción)'}")
        identidad_parts.append("")
    else:
        identidad_parts.append("_(No se encontraron nodos de identidad del proyecto)_")
        identidad_parts.append("")

    identidad_parts.extend(_pie("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.3-Proposito.md", identidad_parts)


def _render_seccion_ideas(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 2.0-IDEAS (2.0, 2.1, 2.2, 2.3, 2.4).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    ideas_dir = os.path.join(output_dir, "2.0-IDEAS")
    os.makedirs(ideas_dir, exist_ok=True)

    idea_nodes = clasificados["IDEA"]
    completadas = [n for n in idea_nodes if n.status == "completado"]
    pendientes = [n for n in idea_nodes if n.status == "pendiente"]
    activas = [n for n in idea_nodes if n.status == "activo"]

    partes = _cabecera(
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
        "- [[2.1-Ideas-Pendientes/2.1-Ideas-Pendientes|2.1 Ideas Pendientes]]",
        "- [[2.2-Ideas-Futuras/2.2-Ideas-Futuras|2.2 Ideas Futuras]]",
        "- [[2.3-Ideas-Completas-e-Implementadas/2.3-Ideas-Completas|2.3 Ideas Completas]]",
        "- [[2.4-Ideas-Relevantes|2.4 Ideas Relevantes]]",
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(ideas_dir, "2.0-IDEAS.md", partes)

    if pendientes:
        pendientes_dir = os.path.join(ideas_dir, "2.1-Ideas-Pendientes")
        os.makedirs(pendientes_dir, exist_ok=True)

        index_parts = _cabecera(
            "seccion", "ideas-pendientes", project_name, fecha_actual,
            ["context-map", "ideas", "pendientes"],
            f"# 2.1 Ideas Pendientes — {project_name}",
        )
        index_parts.extend([
            f"Ideas pendientes por implementar: **{len(pendientes)}**",
            "",
            "---",
            "",
            "## Lista de Ideas Pendientes",
            "",
        ])
        for n in pendientes:
            slug = _safe_filename(n.title)
            index_parts.append(f"- [[{slug}|⏳ {n.title}]]")
        index_parts.extend(_pie("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
        _escribir_markdown(pendientes_dir, "2.1-Ideas-Pendientes.md", index_parts)

        for n in pendientes:
            _render_nota_idea(
                n, project_name, fecha_actual, pendientes_dir, "pendiente",
                "[[2.1-Ideas-Pendientes/2.1-Ideas-Pendientes|⬅ Volver a 2.1 Ideas Pendientes]]",
            )

    if activas:
        futuras_dir = os.path.join(ideas_dir, "2.2-Ideas-Futuras")
        os.makedirs(futuras_dir, exist_ok=True)

        index_parts = _cabecera(
            "seccion", "ideas-futuras", project_name, fecha_actual,
            ["context-map", "ideas", "futuras"],
            f"# 2.2 Ideas Futuras — {project_name}",
        )
        index_parts.extend([
            f"Ideas futuras registradas: **{len(activas)}**",
            "",
            "---",
            "",
            "## Lista de Ideas Futuras",
            "",
        ])
        for n in activas:
            slug = _safe_filename(n.title)
            index_parts.append(f"- [[{slug}|🔮 {n.title}]]")
        index_parts.extend(_pie("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
        _escribir_markdown(futuras_dir, "2.2-Ideas-Futuras.md", index_parts)

        for n in activas:
            _render_nota_idea(
                n, project_name, fecha_actual, futuras_dir, "activo",
                "[[2.2-Ideas-Futuras/2.2-Ideas-Futuras|⬅ Volver a 2.2 Ideas Futuras]]",
            )

    if completadas:
        completadas_dir = os.path.join(ideas_dir, "2.3-Ideas-Completas-e-Implementadas")
        os.makedirs(completadas_dir, exist_ok=True)

        index_parts = _cabecera(
            "seccion", "ideas-completas", project_name, fecha_actual,
            ["context-map", "ideas", "completadas"],
            f"# 2.3 Ideas Completas e Implementadas — {project_name}",
        )
        index_parts.extend([
            f"Ideas completadas acumuladas: **{len(completadas)}**",
            "",
            "---",
            "",
        ])
        _escribir_markdown(completadas_dir, "2.3-Ideas-Completas.md", index_parts)

        batch_size = 10
        for batch_idx in range(0, len(completadas), batch_size):
            batch = completadas[batch_idx:batch_idx + batch_size]
            batch_num = batch_idx // batch_size + 1
            start_num = batch_idx + 1
            end_num = min(batch_idx + batch_size, len(completadas))
            filename = f"{batch_num:02d}-features-{start_num:02d}-{end_num:02d}.md"
            tags_str = ', '.join(f'"{t}"' for t in ["context-map", "ideas", "completadas"])
            batch_parts = [
                "---",
                "type: ideas-completadas",
                f"created: {fecha_actual}",
                f'project: "{project_name}"',
                f"tags: [{tags_str}]",
                "---",
                "",
                f"# ✅ Ideas Completadas ({start_num}-{end_num} de {len(completadas)})",
                "",
            ]
            for n in batch:
                batch_parts.append(f"## 🔧 {n.title}")
                batch_parts.append("")
                if n.summary:
                    batch_parts.append(n.summary)
                    batch_parts.append("")
            batch_parts.extend(_pie(
                "[[2.3-Ideas-Completas-e-Implementadas/2.3-Ideas-Completas|⬅ Volver a 2.3 Ideas Completas]]",
            ))
            _escribir_markdown(completadas_dir, filename, batch_parts)

    seen_ideas_top: set[str] = set()
    top_ideas: list[Node] = []
    for n in idea_nodes:
        key = n.title[:80]
        if key not in seen_ideas_top and len(top_ideas) < 20:
            seen_ideas_top.add(key)
            top_ideas.append(n)

    ideas_top_parts = _cabecera(
        "ideas-relevantes", None, project_name, fecha_actual,
        ["context-map", "ideas", "relevantes"],
        "# 2.4 Ideas Relevantes",
    )
    ideas_top_parts.extend([
        "Las ideas más importantes y transversales del proyecto.",
        "",
        "---",
        "",
    ])
    if top_ideas:
        for n in top_ideas:
            status_icon = {"completado": "✅", "pendiente": "⏳", "activo": "🔄"}.get(n.status, "💡")
            ideas_top_parts.append(f"- {status_icon} **{n.title}** ({n.status})")
            if n.summary:
                ideas_top_parts.append(f"  - {n.summary}")
        ideas_top_parts.append("")
    else:
        ideas_top_parts.append("_(No se registraron ideas)_")
        ideas_top_parts.append("")

    ideas_top_parts.extend(_pie("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]"))
    _escribir_markdown(ideas_dir, "2.4-Ideas-Relevantes.md", ideas_top_parts)


def _render_seccion_estructura(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 3.0-ESTRUCTURA (3.0, 3.1).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    estructura_dir = os.path.join(output_dir, "3.0-ESTRUCTURA")
    os.makedirs(estructura_dir, exist_ok=True)

    partes = _cabecera(
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

    fund_parts = _cabecera(
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

    fund_parts.extend(_pie("[[3.0-ESTRUCTURA/3.0-ESTRUCTURA|⬅ Volver a 3.0 Estructura]]"))
    _escribir_markdown(estructura_dir, "3.1-Fundamentos.md", fund_parts)


def _render_seccion_riesgos(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 4.0-RIESGOS (4.0 + notas atómicas de riesgo).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    riesgos_dir = os.path.join(output_dir, "4.0-RIESGOS")
    os.makedirs(riesgos_dir, exist_ok=True)

    partes = _cabecera(
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

    partes.extend(_pie("[[00-INDICE|⬅ Volver al índice]]"))
    _escribir_markdown(riesgos_dir, "4.0-RIESGOS.md", partes)

    if clasificados["RIESGO"]:
        seen_riesgo_file: set[str] = set()
        for n in clasificados["RIESGO"]:
            key_file = n.title[:80]
            if key_file in seen_riesgo_file:
                continue
            seen_riesgo_file.add(key_file)
            _render_nota_riesgo(n, project_name, fecha_actual, riesgos_dir)


def _render_seccion_backlog(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 5.0-BACKLOG (5.0, 5.1).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    backlog_dir = os.path.join(output_dir, "5.0-BACKLOG")
    os.makedirs(backlog_dir, exist_ok=True)

    partes = _cabecera(
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

    tareas_parts = _cabecera(
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

    tareas_parts.extend(_pie("[[5.0-BACKLOG/5.0-BACKLOG|⬅ Volver a 5.0 Backlog]]"))
    _escribir_markdown(backlog_dir, "5.1-Tareas.md", tareas_parts)


def _render_seccion_historial(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza la sección 6.0-HISTORIAL (6.0, 6.1, 6.2, 6.3).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    historial_dir = os.path.join(output_dir, "6.0-HISTORIAL")
    os.makedirs(historial_dir, exist_ok=True)

    cambio_only = [n for n in clasificados["CAMBIO"] if n.type == "CAMBIO"]
    correccion_only = [n for n in clasificados["CAMBIO"] if n.type == "CORRECCION"]

    partes = _cabecera(
        "seccion", "historial", project_name, fecha_actual,
        ["context-map", "historial"],
        f"# 6.0 Historial — {project_name}",
    )
    partes.extend([
        "Registro de cambios, correcciones y decisiones arquitectónicas del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        f"- [[6.1-Cambios|6.1 Cambios]] ({len(cambio_only)} registros)",
        f"- [[6.2-Correcciones|6.2 Correcciones]] ({len(correccion_only)} registros)",
        "- [[6.3-Versiones|6.3 Versiones / Changelog]]",
        "",
    ])
    if clasificados["HITO"]:
        partes.append("## 🎯 Hitos")
        partes.append("")
        for n in clasificados["HITO"]:
            partes.append(f"- 🎯 **{n.title}**: {n.summary or 'Hito alcanzado'}")
        partes.append("")
        partes.append("---")
        partes.append("")

    partes.extend(_pie("[[00-INDICE|⬅ Volver al índice]]"))
    _escribir_markdown(historial_dir, "6.0-HISTORIAL.md", partes)

    cambios_parts = _cabecera(
        "cambios", None, project_name, fecha_actual,
        ["context-map", "cambios"],
        "# 6.1 Cambios",
    )
    cambios_parts.extend([
        "Registro de cambios realizados en el proyecto.",
        "",
        "---",
        "",
    ])
    if cambio_only:
        from context_map.core.generators import generar_contexto_narrativo
        for n in cambio_only:
            cambios_parts.append(f"## 🔄 {n.title} ({n.created_at or 'Fecha no esp.'})")
            cambios_parts.append("")
            if n.summary and n.summary != n.title:
                cambios_parts.append(n.summary)
                cambios_parts.append("")
            cambios_parts.append(generar_contexto_narrativo(n))
            cambios_parts.append("")
    else:
        cambios_parts.append("_(No se registraron cambios)_")
        cambios_parts.append("")

    cambios_parts.extend(_pie("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.1-Cambios.md", cambios_parts)

    correcciones_parts = _cabecera(
        "correcciones", None, project_name, fecha_actual,
        ["context-map", "correcciones"],
        "# 6.2 Correcciones",
    )
    correcciones_parts.extend([
        "Registro de correcciones aplicadas al proyecto.",
        "",
        "---",
        "",
    ])
    if correccion_only:
        from context_map.core.generators import generar_contexto_narrativo
        for n in correccion_only:
            correcciones_parts.append(f"## 🔧 {n.title} ({n.created_at or 'Fecha no esp.'})")
            correcciones_parts.append("")
            if n.summary and n.summary != n.title:
                correcciones_parts.append(n.summary)
                correcciones_parts.append("")
            correcciones_parts.append(generar_contexto_narrativo(n))
            correcciones_parts.append("")
    else:
        correcciones_parts.append("_(No se registraron correcciones)_")
        correcciones_parts.append("")

    correcciones_parts.extend(_pie("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.2-Correcciones.md", correcciones_parts)

    _render_versiones(project_name, fecha_actual, historial_dir)


def _render_versiones(project_name: str, fecha_actual: str, historial_dir: str) -> None:
    """Renderiza 6.3-Versiones.md con el changelog obtenido desde git.

    Args:
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        historial_dir (str): Directorio de la sección de historial.
    """
    partes = _cabecera(
        "versiones", None, project_name, fecha_actual,
        ["context-map", "versiones", "changelog"],
        "# 6.3 Versiones",
    )
    partes.extend([
        "Registro de versiones del proyecto, generado a partir del historial git.",
        "",
    ])

    project_root = os.getcwd()
    try:
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, cwd=project_root,
            timeout=10
        )
        all_tags_list = [t.strip() for t in result.stdout.split("\n")
                         if t.strip() and "desktop.ini" not in t]

        if all_tags_list:
            partes.append("## Versiones publicadas")
            partes.append("")

            prev_tag = None
            for tag in all_tags_list:
                date_result = subprocess.run(
                    ["git", "log", "-1", "--format=%ai", tag],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_date = date_result.stdout.strip()[:10] if date_result.stdout.strip() else "?"

                msg_result = subprocess.run(
                    ["git", "tag", "-l", tag, "--format=%(contents)"],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_msg = msg_result.stdout.strip()

                if prev_tag:
                    log_result = subprocess.run(
                        ["git", "log", "--oneline", f"{tag}..{prev_tag}"],
                        capture_output=True, text=True, cwd=project_root,
                        timeout=10
                    )
                else:
                    log_result = subprocess.run(
                        ["git", "log", "--oneline", tag],
                        capture_output=True, text=True, cwd=project_root,
                        timeout=10
                    )

                commits = log_result.stdout.strip()
                commit_lines = [c for c in commits.split("\n") if c.strip()]
                commit_count = len(commit_lines)

                partes.append(f"### {tag} ({tag_date})")
                partes.append("")
                if tag_msg:
                    partes.append(tag_msg)
                    partes.append("")
                if commit_lines:
                    partes.append(f"**{commit_count} commits** desde la versión anterior:")
                    partes.append("")
                    for c in commit_lines[:20]:
                        partes.append(f"- `{c}`")
                    if commit_count > 20:
                        partes.append(f"- ... y {commit_count - 20} commits más")
                    partes.append("")

                prev_tag = tag
        else:
            partes.append("## Historial por Meses")
            partes.append("")

            log_result = subprocess.run(
                ["git", "log", "--oneline", "--format=%ai | %s"],
                capture_output=True, text=True, cwd=project_root,
                timeout=10
            )
            all_commits = log_result.stdout.strip().split("\n")

            meses: dict[str, list[str]] = defaultdict(list)
            for line in all_commits:
                if " | " in line:
                    date_part, msg = line.split(" | ", 1)
                    month_key = date_part[:7]
                    meses[month_key].append(msg)

            for mes in sorted(meses.keys(), reverse=True):
                items = meses[mes]
                partes.append(f"### {mes} ({len(items)} commits)")
                partes.append("")
                for msg in items[:15]:
                    partes.append(f"- {msg}")
                if len(items) > 15:
                    partes.append(f"- ... y {len(items) - 15} commits más")
                partes.append("")

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as err:
        logger.warning("No se pudo obtener el historial de versiones: %s", err)
        partes.append("_(No se pudo obtener el historial de versiones)_")
        partes.append("")

    partes.extend(_pie("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]"))
    _escribir_markdown(historial_dir, "6.3-Versiones.md", partes)


def _render_indice_hierarchico(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 00-INDICE.md del modo jerárquico enlazando a las 6 secciones raíz.

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista de aristas/relaciones.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    all_tags: set[str] = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])

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
        f"# 🗺️ Indice MOC — {project_name}",
        "",
        "> Mapa jerárquico del proyecto. Navegá por secciones temáticas para explorar cada aspecto del contexto.",
        "",
        "---",
        "",
        "## 📊 Métricas",
        "",
        f"- 📦 Nodos Totales: **{len(nodes)}**",
        f"- 🧱 BASE: **{len(clasificados['BASE'])}**",
        f"- 💡 IDEA: **{len(clasificados['IDEA'])}**",
        f"- ⚠️ RIESGO: **{len(clasificados['RIESGO'])}**",
        f"- 🔄 CAMBIO/CORRECCION: **{len(clasificados['CAMBIO'])}**",
        f"- 🔮 FUTURO: **{len(clasificados['FUTURO'])}**",
        f"- 🎯 HITO: **{len(clasificados['HITO'])}**",
        f"- 🔗 Conexiones: **{len(edges)}**",
        "",
        "---",
        "",
        "## 📂 Secciones",
        "",
        "- [[1.0-PROPOSITO/1.0-PROPOSITO|1.0 Propósito]]",
        "- [[2.0-IDEAS/2.0-IDEAS|2.0 Ideas]]",
        "- [[3.0-ESTRUCTURA/3.0-ESTRUCTURA|3.0 Estructura]]",
        "- [[4.0-RIESGOS/4.0-RIESGOS|4.0 Riesgos]]",
        "- [[5.0-BACKLOG/5.0-BACKLOG|5.0 Backlog]]",
        "- [[6.0-HISTORIAL/6.0-HISTORIAL|6.0 Historial]]",
        "",
        "---",
        "",
        "## 🏷️ Tags Principales",
        "",
    ]
    partes.append(tags_badges or "`#context-map`")
    partes.append("")

    _escribir_markdown(output_dir, "00-INDICE.md", partes)


def _render_hierarchical_vault(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo jerárquico en árbol."""
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    clasificados = _clasificar_nodos(nodes)

    _render_indice_hierarchico(project_name, nodes, edges, clasificados, fecha_actual, output_dir)
    _render_seccion_proposito(project_name, nodes, edges, clasificados, fecha_actual, output_dir)
    _render_seccion_ideas(project_name, clasificados, fecha_actual, output_dir)
    _render_seccion_estructura(project_name, clasificados, fecha_actual, output_dir)
    _render_seccion_riesgos(project_name, clasificados, fecha_actual, output_dir)
    _render_seccion_backlog(project_name, clasificados, fecha_actual, output_dir)
    _render_seccion_historial(project_name, clasificados, fecha_actual, output_dir)
    _render_grafo_conexiones(output_dir, nodes, edges)

    return output_dir

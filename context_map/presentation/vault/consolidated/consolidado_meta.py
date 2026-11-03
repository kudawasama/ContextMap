"""Notas consolidadas de contexto del proyecto: índice MOC, propósito y estructura.

Son las tres notas que describen **qué es** el proyecto: el índice que enlaza
todo, el propósito extraído del README y los componentes base del grafo.
"""

from __future__ import annotations

import os

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.consolidado_base import (
    SECCIONES_MOC,
    _cabecera_nota,
    _pie_nota,
)
from context_map.presentation.vault.consolidated.escritura import _escribir_markdown
from context_map.presentation.vault.consolidated.nodos import _mencion_nodo_en_lista
from context_map.presentation.vault.consolidated.readme_extract import _extract_project_purpose


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

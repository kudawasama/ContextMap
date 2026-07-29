"""Renderizado de vaults consolidados y jerárquicos.

Este módulo implementa la generación de la estructura temática consolidada
y jerárquica del vault de Obsidian para consumo óptimo por agentes de IA.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict

from context_map.core.models import Node, Edge
from context_map.presentation.vault.templates import _safe_filename, _normalize_tags
from context_map.presentation.vault.atomic import _render_conexiones


def _extract_project_purpose(cwd: str) -> str:
    """Extrae el propósito del proyecto desde README.md si existe.

    Busca README.md en cwd, extrae el primer párrafo después del título,
    saltando badges, TOC y líneas vacías.

    Returns:
        String con el párrafo extraído, o string vacío si no existe.
    """
    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""

    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return ""

    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("#!"):
            title_idx = i
            break

    if title_idx is None:
        return ""

    start_idx = title_idx + 1
    paragraphs: List[str] = []
    current_para: List[str] = []

    for line in lines[start_idx:]:
        stripped = line.strip()

        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("[!["):
            continue

        if stripped.startswith("- [") or stripped.startswith("* ["):
            continue

        if stripped.startswith("<!--"):
            continue

        if stripped.startswith("---") or stripped.startswith("___") or stripped.startswith("***"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("#"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            break

        current_para.append(stripped)

    if current_para:
        paragraphs.append(" ".join(current_para))

    return paragraphs[0] if paragraphs else ""


def _render_consolidated_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo consolidado (8 notas temáticas sintéticas)."""
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    base_nodes = [n for n in nodes if n.type == "BASE"]
    idea_nodes = [n for n in nodes if n.type == "IDEA"]
    riesgo_nodes = [n for n in nodes if n.type == "RIESGO"]
    cambio_nodes = [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")]
    prueba_nodes = [n for n in nodes if n.type == "PRUEBA"]
    futuro_nodes = [n for n in nodes if n.type == "FUTURO"]
    hito_nodes = [n for n in nodes if n.type == "HITO"]

    proposito_texto = _extract_project_purpose(os.getcwd())

    # 1. 00-INDICE.md
    indice_parts = [
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
        f"- 🧱 Estructura (BASE): **{len(base_nodes)}**",
        f"- 💡 Ideas (IDEA): **{len(idea_nodes)}**",
        f"- ⚠️ Riesgos (RIESGO): **{len(riesgo_nodes)}**",
        f"- 🔮 Tareas (FUTURO): **{len(futuro_nodes)}**",
        f"- 🔄 Cambios (CAMBIO/CORRECCION): **{len(cambio_nodes)}**",
        f"- 🎯 Hitos (HITO): **{len(hito_nodes)}**",
        f"- 🧪 Pruebas (PRUEBA): **{len(prueba_nodes)}**",
        "",
        "---",
        "",
        "## 📂 Secciones Consolidadas",
        "",
        "- [[01-PROPOSITO|01. Propósito del Proyecto]]",
        "- [[02-IDEAS|02. Ideas y Características]]",
        "- [[03-ESTRUCTURA|03. Estructura del Proyecto]]",
        "- [[04-RIESGOS_Y_COMPLEJIDAD|04. Riesgos y Complejidad]]",
        "- [[05-BACKLOG_Y_TODOS|05. Backlog y Tareas Pendientes]]",
        "- [[06-HISTORIAL_Y_DECISIONES|06. Historial y Decisiones]]",
        "- [[00-CONEXIONES|07. Grafo Completo de Conexiones]]",
        "",
        "---",
        "",
        "## 🏷️ Tags Principales",
        "",
    ]
    all_tags = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])
    indice_parts.append(tags_badges or "`#context-map`")
    indice_parts.append("")

    with open(os.path.join(output_dir, "00-INDICE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(indice_parts))

    # 2. 01-PROPOSITO.md
    proposito_parts = [
        "---",
        "type: proposito",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, proposito, proyecto]",
        "---",
        "",
        f"# 🎯 Propósito del Proyecto — {project_name}",
        "",
    ]
    if proposito_texto:
        proposito_parts.extend([
            "> " + proposito_texto,
            "",
        ])

    proposito_parts.append("## 📋 Datos Clave")
    proposito_parts.append("")
    identidad_nodes = [n for n in base_nodes if any(
        kw in (n.title + " " + (n.summary or "")).lower()
        for kw in ["proyecto", "identidad", "readme", "package", "setup", "entry"]
    )]
    if identidad_nodes:
        seen_kw = set()
        for n in identidad_nodes:
            key = n.title[:80]
            if key in seen_kw:
                continue
            seen_kw.add(key)
            proposito_parts.append(f"- **{n.title}**: {n.summary or '(sin descripcion)'}")
    else:
        proposito_parts.append("_(No se encontraron nodos de identidad del proyecto)_")
    proposito_parts.append("")
    proposito_parts.append("---")
    proposito_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    proposito_parts.append("")

    with open(os.path.join(output_dir, "01-PROPOSITO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(proposito_parts))

    # 3. 02-IDEAS.md
    ideas_parts = [
        "---",
        "type: ideas",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, ideas, caracteristicas]",
        "---",
        "",
        f"# 💡 Ideas y Características — {project_name}",
        "",
        "Listado de ideas, features y conceptos registrados en el proyecto.",
        "",
        "---",
        "",
    ]
    if idea_nodes:
        completadas = [n for n in idea_nodes if n.status == "completado"]
        pendientes = [n for n in idea_nodes if n.status == "pendiente"]
        activas = [n for n in idea_nodes if n.status == "activo"]

        seen_total: Set[str] = set()

        def _render_idea_group(parts: List[str], title: str, icon: str, nodes_list: List[Node], emoji_prefix: str) -> None:
            if not nodes_list:
                return
            parts.append(f"## {icon} {title}")
            parts.append("")
            seen: Set[str] = set()
            for n in nodes_list:
                key = n.title[:80]
                if key in seen:
                    continue
                seen.add(key)
                seen_total.add(key)
                if n.source == "git":
                    parts.append(f"### {emoji_prefix} {n.title}")
                else:
                    parts.append(f"### 📝 {n.title}")
                if n.summary and n.summary != n.title:
                    parts.append(f"{n.summary}")
                parts.append("")

        _render_idea_group(ideas_parts, "Completadas", "✅", completadas, "🔧")
        _render_idea_group(ideas_parts, "Pendientes", "⏳", pendientes, "📋")
        _render_idea_group(ideas_parts, "Activas", "🔄", activas, "⚡")

        if not seen_total:
            ideas_parts.append("_(No se registraron ideas o características)_")
            ideas_parts.append("")
    else:
        ideas_parts.append("_(No se registraron ideas o características)_")
        ideas_parts.append("")

    ideas_parts.append("---")
    ideas_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    ideas_parts.append("")

    with open(os.path.join(output_dir, "02-IDEAS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ideas_parts))

    # 4. 03-ESTRUCTURA.md
    est_parts = [
        "---",
        "type: estructura",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, estructura]",
        "---",
        "",
        f"# 🧱 Estructura del Proyecto — {project_name}",
        "",
        "Componentes base, entrypoints, documentación e identidad del proyecto.",
        "",
        "---",
        "",
    ]
    if base_nodes:
        seen_base: Set[str] = set()
        for n in base_nodes:
            key = n.title[:80]
            if key in seen_base:
                continue
            seen_base.add(key)
            est_parts.append(f"- **{n.title}**")
            if n.summary:
                est_parts.append(f"  - {n.summary}")
            if n.source:
                est_parts.append(f"  - *Origen*: `{n.source}`")
            est_parts.append("")
    else:
        est_parts.append("_(No se registraron componentes base)_")
        est_parts.append("")

    est_parts.append("---")
    est_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    est_parts.append("")

    with open(os.path.join(output_dir, "03-ESTRUCTURA.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(est_parts))

    # 5. 04-RIESGOS_Y_COMPLEJIDAD.md
    riesgo_parts = [
        "---",
        "type: riesgos",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, riesgo, complejidad]",
        "---",
        "",
        f"# ⚠️ Riesgos y Complejidad — {project_name}",
        "",
        "Identificación de puntos de alta complejidad, alertas de mantenimiento y cobertura de pruebas.",
        "",
        "---",
        "",
        "## 🚨 Alertas de Riesgo y Alta Complejidad",
        "",
    ]
    if riesgo_nodes:
        seen_riesgo: Set[str] = set()
        for n in riesgo_nodes:
            key = n.title[:80]
            if key in seen_riesgo:
                continue
            seen_riesgo.add(key)
            riesgo_parts.append(f"### ⚠️ {n.title}")
            riesgo_parts.append(f"{n.summary or 'Punto de atención técnica'}")
            if n.evidence:
                riesgo_parts.append("- **Evidencia**:")
                for ev in n.evidence:
                    riesgo_parts.append(f"  - {ev}")
            riesgo_parts.append("")
    else:
        riesgo_parts.append("✅ **Sin riesgos o alertas críticas detectadas.**")
        riesgo_parts.append("")

    if prueba_nodes:
        riesgo_parts.append("## 🧪 Cobertura de Pruebas Detectadas")
        riesgo_parts.append("")
        seen_prueba: Set[str] = set()
        for n in prueba_nodes:
            key = n.title[:80]
            if key in seen_prueba:
                continue
            seen_prueba.add(key)
            riesgo_parts.append(f"- **{n.title}**: {n.summary or 'Test'}")
        riesgo_parts.append("")

    riesgo_parts.append("---")
    riesgo_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    riesgo_parts.append("")

    with open(os.path.join(output_dir, "04-RIESGOS_Y_COMPLEJIDAD.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(riesgo_parts))

    # 6. 05-BACKLOG_Y_TODOS.md
    backlog_parts = [
        "---",
        "type: backlog",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, backlog, todos]",
        "---",
        "",
        f"# 🔮 Backlog y Tareas Pendientes — {project_name}",
        "",
        "Listado consolidado de tareas futuras, TODOs e iniciativas registradas en el proyecto.",
        "",
        "---",
        "",
        "## 📋 Checklists de Tareas (TODOs / FUTURO)",
        "",
    ]
    if futuro_nodes:
        seen_futuro: Set[str] = set()
        for n in futuro_nodes:
            key = n.title[:80]
            if key in seen_futuro:
                continue
            seen_futuro.add(key)
            estado_mark = "[x]" if n.status == "completado" else "[ ]"
            backlog_parts.append(f"- {estado_mark} **{n.title}**")
            if n.summary:
                backlog_parts.append(f"  - _{n.summary}_")
    else:
        backlog_parts.append("- [x] No hay tareas pendientes en el backlog actual.")

    backlog_parts.append("")
    backlog_parts.append("---")
    backlog_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    backlog_parts.append("")

    with open(os.path.join(output_dir, "05-BACKLOG_Y_TODOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(backlog_parts))

    # 7. 06-HISTORIAL_Y_DECISIONES.md
    historial_parts = [
        "---",
        "type: historial",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, historial, cambios]",
        "---",
        "",
        f"# 🔄 Historial y Decisiones — {project_name}",
        "",
        "Registro consolidado de cambios, correcciones y decisiones arquitectónicas.",
        "",
        "---",
        "",
        "## 🎯 Hitos",
        "",
    ]
    if hito_nodes:
        for n in hito_nodes:
            historial_parts.append(f"- 🎯 **{n.title}**: {n.summary or 'Hito alcanzado'}")
        historial_parts.append("")
    else:
        historial_parts.append("_(Sin hitos registrados)_")
        historial_parts.append("")

    historial_parts.append("## 🔄 Registro de Cambios y Correcciones")
    historial_parts.append("")
    if cambio_nodes:
        seen_cambio: Set[str] = set()
        for n in cambio_nodes[:50]:
            key = n.title[:80]
            if key in seen_cambio:
                continue
            seen_cambio.add(key)
            icon = "🔧" if n.type == "CORRECCION" else "🔄"
            historial_parts.append(f"- {icon} **{n.title}** ({n.created_at or 'Fecha no esp.'})")
            if n.summary and n.summary != n.title:
                historial_parts.append(f"  - {n.summary}")
        historial_parts.append("")
    else:
        historial_parts.append("_(Sin registros de cambios)_")
        historial_parts.append("")

    historial_parts.append("---")
    historial_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    historial_parts.append("")

    with open(os.path.join(output_dir, "06-HISTORIAL_Y_DECISIONES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(historial_parts))

    _render_conexiones(output_dir, nodes, edges)

    return output_dir


def _render_hierarchical_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo jerárquico en árbol."""
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    base_nodes = [n for n in nodes if n.type == "BASE"]
    idea_nodes = [n for n in nodes if n.type == "IDEA"]
    riesgo_nodes = [n for n in nodes if n.type == "RIESGO"]
    cambio_nodes = [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")]
    futuro_nodes = [n for n in nodes if n.type == "FUTURO"]
    hito_nodes = [n for n in nodes if n.type == "HITO"]

    proposito_texto = _extract_project_purpose(os.getcwd())

    all_tags = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])

    # 00-INDICE.md
    indice_parts = [
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
        f"- 🧱 BASE: **{len(base_nodes)}**",
        f"- 💡 IDEA: **{len(idea_nodes)}**",
        f"- ⚠️ RIESGO: **{len(riesgo_nodes)}**",
        f"- 🔄 CAMBIO/CORRECCION: **{len(cambio_nodes)}**",
        f"- 🔮 FUTURO: **{len(futuro_nodes)}**",
        f"- 🎯 HITO: **{len(hito_nodes)}**",
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
    indice_parts.append(tags_badges or "`#context-map`")
    indice_parts.append("")

    with open(os.path.join(output_dir, "00-INDICE.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(indice_parts))

    # 1.0-PROPOSITO/
    proposito_dir = os.path.join(output_dir, "1.0-PROPOSITO")
    os.makedirs(proposito_dir, exist_ok=True)

    proposito_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: proposito",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, proposito]",
        "---",
        "",
        f"# 1.0 Propósito — {project_name}",
        "",
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
    ]

    with open(os.path.join(proposito_dir, "1.0-PROPOSITO.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(proposito_seccion_parts))

    readme_content = ""
    readme_path = os.path.join(os.getcwd(), "README.md")
    if os.path.exists(readme_path):
        try:
            with open(readme_path, "r", encoding="utf-8") as rf:
                readme_content = rf.read().strip()
        except Exception:
            readme_content = ""

    narrativa_parts = [
        "---",
        "type: narrativa",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, narrativa, mapa-mental]",
        "---",
        "",
        "# 1.1 Mapa Mental Narrativo",
        "",
    ]
    if proposito_texto:
        narrativa_parts.extend([
            "> " + proposito_texto,
            "",
        ])

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

    narrativa_parts.extend([
        "---",
        "[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]",
        "",
    ])

    with open(os.path.join(proposito_dir, "1.1-Mapa-Mental-Narrativo.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(narrativa_parts))

    # 1.2-Datos-Clave.md
    datos_clave_parts = [
        "---",
        "type: datos-clave",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, datos-clave, metricas]",
        "---",
        "",
        "# 1.2 Datos Clave",
        "",
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
        f"| Componentes BASE | {len(base_nodes)} |",
        f"| Ideas registradas | {len(idea_nodes)} |",
        f"| Riesgos identificados | {len(riesgo_nodes)} |",
        f"| Tareas FUTURO | {len(futuro_nodes)} |",
        f"| Cambios y Correcciones | {len(cambio_nodes)} |",
        f"| Hitos | {len(hito_nodes)} |",
        "",
    ]
    metric_nodes = [n for n in base_nodes if any(
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

    datos_clave_parts.append("---")
    datos_clave_parts.append("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]")
    datos_clave_parts.append("")

    with open(os.path.join(proposito_dir, "1.2-Datos-Clave.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(datos_clave_parts))

    # 1.3-Proposito.md
    identidad_parts = [
        "---",
        "type: identidad",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, identidad, proposito]",
        "---",
        "",
        "# 1.3 Propósito",
        "",
        "Identidad y configuración fundamental del proyecto.",
        "",
        "---",
        "",
    ]
    identidad_nodes = [n for n in base_nodes if any(
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

    identidad_parts.append("---")
    identidad_parts.append("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]")
    identidad_parts.append("")

    with open(os.path.join(proposito_dir, "1.3-Proposito.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(identidad_parts))

    # 2.0-IDEAS/
    ideas_dir = os.path.join(output_dir, "2.0-IDEAS")
    os.makedirs(ideas_dir, exist_ok=True)
    completadas = [n for n in idea_nodes if n.status == "completado"]
    pendientes = [n for n in idea_nodes if n.status == "pendiente"]
    activas = [n for n in idea_nodes if n.status == "activo"]

    ideas_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: ideas",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, ideas]",
        "---",
        "",
        f"# 2.0 Ideas — {project_name}",
        "",
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
    ]

    with open(os.path.join(ideas_dir, "2.0-IDEAS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ideas_seccion_parts))

    # 2.1-Ideas-Pendientes/
    if pendientes:
        pendientes_dir = os.path.join(ideas_dir, "2.1-Ideas-Pendientes")
        os.makedirs(pendientes_dir, exist_ok=True)

        pend_index_parts = [
            "---",
            "type: seccion",
            "subtype: ideas-pendientes",
            f"created: {fecha_actual}",
            f'project: "{project_name}"',
            "tags: [context-map, ideas, pendientes]",
            "---",
            "",
            f"# 2.1 Ideas Pendientes — {project_name}",
            "",
            f"Ideas pendientes por implementar: **{len(pendientes)}**",
            "",
            "---",
            "",
            "## Lista de Ideas Pendientes",
            "",
        ]
        for n in pendientes:
            slug = _safe_filename(n.title)
            pend_index_parts.append(f"- [[{slug}|⏳ {n.title}]]")
        pend_index_parts.extend([
            "",
            "---",
            "[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]",
            "",
        ])
        with open(os.path.join(pendientes_dir, "2.1-Ideas-Pendientes.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(pend_index_parts))

        for n in pendientes:
            filename = _safe_filename(n.title) + ".md"
            tags_list = _normalize_tags(n.tags, n.type)
            tags_str = ", ".join(f'"{t}"' for t in tags_list)
            parts = [
                "---",
                "type: idea",
                "status: pendiente",
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
                parts.append(n.summary)
                parts.append("")

            from context_map.core.generators import generar_contexto_narrativo
            parts.append("## 🧠 Contexto Narrativo con Alma")
            parts.append("")
            parts.append(generar_contexto_narrativo(n))
            parts.append("")
            if n.evidence:
                parts.append("## 📋 Evidencia")
                parts.append("")
                for ev in n.evidence:
                    parts.append(f"- {ev}")
                parts.append("")
            parts.append("---")
            parts.append("[[2.1-Ideas-Pendientes/2.1-Ideas-Pendientes|⬅ Volver a 2.1 Ideas Pendientes]]")
            parts.append("")

            with open(os.path.join(pendientes_dir, filename), "w", encoding="utf-8") as f:
                f.write("\n".join(parts))

    # 2.2-Ideas-Futuras/
    if activas:
        futuras_dir = os.path.join(ideas_dir, "2.2-Ideas-Futuras")
        os.makedirs(futuras_dir, exist_ok=True)

        futuras_index_parts = [
            "---",
            "type: seccion",
            "subtype: ideas-futuras",
            f"created: {fecha_actual}",
            f'project: "{project_name}"',
            "tags: [context-map, ideas, futuras]",
            "---",
            "",
            f"# 2.2 Ideas Futuras — {project_name}",
            "",
            f"Ideas futuras registradas: **{len(activas)}**",
            "",
            "---",
            "",
            "## Lista de Ideas Futuras",
            "",
        ]
        for n in activas:
            slug = _safe_filename(n.title)
            futuras_index_parts.append(f"- [[{slug}|🔮 {n.title}]]")
        futuras_index_parts.extend([
            "",
            "---",
            "[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]",
            "",
        ])
        with open(os.path.join(futuras_dir, "2.2-Ideas-Futuras.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(futuras_index_parts))

        for n in activas:
            filename = _safe_filename(n.title) + ".md"
            tags_list = _normalize_tags(n.tags, n.type)
            tags_str = ", ".join(f'"{t}"' for t in tags_list)
            parts = [
                "---",
                "type: idea",
                "status: activo",
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
                parts.append(n.summary)
                parts.append("")

            from context_map.core.generators import generar_contexto_narrativo
            parts.append("## 🧠 Contexto Narrativo con Alma")
            parts.append("")
            parts.append(generar_contexto_narrativo(n))
            parts.append("")
            if n.evidence:
                parts.append("## 📋 Evidencia")
                parts.append("")
                for ev in n.evidence:
                    parts.append(f"- {ev}")
                parts.append("")
            parts.append("---")
            parts.append("[[2.2-Ideas-Futuras/2.2-Ideas-Futuras|⬅ Volver a 2.2 Ideas Futuras]]")
            parts.append("")

            with open(os.path.join(futuras_dir, filename), "w", encoding="utf-8") as f:
                f.write("\n".join(parts))

    # 2.3-Ideas-Completas-e-Implementadas/
    if completadas:
        completadas_dir = os.path.join(ideas_dir, "2.3-Ideas-Completas-e-Implementadas")
        os.makedirs(completadas_dir, exist_ok=True)

        completas_index_parts = [
            "---",
            "type: seccion",
            "subtype: ideas-completas",
            f"created: {fecha_actual}",
            f'project: "{project_name}"',
            "tags: [context-map, ideas, completadas]",
            "---",
            "",
            f"# 2.3 Ideas Completas e Implementadas — {project_name}",
            "",
            f"Ideas completadas acumuladas: **{len(completadas)}**",
            "",
            "---",
            "",
        ]
        with open(os.path.join(completadas_dir, "2.3-Ideas-Completas.md"), "w", encoding="utf-8") as f:
            f.write("\n".join(completas_index_parts))

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
            batch_parts.append("---")
            batch_parts.append("[[2.3-Ideas-Completas-e-Implementadas/2.3-Ideas-Completas|⬅ Volver a 2.3 Ideas Completas]]")
            batch_parts.append("")

            with open(os.path.join(completadas_dir, filename), "w", encoding="utf-8") as f:
                f.write("\n".join(batch_parts))

    # 2.4-Ideas-Relevantes.md
    top_ideas = idea_nodes[:20]

    ideas_top_parts = [
        "---",
        "type: ideas-relevantes",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, ideas, relevantes]",
        "---",
        "",
        "# 2.4 Ideas Relevantes",
        "",
        "Las ideas más importantes y transversales del proyecto.",
        "",
        "---",
        "",
    ]
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

    ideas_top_parts.append("---")
    ideas_top_parts.append("[[2.0-IDEAS/2.0-IDEAS|⬅ Volver a 2.0 Ideas]]")
    ideas_top_parts.append("")

    with open(os.path.join(ideas_dir, "2.4-Ideas-Relevantes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(ideas_top_parts))

    # 3.0-ESTRUCTURA/
    estructura_dir = os.path.join(output_dir, "3.0-ESTRUCTURA")
    os.makedirs(estructura_dir, exist_ok=True)

    est_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: estructura",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, estructura]",
        "---",
        "",
        f"# 3.0 Estructura — {project_name}",
        "",
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
    ]
    with open(os.path.join(estructura_dir, "3.0-ESTRUCTURA.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(est_seccion_parts))

    fund_parts = [
        "---",
        "type: fundamentos",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, fundamentos, estructura]",
        "---",
        "",
        "# 3.1 Fundamentos",
        "",
        "Componentes base del proyecto con sus descripciones y orígenes.",
        "",
        "---",
        "",
    ]
    if base_nodes:
        from context_map.core.generators import generar_contexto_narrativo
        seen_base: Set[str] = set()
        for n in base_nodes:
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

    fund_parts.append("---")
    fund_parts.append("[[3.0-ESTRUCTURA/3.0-ESTRUCTURA|⬅ Volver a 3.0 Estructura]]")
    fund_parts.append("")

    with open(os.path.join(estructura_dir, "3.1-Fundamentos.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(fund_parts))

    # 4.0-RIESGOS/
    riesgos_dir = os.path.join(output_dir, "4.0-RIESGOS")
    os.makedirs(riesgos_dir, exist_ok=True)

    riesgo_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: riesgos",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, riesgos]",
        "---",
        "",
        f"# 4.0 Riesgos — {project_name}",
        "",
        "Identificación de puntos de alta complejidad, alertas y riesgos del proyecto.",
        "",
        "---",
        "",
    ]
    if riesgo_nodes:
        riesgo_seccion_parts.append("## Riesgos Identificados")
        riesgo_seccion_parts.append("")
        for n in riesgo_nodes:
            slug = _safe_filename(n.title)
            riesgo_seccion_parts.append(f"- [[{slug}|⚠️ {n.title}]]")
        riesgo_seccion_parts.append("")
    else:
        riesgo_seccion_parts.append("✅ **Sin riesgos o alertas críticas detectadas.**")
        riesgo_seccion_parts.append("")

    riesgo_seccion_parts.append("---")
    riesgo_seccion_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    riesgo_seccion_parts.append("")

    with open(os.path.join(riesgos_dir, "4.0-RIESGOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(riesgo_seccion_parts))

    if riesgo_nodes:
        for n in riesgo_nodes:
            filename = _safe_filename(n.title) + ".md"
            tags_list = _normalize_tags(n.tags, n.type)
            tags_str = ", ".join(f'"{t}"' for t in tags_list)
            riesgo_item_parts = [
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
                riesgo_item_parts.append(n.summary)
                riesgo_item_parts.append("")

            from context_map.core.generators import generar_contexto_narrativo
            riesgo_item_parts.append("## 🧠 Contexto Narrativo con Alma")
            riesgo_item_parts.append("")
            riesgo_item_parts.append(generar_contexto_narrativo(n))
            riesgo_item_parts.append("")
            if n.evidence:
                riesgo_item_parts.append("## 📋 Evidencia")
                riesgo_item_parts.append("")
                for ev in n.evidence:
                    riesgo_item_parts.append(f"- {ev}")
                riesgo_item_parts.append("")
            riesgo_item_parts.append("---")
            riesgo_item_parts.append("[[4.0-RIESGOS/4.0-RIESGOS|⬅ Volver a 4.0 Riesgos]]")
            riesgo_item_parts.append("")

            with open(os.path.join(riesgos_dir, filename), "w", encoding="utf-8") as f:
                f.write("\n".join(riesgo_item_parts))

    # 5.0-BACKLOG/
    backlog_dir = os.path.join(output_dir, "5.0-BACKLOG")
    os.makedirs(backlog_dir, exist_ok=True)

    backlog_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: backlog",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, backlog]",
        "---",
        "",
        f"# 5.0 Backlog — {project_name}",
        "",
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
    ]
    with open(os.path.join(backlog_dir, "5.0-BACKLOG.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(backlog_seccion_parts))

    tareas_parts = [
        "---",
        "type: tareas",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, tareas, backlog]",
        "---",
        "",
        "# 5.1 Tareas",
        "",
        "Lista de tareas futuras y pendientes del proyecto.",
        "",
        "---",
        "",
    ]
    if futuro_nodes:
        from context_map.core.generators import generar_contexto_narrativo
        for n in futuro_nodes:
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

    tareas_parts.append("---")
    tareas_parts.append("[[5.0-BACKLOG/5.0-BACKLOG|⬅ Volver a 5.0 Backlog]]")
    tareas_parts.append("")

    with open(os.path.join(backlog_dir, "5.1-Tareas.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(tareas_parts))

    # 6.0-HISTORIAL/
    historial_dir = os.path.join(output_dir, "6.0-HISTORIAL")
    os.makedirs(historial_dir, exist_ok=True)

    cambio_only = [n for n in cambio_nodes if n.type == "CAMBIO"]
    correccion_only = [n for n in cambio_nodes if n.type == "CORRECCION"]

    historial_seccion_parts = [
        "---",
        "type: seccion",
        "subtype: historial",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, historial]",
        "---",
        "",
        f"# 6.0 Historial — {project_name}",
        "",
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
    ]
    if hito_nodes:
        historial_seccion_parts.append("## 🎯 Hitos")
        historial_seccion_parts.append("")
        for n in hito_nodes:
            historial_seccion_parts.append(f"- 🎯 **{n.title}**: {n.summary or 'Hito alcanzado'}")
        historial_seccion_parts.append("")
        historial_seccion_parts.append("---")
        historial_seccion_parts.append("")

    historial_seccion_parts.append("---")
    historial_seccion_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    historial_seccion_parts.append("")

    with open(os.path.join(historial_dir, "6.0-HISTORIAL.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(historial_seccion_parts))

    cambios_parts = [
        "---",
        "type: cambios",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, cambios]",
        "---",
        "",
        "# 6.1 Cambios",
        "",
        "Registro de cambios realizados en el proyecto.",
        "",
        "---",
        "",
    ]
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

    cambios_parts.append("---")
    cambios_parts.append("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]")
    cambios_parts.append("")

    with open(os.path.join(historial_dir, "6.1-Cambios.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(cambios_parts))

    correcciones_parts = [
        "---",
        "type: correcciones",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, correcciones]",
        "---",
        "",
        "# 6.2 Correcciones",
        "",
        "Registro de correcciones aplicadas al proyecto.",
        "",
        "---",
        "",
    ]
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

    correcciones_parts.append("---")
    correcciones_parts.append("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]")
    correcciones_parts.append("")

    with open(os.path.join(historial_dir, "6.2-Correcciones.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(correcciones_parts))

    versiones_parts = [
        "---",
        "type: versiones",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, versiones, changelog]",
        "---",
        "",
        "# 6.3 Versiones",
        "",
        "Registro de versiones del proyecto, generado a partir del historial git.",
        "",
    ]

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
            versiones_parts.append("## Versiones publicadas")
            versiones_parts.append("")

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

                versiones_parts.append(f"### {tag} ({tag_date})")
                versiones_parts.append("")
                if tag_msg:
                    versiones_parts.append(tag_msg)
                    versiones_parts.append("")
                if commit_lines:
                    versiones_parts.append(f"**{commit_count} commits** desde la versión anterior:")
                    versiones_parts.append("")
                    for c in commit_lines[:20]:
                        versiones_parts.append(f"- `{c}`")
                    if commit_count > 20:
                        versiones_parts.append(f"- ... y {commit_count - 20} commits más")
                    versiones_parts.append("")

                prev_tag = tag
        else:
            versiones_parts.append("## Historial por Meses")
            versiones_parts.append("")

            log_result = subprocess.run(
                ["git", "log", "--oneline", "--format=%ai | %s"],
                capture_output=True, text=True, cwd=project_root,
                timeout=10
            )
            all_commits = log_result.stdout.strip().split("\n")

            meses: Dict[str, List[str]] = defaultdict(list)
            for line in all_commits:
                if " | " in line:
                    date_part, msg = line.split(" | ", 1)
                    month_key = date_part[:7]
                    meses[month_key].append(msg)

            for mes in sorted(meses.keys(), reverse=True):
                items = meses[mes]
                versiones_parts.append(f"### {mes} ({len(items)} commits)")
                versiones_parts.append("")
                for msg in items[:15]:
                    versiones_parts.append(f"- {msg}")
                if len(items) > 15:
                    versiones_parts.append(f"- ... y {len(items) - 15} commits más")
                versiones_parts.append("")

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        versiones_parts.append("_(No se pudo obtener el historial de versiones)_")
        versiones_parts.append("")

    versiones_parts.append("---")
    versiones_parts.append("[[6.0-HISTORIAL/6.0-HISTORIAL|⬅ Volver a 6.0 Historial]]")
    versiones_parts.append("")

    with open(os.path.join(historial_dir, "6.3-Versiones.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(versiones_parts))

    _render_conexiones(output_dir, nodes, edges)

    return output_dir

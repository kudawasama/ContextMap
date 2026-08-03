"""Renderizado de la sección 1.0-PROPOSITO para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import logging
import os

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.common import (
    _escribir_markdown,
    _extract_project_purpose,
)

logger = logging.getLogger(__name__)


def _render_seccion_proposito(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 1.0-PROPOSITO (1.0, 1.1, 1.2, 1.3).

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista de aristas/relaciones.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Función generadora de cabeceras YAML.
        pie_fn (Callable): Función generadora de pies con wikilink.
    """
    proposito_dir = os.path.join(output_dir, "1.0-PROPOSITO")
    os.makedirs(proposito_dir, exist_ok=True)

    partes = cabecera_fn(
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

    narrativa_parts = cabecera_fn(
        "narrativa", None, project_name, fecha_actual,
        ["context-map", "narrativa", "mapa-mental"],
        "# 1.1 Mapa Mental Narrativo",
    )
    if proposito_texto:
        narrativa_parts.extend(["> " + proposito_texto, ""])

    from context_map.presentation.vault.mermaid import generar_diagrama_mermaid_global
    diagrama_mermaid = generar_diagrama_mermaid_global(nodes, edges)
    if diagrama_mermaid:
        narrativa_parts.extend([
            "## 📊 Diagrama de Arquitectura (Mermaid)",
            "",
            diagrama_mermaid,
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

    narrativa_parts.extend(pie_fn("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.1-Mapa-Mental-Narrativo.md", narrativa_parts)

    datos_clave_parts = cabecera_fn(
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

    datos_clave_parts.extend(pie_fn("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.2-Datos-Clave.md", datos_clave_parts)

    identidad_parts = cabecera_fn(
        "proposito", None, project_name, fecha_actual,
        ["context-map", "proposito", "identidad"],
        "# 1.3 Propósito del Proyecto",
    )
    identidad_parts.extend([
        "Propósito central e identidad del proyecto en el mapa conceptual.",
        "",
        "---",
        "",
        "## 🎯 Propósito del Dominio",
        "",
    ])
    if proposito_texto:
        identidad_parts.extend([proposito_texto, ""])
    else:
        identidad_parts.extend([
            f"El proyecto **{project_name}** facilita el desarrollo ágil y estructurado mediante trazabilidad de contexto.",
            "",
        ])

    identidad_parts.extend([
        "## 🏛️ Principios y Componentes Principales",
        "",
    ])
    identidad_nodes = [n for n in clasificados["BASE"] if any(
        kw in (n.title + " " + (n.summary or "")).lower()
        for kw in ["proyecto", "propósito", "arquitectura", "core", "dominio"]
    )]
    if identidad_nodes:
        for n in identidad_nodes:
            identidad_parts.append(f"- **{n.title}**: {n.summary or '(sin descripción)'}")
        identidad_parts.append("")
    else:
        identidad_parts.append("_(No se encontraron nodos de identidad del proyecto)_")
        identidad_parts.append("")

    identidad_parts.extend(pie_fn("[[1.0-PROPOSITO/1.0-PROPOSITO|⬅ Volver a 1.0 Propósito]]"))
    _escribir_markdown(proposito_dir, "1.3-Proposito.md", identidad_parts)

"""Renderizado atómico y consolidación legacy de notas individualizadas para el vault.

Provee funciones para generar notas atómicas individuales, MOC general,
carpetas de estado, consolidaciones de grupos y seguimiento de conexiones.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.templates import (
    STATUS_FOLDERS,
    TYPE_TO_FOLDER,
    _frontmatter,
    _slugificar,
    _wiki_links,
)


def _render_nota(node: Node, all_nodes: list[Node], edges: list[Edge]) -> str:
    """Renderiza una nota individual del vault Obsidian."""
    frontmatter = _frontmatter(node)
    links = _wiki_links(node, all_nodes, edges)

    # Icono por tipo
    iconos = {
        "BASE": "📦", "IDEA": "💡", "RIESGO": "⚠️", "CAMBIO": "🔄",
        "PRUEBA": "🧪", "FUTURO": "🔮", "HITO": "🎯", "CORRECCION": "🔧",
    }
    icono = iconos.get(node.type, "📝")

    # Badge de estado
    status_badges = {
        "completado": "✅ COMPLETADO",
        "en_progreso": "🔄 EN PROGRESO",
        "pendiente": "⏳ PENDIENTE",
        "cancelado": "❌ CANCELADO",
    }
    status_badge = status_badges.get(node.status, "")

    partes = [
        frontmatter,
        "",
        f"# {icono} {node.title}",
        "",
    ]

    if status_badge:
        partes.append(f"**Estado**: {status_badge}")
        partes.append("")

    if node.tags:
        tags_badges = " ".join(f"`#{t}`" for t in node.tags)
        partes.append(f"**Tags**: {tags_badges}")
        partes.append("")

    if node.source:
        partes.append(f"**Origen**: `{node.source}`")
        partes.append("")

    if node.summary and node.summary != node.title:
        partes.append("## 📝 Descripción")
        partes.append("")
        partes.append(node.summary)
        partes.append("")

    from context_map.core.generators import generar_contexto_narrativo
    partes.append("## 🧠 Contexto Narrativo con Alma")
    partes.append("")
    partes.append(generar_contexto_narrativo(node))
    partes.append("")

    from context_map.presentation.vault.mermaid import generar_diagrama_mermaid_nodo
    mermaid_diag = generar_diagrama_mermaid_nodo(node, all_nodes, edges)
    if mermaid_diag:
        partes.append("## 📊 Mapa de Conexiones (Mermaid)")
        partes.append("")
        partes.append(mermaid_diag)
        partes.append("")

    if links:
        partes.append("## 🔗 Conexiones")
        partes.append("")
        for link in links:
            partes.append(f"- {link}")
        partes.append("")

    partes.append("---")
    partes.append("")
    partes.append("[[00-INDICE|⬅ Volver al índice]]")
    partes.append("")

    if node.evidence:
        partes.append("## 📋 Evidencia")
        partes.append("")
        for ev in node.evidence:
            partes.append(f"- {ev}")
        partes.append("")

    return "\n".join(partes)


def _render_moc(project_name: str, nodes: list[Node], edges: list[Edge]) -> str:
    """Renderiza el Map of Content (índice principal) para modo atómico."""
    frontmatter = f"""---
type: moc
created: {datetime.now().isoformat(timespec="seconds")}
project: "{project_name}"
total_nodes: {len(nodes)}
total_edges: {len(edges)}
---"""

    por_tipo: dict[str, list[Node]] = {}
    for n in nodes:
        por_tipo.setdefault(n.type, []).append(n)

    iconos = {
        "BASE": "📦", "IDEA": "💡", "RIESGO": "⚠️", "CAMBIO": "🔄",
        "PRUEBA": "🧪", "FUTURO": "🔮", "HITO": "🎯", "CORRECCION": "🔧",
    }

    partes = [
        frontmatter,
        "",
        f"# 🗺️ {project_name}",
        "",
        "> Mapa central del proyecto. Desde acá podés navegar toda la documentación.",
        "",
        "---",
        "",
        "## 📊 Resumen",
        "",
    ]

    for tipo, items in sorted(por_tipo.items()):
        icono = iconos.get(tipo, "📝")
        partes.append(f"- {icono} **{tipo}**: {len(items)}")
    partes.append(f"- 🔗 Conexiones: {len(edges)}")
    partes.append("")
    partes.append("---")
    partes.append("")

    partes.append("## 📂 Secciones Principales")
    partes.append("")
    partes.append("- [[1.0-PROPOSITO/1.0-PROPOSITO|🎯 1.0 Propósito]]")
    partes.append("- [[2.0-IDEAS/2.0-IDEAS|💡 2.0 Ideas]]")
    partes.append("- [[3.0-ESTRUCTURA/3.0-ESTRUCTURA|📦 3.0 Estructura]]")
    partes.append("- [[4.0-RIESGOS/4.0-RIESGOS|⚠️ 4.0 Riesgos]]")
    partes.append("- [[5.0-BACKLOG/5.0-BACKLOG|🔮 5.0 Backlog]]")
    partes.append("- [[6.0-HISTORIAL/6.0-HISTORIAL|📜 6.0 Historial]]")
    partes.append("")

    return "\n".join(partes)


def _detectar_grupo(nodo: Node) -> str | None:
    """Detecta si un nodo pertenece a un grupo que puede consolidarse."""
    title_lower = nodo.title.lower()
    text = nodo.summary.lower() if nodo.summary else ""

    if "archivos de tipo" in title_lower or "archivos de tipo" in text:
        return "ESTRUCTURA"

    if "__init__" in title_lower:
        return "PAQUETES_PYTHON"

    if ".py" in title_lower:
        modulos_unicos = ["cli.py", "models.py", "parser.py"]
        if not any(m in title_lower for m in modulos_unicos):
            return "MODULOS_PYTHON"

    if "pendiente en" in title_lower and ("l" in title_lower and ":" in title_lower):
        return "TODOS_SCANNER"

    if re.match(r"[a-f0-9]{7}\s+feat:", title_lower):
        return "FEATURES"

    if re.match(r"[a-f0-9]{7}\s+docs?:", title_lower):
        return "DOCS"

    if re.match(r"[a-f0-9]{7}\s+chore:", title_lower):
        return "CHORES"

    if re.match(r"\[?[a-f0-9]{7}\]?", title_lower):
        return "COMMITS"

    return None


def _consolidar_grupo(nombre: str, nodos: list[Node], proyecto: str = "") -> Node | None:
    """Consolida un grupo de nodos relacionados en uno solo."""
    if not nodos:
        return None

    base = nodos[0]
    tag_counts: dict[str, int] = {}
    for n in nodos:
        for t in n.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    tags_top = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    tags = [t for t, _ in tags_top] or base.tags

    proyecto_slug = proyecto.replace(" ", "-").lower()[:30] if proyecto else ""
    titulo = f"{proyecto_slug} {nombre}" if proyecto_slug else nombre
    titulo = titulo.replace("-", " ").title()

    contenido_parts: list[str] = []
    for n in nodos[:20]:
        tit = n.title.replace("**", "")
        contenido_parts.append(f"### {tit}\n\n{n.summary or '(sin descripción)'}")

    contenido = "\n\n".join(contenido_parts)

    return Node(
        id=f"CONSOLIDADO-{nombre}",
        type=base.type,
        title=f"{titulo} ({len(nodos)} items)",
        summary=contenido,
        tags=list(set(tags)),
        source="consolidacion",
        status="completado",
        version=base.version,
    )


def _consolidar_nodos(nodes: list[Node], project_name: str = "") -> tuple[list[Node], dict[str, list[str]]]:
    """Consolida notas relacionadas en grupos."""
    grupos: dict[tuple[str, str], list[Node]] = defaultdict(list)
    sin_grupo: list[Node] = []

    for n in nodes:
        grupo = _detectar_grupo(n)
        if grupo:
            clave = (grupo, n.type)
            grupos[clave].append(n)
        else:
            sin_grupo.append(n)

    resultado = list(sin_grupo)
    tracking: dict[str, list[str]] = {}

    for (nombre, tipo), nodos_grupo in grupos.items():
        if len(nodos_grupo) >= 5:
            consolidado = _consolidar_grupo(nombre, nodos_grupo, proyecto=project_name)
            if consolidado:
                resultado.append(consolidado)
                tracking[f"{nombre} ({tipo})"] = [n.id for n in nodos_grupo]
        else:
            resultado.extend(nodos_grupo)

    return resultado, tracking


def _obtener_carpeta_estado(node: Node) -> str:
    """Determina la subcarpeta de estado para un nodo."""
    status = node.status.lower() if node.status else "pendiente"
    return STATUS_FOLDERS.get(status, STATUS_FOLDERS["pendiente"])


def _crear_estructura_carpetas(output_dir: str) -> None:
    """Crea la estructura de carpetas básica del vault."""
    for folder in TYPE_TO_FOLDER.values():
        os.makedirs(os.path.join(output_dir, folder), exist_ok=True)


def _obtener_ruta_nota(node: Node, output_dir: str) -> str:
    """Obtiene la ruta de archivo para un nodo individual."""
    folder = TYPE_TO_FOLDER.get(node.type, "02-IDEAS")
    slug = _slugificar(node.title)
    return os.path.join(output_dir, folder, f"{slug}.md")


def _render_conexiones(output_dir: str, nodes: list[Node], edges: list[Edge]) -> None:
    """Genera un archivo con todas las conexiones para graph view."""
    from context_map.core.storage.store import _ensure

    path = os.path.join(output_dir, "00-CONEXIONES.md")
    _ensure(path)

    node_map = {n.id: n for n in nodes}

    partes = [
        "---",
        "type: conexiones",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        "# 🔗 Todas las Conexiones",
        "",
        "Este archivo muestra todas las relaciones entre notas.",
        "Útil para entender la estructura del grafo.",
        "",
        "| Origen | Destino | Tipo | Nota |",
        "|--------|---------|------|------|",
    ]

    for e in edges:
        src = node_map.get(e.source)
        tgt = node_map.get(e.target)
        src_slug = _slugificar(src.title) if src else e.source
        tgt_slug = _slugificar(tgt.title) if tgt else e.target
        src_title = src.title[:40] if src else e.source
        tgt_title = tgt.title[:40] if tgt else e.target
        partes.append(f"| [[{src_slug}\\|{src_title}]] | [[{tgt_slug}\\|{tgt_title}]] | {e.kind} | {e.note or '—'} |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))


def _render_tracking_consolidacion(output_dir: str, tracking: dict[str, list[str]]) -> None:
    """Genera archivo de tracking de consolidación."""
    path = os.path.join(output_dir, "00-CONSOLIDACION.md")

    partes = [
        "---",
        "type: consolidacion",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        "---",
        "",
        "# 📦 Notas Consolidadas",
        "",
        "Este archivo rastrea qué notas fueron consolidadas en una sola.",
        "Útil para auditoría y referencia.",
        "",
    ]

    for grupo, ids in tracking.items():
        partes.append(f"## {grupo}")
        partes.append("")
        partes.append(f"**Notas originales**: {len(ids)}")
        partes.append("")
        for id_ in ids:
            partes.append(f"- `{id_}`")
        partes.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))

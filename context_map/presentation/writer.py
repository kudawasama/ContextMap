"""Generador de vault Obsidian desde el grafo de contexto.

Produce archivos .md con:
- YAML frontmatter (tags, created, type)
- [[wiki-links]] entre conceptos
- Secciones de descripción, conexiones y evidencia
- Un MOC (Map of Content) como índice principal
- Carpetas por estado (COMPLETADO, EN_PROGRESO, PENDIENTE)
- Consolidación de notas relacionadas
"""

from __future__ import annotations

import os
import re
from typing import List, Dict, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict

from context_map.core.models import Node, Edge

# Mapeo de tipos a carpetas del vault
TYPE_TO_FOLDER = {
    "BASE": "01-PROYECTOS",
    "IDEA": "02-IDEAS",
    "RIESGO": "03-RIESGO",
    "CAMBIO": "04-CAMBIOS",
    "PRUEBA": "05-PRUEBAS",
    "FUTURO": "06-FUTURO",
    "HITO": "07-HITORIAL",
    "CORRECCION": "08-CORRECCIONES",
}

# Subcarpetas por estado
STATUS_FOLDERS = {
    "completado": "COMPLETADO",
    "en_progreso": "EN_PROGRESO",
    "pendiente": "PENDIENTE",
    "cancelado": "CANCELADO",
}


def _slugificar(texto: str) -> str:
    """Convierte texto a slug seguro para nombres de archivo."""
    slug = texto.lower().strip()
    slug = re.sub(r"[áàäâ]", "a", slug)
    slug = re.sub(r"[éèëê]", "e", slug)
    slug = re.sub(r"[íìïî]", "i", slug)
    slug = re.sub(r"[óòöô]", "o", slug)
    slug = re.sub(r"[úùüû]", "u", slug)
    slug = re.sub(r"[ñ]", "n", slug)
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug[:60] or "sin-nombre"


def _frontmatter(node: Node) -> str:
    """Genera YAML frontmatter para una nota Obsidian."""
    tags_str = ", ".join(f'"{t}"' for t in node.tags) if node.tags else ""
    tag_line = f"tags: [{tags_str}]" if tags_str else "tags: []"

    return f"""---
type: {node.type.lower()}
status: {node.status}
version: {node.version}
created: {node.created_at}
updated: {node.updated_at}
source: "{node.source}"
{tag_line}
---"""


def _wiki_links(node: Node, all_nodes: List[Node], edges: List[Edge]) -> List[str]:
    """Encuentra conexiones related basado en aristas y tags compartidos."""
    links = []

    # 1. Links por aristas directas
    for e in edges:
        if e.source == node.id:
            target = next((n for n in all_nodes if n.id == e.target), None)
            if target:
                slug = _slugificar(target.title)
                links.append(f"[[{slug}|{target.title[:50]}]]")
        elif e.target == node.id:
            source = next((n for n in all_nodes if n.id == e.source), None)
            if source:
                slug = _slugificar(source.title)
                links.append(f"[[{slug}|{source.title[:50]}]]")

    # 2. Links por tags compartidos (excluyendo self)
    if node.tags:
        for other in all_nodes:
            if other.id == node.id:
                continue
            shared = set(node.tags) & set(other.tags)
            if shared and other.id not in [e.source for e in edges if e.target == node.id]:
                slug = _slugificar(other.title)
                links.append(f"[[{slug}|{other.title[:50]}]]")

    # Eliminar duplicados preservando orden
    seen = set()
    unique = []
    for l in links:
        if l not in seen:
            seen.add(l)
            unique.append(l)
    return unique[:10]  # Max 10 links por nota


def _render_nota(node: Node, all_nodes: List[Node], edges: List[Edge]) -> str:
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

    # Badge de estado
    if status_badge:
        partes.append(f"**Estado**: {status_badge}")
        partes.append("")

    # Tags como badges
    if node.tags:
        tags_badges = " ".join(f"`#{t}`" for t in node.tags)
        partes.append(f"**Tags**: {tags_badges}")
        partes.append("")

    # Información de origen
    if node.source:
        partes.append(f"**Origen**: `{node.source}`")
        partes.append("")

    # Resumen/Descripción
    if node.summary and node.summary != node.title:
        partes.append("## 📝 Descripción")
        partes.append("")
        partes.append(node.summary)
        partes.append("")

    # Conexiones
    if links:
        partes.append("## 🔗 Conexiones")
        partes.append("")
        for link in links:
            partes.append(f"- {link}")
        partes.append("")

    # Evidencia
    if node.evidence:
        partes.append("## 📋 Evidencia")
        partes.append("")
        for ev in node.evidence:
            partes.append(f"- {ev}")
        partes.append("")

    return "\n".join(partes)


def _render_moc(project_name: str, nodes: List[Node], edges: List[Edge]) -> str:
    """Renderiza el Map of Content (índice principal)."""
    frontmatter = f"""---
type: moc
created: {datetime.now().isoformat(timespec="seconds")}
project: "{project_name}"
total_nodes: {len(nodes)}
total_edges: {len(edges)}
---"""

    # Agrupar por tipo
    por_tipo: Dict[str, List[Node]] = {}
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
        "Mapa mental del proyecto — contexto técnico y emocional.",
        "",
        "---",
        "",
    ]

    # Stats rápidas
    partes.append("## 📊 Resumen")
    partes.append("")
    for tipo, items in sorted(por_tipo.items()):
        icono = iconos.get(tipo, "📝")
        partes.append(f"- {icono} **{tipo}**: {len(items)} notas")
    partes.append(f"- 🔗 **Conexiones**: {len(edges)} aristas")
    partes.append("")

    # Notas por tipo
    for tipo in ["BASE", "IDEA", "RIESGO", "CAMBIO", "PRUEBA", "FUTURO", "HITO", "CORRECCION"]:
        items = por_tipo.get(tipo, [])
        if not items:
            continue
        icono = iconos.get(tipo, "📝")
        partes.append(f"## {icono} {tipo}")
        partes.append("")
        for n in items:
            slug = _slugificar(n.title)
            partes.append(f"- [[{slug}|{n.title[:70]}]]")
        partes.append("")

    return "\n".join(partes)


# ============================================================
# CONSOLIDACIÓN DE NOTAS RELACIONADAS
# ============================================================

def _detectar_grupo(nodo: Node) -> Optional[str]:
    """Detecta si un nodo pertenece a un grupo que puede consolidarse."""
    title_lower = nodo.title.lower()
    text = nodo.summary.lower() if nodo.summary else ""

    # Grupo: Estructura del proyecto
    if "archivos de tipo" in title_lower or "archivos de tipo" in text:
        return "ESTRUCTURA"

    # Grupo: Descripciones de módulos Python
    if re.match(r".*\.py\s+(define|descripción|docstring)", title_lower):
        return "MODULOS_PYTHON"

    # Grupo: TODOs/pendientes del scanner
    if "pendiente en" in title_lower and ("l" in title_lower and ":" in title_lower):
        return "TODOS_SCANNER"

    # Grupo: Commits de features
    if re.match(r"[a-f0-9]{7}\s+feat:", title_lower):
        return "FEATURES"

    # Grupo: Commits de docs
    if re.match(r"[a-f0-9]{7}\s+docs?:", title_lower):
        return "DOCS"

    # Grupo: Commits de chore
    if re.match(r"[a-f0-9]{7}\s+chore:", title_lower):
        return "CHORES"

    return None


def _consolidar_grupo(nombre: str, nodos: List[Node]) -> Node:
    """Consolida un grupo de nodos relacionados en uno solo."""
    if not nodos:
        return None

    # Tomar el primero como base
    base = nodos[0]

    # Construir contenido consolidado
    contenido_parts = []
    for n in nodos:
        contenido_parts.append(f"### {n.title}\n\n{n.summary or '(sin descripción)'}")

    contenido = "\n\n".join(contenido_parts)

    # Crear nodo consolidado
    return Node(
        id=f"CONSOLIDADO-{nombre}",
        type=base.type,
        title=f"{nombre} ({len(nodos)} items)",
        summary=contenido,
        tags=list(set(t for n in nodos for t in n.tags)),
        source="consolidacion",
        status="completado",
        version=base.version,
    )


def _consolidar_nodos(nodes: List[Node]) -> Tuple[List[Node], Dict[str, List[str]]]:
    """Consolida notas relacionadas.

    Retorna:
        - Lista de nodos (algunos consolidados)
        - Mapa de grupo -> IDs originales (para tracking)
    """
    # Agrupar por grupo
    grupos: Dict[str, List[Node]] = defaultdict(list)
    sin_grupo: List[Node] = []

    for n in nodes:
        grupo = _detectar_grupo(n)
        if grupo:
            grupos[grupo].append(n)
        else:
            sin_grupo.append(n)

    # Consolidar grupos con 3+ miembros
    resultado = list(sin_grupo)
    tracking: Dict[str, List[str]] = {}

    for nombre, nodos_grupo in grupos.items():
        if len(nodos_grupo) >= 3:
            consolidado = _consolidar_grupo(nombre, nodos_grupo)
            if consolidado:
                resultado.append(consolidado)
                tracking[nombre] = [n.id for n in nodos_grupo]
        else:
            # Si tiene menos de 3, agregar individuales
            resultado.extend(nodos_grupo)

    return resultado, tracking


# ============================================================
# CARPETAS POR ESTADO
# ============================================================

def _obtener_carpeta_estado(node: Node) -> str:
    """Determina la subcarpeta de estado para un nodo."""
    status = node.status.lower() if node.status else "pendiente"
    return STATUS_FOLDERS.get(status, STATUS_FOLDERS["pendiente"])


def _crear_estructura_carpetas(output_dir: str) -> None:
    """Crea la estructura de carpetas con estados."""
    for folder in TYPE_TO_FOLDER.values():
        folder_path = os.path.join(output_dir, folder)
        for status_folder in STATUS_FOLDERS.values():
            os.makedirs(os.path.join(folder_path, status_folder), exist_ok=True)


# ============================================================
# RENDER PRINCIPAL
# ============================================================

def render_obsidian_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Genera un vault completo de Obsidian.

    Incluye:
    - Carpetas por estado
    - Notas consolidadas
    - MOC principal
    - Conexiones

    Retorna la ruta del vault creado.
    """
    # Crear estructura de carpetas
    _crear_estructura_carpetas(output_dir)

    # Consolidar notas relacionadas
    nodos_consolidados, tracking = _consolidar_nodos(nodes)

    # Generar MOC principal
    moc_path = os.path.join(output_dir, "00-INDICE.md")
    with open(moc_path, "w", encoding="utf-8") as f:
        f.write(_render_moc(project_name, nodos_consolidados, edges))

    # Generar notas individuales
    for node in nodos_consolidados:
        folder = TYPE_TO_FOLDER.get(node.type, "02-IDEAS")
        status_folder = _obtener_carpeta_estado(node)
        slug = _slugificar(node.title)
        filename = f"{slug}.md"

        filepath = os.path.join(output_dir, folder, status_folder, filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(_render_nota(node, nodos_consolidados, edges))

    # Generar archivo de conexiones (graph view helper)
    _render_conexiones(output_dir, nodos_consolidados, edges)

    # Generar archivo de tracking de consolidación
    if tracking:
        _render_tracking_consolidacion(output_dir, tracking)

    return output_dir


def _render_conexiones(output_dir: str, nodes: List[Node], edges: List[Edge]) -> None:
    """Genera un archivo con todas las conexiones para graph view."""
    from context_map.core.store import _ensure

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


def _render_tracking_consolidacion(output_dir: str, tracking: Dict[str, List[str]]) -> None:
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


# ============================================================
# Función legacy para ACTIVE.md (mantener compatibilidad)
# ============================================================

def _section(title: str, body: str, level: int = 2) -> str:
    return f"{'#' * level} {title}\n\n{body.strip()}\n\n"


def _node_list(nodes: List[Node]) -> str:
    if not nodes:
        return "_(sin registros)_"
    grouped: dict[str, list[Node]] = {t: [] for t in [
        "BASE", "IDEA", "PRUEBA", "FUTURO", "CORRECCION",
        "CAMBIO", "RIESGO", "HITO",
    ]}
    for n in nodes:
        grouped.setdefault(n.type, []).append(n)

    out: List[str] = []
    for t in list(grouped.keys()):
        items = grouped.get(t, [])
        if not items:
            continue
        out.append(f"- **{t}**\n")
        out.append("  - **ID**, título/tags, estado, source, versión\n")
        for n in items:
            tags = ", ".join(n.tags) if n.tags else "—"
            ev = "; ".join(n.evidence) if n.evidence else "—"
            line = (
                f"    - **{n.id}** {n.title} `[{tags}]` {n.status}"
                f" | v{n.version} | src: {n.source or '—'} | ev: {ev}"
            )
            if n.summary:
                line += f"\n      - {n.summary[:220]}"
            out.append(line)
        out.append("")
    return "\n".join(out)


def _edges_table(edges: List[Edge]) -> str:
    if not edges:
        return "_(sin conexiones)_"
    lines = ["| source | target | tipo | nota |", "|---|---|---|---|"]
    for e in edges[:200]:
        lines.append(
            f"| {e.source} | {e.target} | {e.kind} | {(e.note or '—')[:80]} |"
        )
    return "\n".join(lines)


def render_active_map(project_name: str, nodes: List[Node], edges: List[Edge]) -> str:
    nodes_by_type: dict[str, List[Node]] = {}
    for n in nodes:
        nodes_by_type.setdefault(n.type, []).append(n)

    body = ""
    body += _section("Identidad del proyecto", project_name)
    body += _section(
        "Historia causal",
        "\n".join(
            f"- {n.id}: {n.title}"
            for n in (nodes_by_type.get("HITO", []) or nodes[:5])
        ) or "_(pendiente)_",
    )
    body += _section("Mapa mental de contexto", _node_list(nodes))
    body += _section("Conexiones", _edges_table(edges))
    body += _section(
        "Cambios esperados / vivos",
        "\n".join(
            f"- {n.id}: {n.title}" for n in nodes_by_type.get("CAMBIO", [])
        ) or "_(pendiente)_",
    )
    body += _section(
        "Riesgos activos",
        "\n".join(
            f"- {n.id}: {n.title}" for n in nodes_by_type.get("RIESGO", [])
        ) or "_(pendiente)_",
    )
    body += _section(
        "Instrucciones para agentes",
        (
            "1) Usar solo este archivo como memoria oficial del proyecto.\n"
            "2) No reeditar el mapa: usar CLI para agregar nodos/eventos.\n"
            "3) Toda modificación genera snapshot en `.context-map/maps/HISTORY/`."
        ),
    )

    return f"# {project_name} — Context Map\n\n{body}"


# ============================================================
# Generador de diagramas Mermaid
# ============================================================

def _mermaid_safe_id(text: str) -> str:
    """Convierte texto a un ID seguro para Mermaid."""
    safe = re.sub(r"[^a-zA-Z0-9]", "_", text)
    return safe[:30]


def render_mermaid(nodes: List[Node], edges: List[Edge]) -> str:
    """Genera un diagrama Mermaid de las conexiones.

    Returns:
        String con el diagrama en formato Mermaid
    """
    if not nodes:
        return "```mermaid\ngraph TD\n    empty[Vacío]\n```"

    # Colores por tipo
    colores = {
        "BASE": "#4CAF50",
        "IDEA": "#2196F3",
        "RIESGO": "#F44336",
        "CAMBIO": "#FF9800",
        "PRUEBA": "#9C27B0",
        "FUTURO": "#00BCD4",
        "HITO": "#FFEB3B",
        "CORRECCION": "#795548",
    }

    lineas = ["graph TD"]

    # Nodos
    for n in nodes[:30]:  # Límite para legibilidad
        node_id = _mermaid_safe_id(n.id)
        titulo = n.title[:40].replace('"', "'")
        color = colores.get(n.type, "#9E9E9E")
        lineas.append(f'    {node_id}["{titulo}"]')

    # Aristas
    for e in edges[:50]:
        src = _mermaid_safe_id(e.source)
        dst = _mermaid_safe_id(e.target)
        lineas.append(f"    {src} --> {dst}")

    return "```mermaid\n" + "\n".join(lineas) + "\n```"

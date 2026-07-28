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

FOLDER_BY_NAME = {v: k for k, v in TYPE_TO_FOLDER.items()}
STANDARD_TAGS_BY_TYPE = {
    "BASE": ["proyecto"],
    "IDEA": ["idea"],
    "RIESGO": ["riesgo"],
    "CAMBIO": ["cambio"],
    "PRUEBA": ["prueba"],
    "FUTURO": ["futuro"],
    "HITO": ["hito"],
    "CORRECCION": ["correccion"],
}
STANDARD_TAGS_COMMON = ["context-map"]


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


def _safe_slug(text: str) -> str:
    return _slugificar(text)


def _normalize_tags(tags: List[str], type_name: str) -> List[str]:
    base_tags = STANDARD_TAGS_COMMON[:]
    topic_tags = [t for t in tags if t not in base_tags]
    topic_tags = list(dict.fromkeys(topic_tags))[:5]
    return STANDARD_TAGS_BY_TYPE.get(type_name) + topic_tags


def _vault_nodes_and_edges(output_dir: str) -> Tuple[List[Node], List[Edge]]:
    nodes: List[Node] = []
    edges: List[Edge] = []
    seen_nodes: Set[str] = {"00-INDICE"}
    seen_edges: Set[Tuple[str, str, str]] = set()

    def add_node(node_id: str, title: str, kind: str, tags: List[str], summary: str = "", source: str = "vault") -> Optional[Node]:
        if node_id in seen_nodes:
            return None
        seen_nodes.add(node_id)
        node = Node(
            id=node_id,
            type=kind,
            title=title,
            summary=summary,
            tags=_normalize_tags(tags, kind),
            source=source,
            status="vigente",
        )
        nodes.append(node)
        return node

    def add_edge(src: str, target: str, kind: str = "contains", note: str = "") -> None:
        key = (src, target, kind)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append(Edge(source=src, target=target, kind=kind, note=note))

    index_node = Node(
        id="00-INDICE",
        type="BASE",
        title="00 INDICE",
        summary="Indice central del vault.",
        tags=_normalize_tags(["indice"], "BASE"),
        source="vault",
        status="vigente",
    )
    nodes.append(index_node)

    top_folders = []
    top_folder_names = []
    for folder_name in TYPE_TO_FOLDER.values():
        folder_path = os.path.join(output_dir, folder_name)
        if os.path.isdir(folder_path):
            top_folder_names.append(folder_name)

    for folder_name in top_folder_names:
        folder_id = _safe_slug(folder_name)
        kind = FOLDER_BY_NAME.get(folder_name, "BASE")
        folder_node = Node(
            id=folder_id,
            type=kind,
            title=folder_name.replace("-", " ").title(),
            summary=f"Carpeta: {folder_name}",
            tags=_normalize_tags(["carpeta", folder_name.lower()], kind),
            source="vault",
            status="vigente",
        )
        nodes.append(folder_node)
        top_folders.append((folder_name, folder_id))
        add_edge("00-INDICE", folder_id, "has_child", folder_name)

    for folder_name, folder_id in top_folders:
        folder_path = os.path.join(output_dir, folder_name)
        for dirpath, dirnames, filenames in os.walk(folder_path):
            subfolder_ids = []
            for dirname in dirnames:
                child_path = os.path.join(dirpath, dirname)
                rel = os.path.relpath(child_path, output_dir).replace("\\", "/")
                child_id = _safe_slug(rel)
                kind = FOLDER_BY_NAME.get(folder_name, "BASE")
                child_node = Node(
                    id=child_id,
                    type=kind,
                    title=dirname.replace("-", " ").title(),
                    summary=f"Carpeta: {rel}",
                    tags=_normalize_tags(["carpeta", dirname.lower()], kind),
                    source="vault",
                    status="vigente",
                )
                nodes.append(child_node)
                add_edge(folder_id, child_id, "has_child", dirname)
                subfolder_ids.append((dirname, child_id, child_path))

            for filename in filenames:
                if not filename.endswith(".md"):
                    continue
                file_path = os.path.join(dirpath, filename)
                rel = os.path.relpath(file_path, output_dir).replace("\\", "/")
                parts = [p for p in rel.split("/") if p]
                if len(parts) < 2:
                    continue
                file_id = _safe_slug(rel.replace(".md", ""))
                kind = FOLDER_BY_NAME.get(folder_name, "BASE")
                file_node = Node(
                    id=file_id,
                    type=kind,
                    title=filename.replace(".md", "").replace("-", " ").title(),
                    summary=f"Archivo: {rel}",
                    tags=_normalize_tags(["archivo", filename.replace(".md", "").lower()], kind),
                    source="vault",
                    status="vigente",
                )
                nodes.append(file_node)
                target_folder_id = _safe_slug(parts[-2])
                add_edge(target_folder_id, file_id, "contains", filename)

    return nodes, edges



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

    # Link de retorno al índice
    partes.append("---")
    partes.append("")
    partes.append("[[00-INDICE|⬅ Volver al índice]]")
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

    por_tipo: Dict[str, List[Node]] = {}
    for n in nodes:
        por_tipo.setdefault(n.type, []).append(n)

    iconos = {
        "BASE": "📦",
        "IDEA": "💡",
        "RIESGO": "⚠️",
        "CAMBIO": "🔄",
        "PRUEBA": "🧪",
        "FUTURO": "🔮",
        "HITO": "🎯",
        "CORRECCION": "🔧",
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

    for tipo in ["BASE", "IDEA", "RIESGO", "CAMBIO", "PRUEBA", "FUTURO", "HITO", "CORRECCION"]:
        items = por_tipo.get(tipo, [])
        if not items:
            continue
        icono = iconos.get(tipo, "📝")
        partes.append(f"## {icono} {tipo}")
        partes.append("")
        for n in items[:40]:
            slug = _slugificar(n.title)
            partes.append(f"- [[{slug}|{n.title[:60]}]]")
        partes.append("")

    partes += [
        "---",
        "",
        "## 🔍 Otros",
        "",
        "- [[00-CONEXIONES|Ver todas las conexiones]]",
        "- [[00-CONSOLIDACION|Ver consolidación]]",
        "",
    ]

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

    # Grupo: Descripciones de __init__.py
    if "__init__" in title_lower:
        return "PAQUETES_PYTHON"

    # Grupo: Descripciones de módulos Python (por .py en título)
    if ".py" in title_lower:
        # No consolidar módulos únicos importantes
        modulos_unicos = ["cli.py", "models.py", "parser.py"]
        if not any(m in title_lower for m in modulos_unicos):
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

    # Grupo: Commits por hash (cualquier tipo)
    if re.match(r"\[?[a-f0-9]{7}\]?", title_lower):
        return "COMMITS"

    return None


def _consolidar_grupo(nombre: str, nodos: List[Node], proyecto: str = "") -> Node:
    """Consolida un grupo de nodos relacionados en uno solo."""
    if not nodos:
        return None

    # Tomar el primero como base
    base = nodos[0]

    # Priorizar resumen más representativo
    candidatos = sorted(
        [n for n in nodos if n.summary and len(n.summary) > 20],
        key=lambda n: len(n.summary or ""),
        reverse=True,
    )
    resumen_principal = candidatos[0].summary if candidatos else (base.summary or "(sin descripción)")

    # Tags más representativos
    tag_counts = {}
    for n in nodos:
        for t in n.tags:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    tags_top = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:8]
    tags = [t for t, _ in tags_top] or base.tags

    # Título más legible: usar el nombre del grupo, proyecto y cantidad
    proyecto_slug = proyecto.replace(" ", "-").lower()[:30] if proyecto else ""
    titulo = f"{proyecto_slug} {nombre}" if proyecto_slug else nombre
    titulo = titulo.replace("-", " ").title()

    # Construir contenido consolidado
    contenido_parts = []
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


def _consolidar_nodos(nodes: List[Node], project_name: str = "") -> Tuple[List[Node], Dict[str, List[str]]]:
    """Consolida notas relacionadas.

    Retorna:
        - Lista de nodos (algunos consolidados)
        - Mapa de grupo -> IDs originales (para tracking)
    """
    # Agrupar por grupo Y tipo (para no mezclar)
    grupos: Dict[Tuple[str, str], List[Node]] = defaultdict(list)
    sin_grupo: List[Node] = []

    for n in nodes:
        grupo = _detectar_grupo(n)
        if grupo:
            clave = (grupo, n.type)  # Grupo + Tipo
            grupos[clave].append(n)
        else:
            sin_grupo.append(n)

    # Consolidar grupos con 5 o más miembros del mismo tipo
    resultado = list(sin_grupo)
    tracking: Dict[str, List[str]] = {}

    for (nombre, tipo), nodos_grupo in grupos.items():
        if len(nodos_grupo) >= 5:
            consolidado = _consolidar_grupo(nombre, nodos_grupo, proyecto=project_name)
            if consolidado:
                resultado.append(consolidado)
                tracking[f"{nombre} ({tipo})"] = [n.id for n in nodos_grupo]
        else:
            # Si tiene menos de 5, agregar individuales
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
    """Crea la estructura de carpetas del vault."""
    for folder in TYPE_TO_FOLDER.values():
        os.makedirs(os.path.join(output_dir, folder), exist_ok=True)


def _obtener_ruta_nota(node: Node, output_dir: str) -> str:
    """Ruta de archivo para un nodo, sin subcarpetas de estado."""
    folder = TYPE_TO_FOLDER.get(node.type, "02-IDEAS")
    slug = _slugificar(node.title)
    return os.path.join(output_dir, folder, f"{slug}.md")


# ============================================================
# RENDER PRINCIPAL
# ============================================================
def _render_consolidated_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo consolidado (4-6 notas temáticas sintéticas).

    Args:
        project_name: Nombre del proyecto
        nodes: Lista de nodos del mapa de contexto
        edges: Lista de aristas/relaciones
        output_dir: Directorio de salida del vault

    Returns:
        Ruta del directorio del vault
    """
    os.makedirs(output_dir, exist_ok=True)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    # Clasificación de nodos por categoría temática
    base_nodes = [n for n in nodes if n.type == "BASE"]
    idea_nodes = [n for n in nodes if n.type == "IDEA"]
    riesgo_nodes = [n for n in nodes if n.type == "RIESGO"]
    cambio_nodes = [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")]
    prueba_nodes = [n for n in nodes if n.type == "PRUEBA"]
    futuro_nodes = [n for n in nodes if n.type == "FUTURO"]
    hito_nodes = [n for n in nodes if n.type == "HITO"]

    # 1. 00-INDICE.md (Dashboard principal)
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
        f"- 🧱 Módulos y Estructura (BASE): **{len(base_nodes)}**",
        f"- 💡 Ideas y Conceptos (IDEA): **{len(idea_nodes)}**",
        f"- ⚠️ Riesgos y Complejidad (RIESGO): **{len(riesgo_nodes)}**",
        f"- 🔮 Tareas y Pendientes (FUTURO): **{len(futuro_nodes)}**",
        f"- 🔄 Cambios e Historial (CAMBIO/CORRECCION): **{len(cambio_nodes)}**",
        f"- 🎯 Hitos (HITO): **{len(hito_nodes)}**",
        f"- 🧪 Pruebas (PRUEBA): **{len(prueba_nodes)}**",
        "",
        "---",
        "",
        "## 📂 Secciones Consolidadas",
        "",
        "- [[01-ESTRUCTURA_Y_MODULOS|01. Estructura y Módulos del Proyecto]]",
        "- [[02-RIESGOS_Y_COMPLEJIDAD|02. Riesgos y Complejidad]]",
        "- [[03-BACKLOG_Y_TODOS|03. Backlog y Tareas Pendientes]]",
        "- [[04-HISTORIAL_Y_DECISIONES|04. Historial y Decisiones]]",
        "- [[00-CONEXIONES|05. Grafo Completo de Conexiones]]",
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

    # 2. 01-ESTRUCTURA_Y_MODULOS.md
    est_parts = [
        "---",
        "type: estructura",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        "tags: [context-map, estructura, modulos]",
        "---",
        "",
        f"# 🧱 Estructura y Módulos — {project_name}",
        "",
        "Resumen consolidado de paquetes, módulos, carpetas y componentes principales del proyecto.",
        "",
        "---",
        "",
        "## 📦 Componentes Base y Carpetas",
        "",
    ]
    if base_nodes:
        for n in base_nodes:
            est_parts.append(f"### {n.title}")
            if n.summary:
                est_parts.append(f"{n.summary}")
            if n.source:
                est_parts.append(f"- **Origen**: `{n.source}`")
            if n.tags:
                est_parts.append(f"- **Tags**: {' '.join(f'`#{t}`' for t in n.tags)}")
            est_parts.append("")
    else:
        est_parts.append("_(No se registraron componentes base)_")
        est_parts.append("")

    if idea_nodes:
        est_parts.append("## 💡 Conceptos y Clases Relevantes")
        est_parts.append("")
        for n in idea_nodes[:30]:
            est_parts.append(f"- **{n.title}**: {n.summary or 'Sin descripción'}")
        est_parts.append("")

    est_parts.append("---")
    est_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    est_parts.append("")

    with open(os.path.join(output_dir, "01-ESTRUCTURA_Y_MODULOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(est_parts))

    # 3. 02-RIESGOS_Y_COMPLEJIDAD.md
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
        for n in riesgo_nodes:
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
        for n in prueba_nodes:
            riesgo_parts.append(f"- **{n.title}**: {n.summary or 'Test'}")
        riesgo_parts.append("")

    riesgo_parts.append("---")
    riesgo_parts.append("[[00-INDICE|⬅ Volver al índice]]")
    riesgo_parts.append("")

    with open(os.path.join(output_dir, "02-RIESGOS_Y_COMPLEJIDAD.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(riesgo_parts))

    # 4. 03-BACKLOG_Y_TODOS.md
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
        for n in futuro_nodes:
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

    with open(os.path.join(output_dir, "03-BACKLOG_Y_TODOS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(backlog_parts))

    # 5. 04-HISTORIAL_Y_DECISIONES.md
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
        for n in cambio_nodes[:50]:
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

    with open(os.path.join(output_dir, "04-HISTORIAL_Y_DECISIONES.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(historial_parts))

    # Generar tabla de conexiones unificada
    _render_conexiones(output_dir, nodes, edges)

    return output_dir


def render_obsidian_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
    mode: str = "consolidated",
) -> str:
    """Genera un vault limpio de Obsidian con grafo jerárquico real.

    Args:
        project_name: Nombre del proyecto
        nodes: Nodos del grafo
        edges: Aristas del grafo
        output_dir: Bóveda de salida
        mode: Modo de generación ('consolidated' o 'raw')
    """
    if mode == "consolidated":
        return _render_consolidated_vault(project_name, nodes, edges, output_dir)

    _crear_estructura_carpetas(output_dir)
    nodos_consolidados, tracking = _consolidar_nodos(nodes, project_name=project_name)
    
    # Recolectar carpetas de estado
    state_folders = set()
    for folder in TYPE_TO_FOLDER.values():
        folder_path = os.path.join(output_dir, folder)
        if os.path.isdir(folder_path):
            for sf in STATUS_FOLDERS.values():
                sf_path = os.path.join(folder_path, sf)
                if os.path.isdir(sf_path):
                    state_folders.add((folder, sf))
    
    # Generar MOC principal
    index_slug = "00-INDICE"
    moc_path = os.path.join(output_dir, "00-INDICE.md")
    with open(moc_path, "w", encoding="utf-8") as f:
        f.write(_render_moc(project_name, nodos_consolidados, edges))
    
    # Nodos estructurales del vault
    vault_nodes: List[Node] = []
    vault_edges: List[Edge] = []
    node_slugs = {}
    
    # Nodo índice
    vault_nodes.append(Node(
        id=index_slug,
        type="BASE",
        title="00 INDICE",
        summary=f"Indice central del proyecto: {project_name}",
        tags=["context-map", "indice", "proyecto"],
        source="vault",
        status="vigente",
    ))
    
    # Nodos de carpetas tipo
    type_folder_nodes = {}
    for type_key, folder_name in TYPE_TO_FOLDER.items():
        folder_path = os.path.join(output_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue
        folder_slug = _slugificar(folder_name)
        type_folder_nodes[folder_name] = folder_slug
        vault_nodes.append(Node(
            id=folder_slug,
            type=type_key,
            title=folder_name.replace("-", " ").title(),
            summary=f"Carpeta principal: {folder_name}",
            tags=["context-map", "carpeta", type_key.lower()],
            source="vault",
            status="vigente",
        ))
        vault_edges.append(Edge(
            source=index_slug,
            target=folder_slug,
            kind="has_child",
            note=folder_name,
        ))
    
    # Nodos de subcarpetas de estado y archivos
    for folder_name, state_folder in state_folders:
        folder_path = os.path.join(output_dir, folder_name, state_folder)
        state_slug = _slugificar(f"{folder_name}-{state_folder}")
        parent_slug = type_folder_nodes.get(folder_name, index_slug)
        
        vault_nodes.append(Node(
            id=state_slug,
            type="BASE",
            title=f"{folder_name.replace('-', ' ').title()} - {state_folder}",
            summary=f"Estado: {state_folder} en {folder_name}",
            tags=["context-map", "estado", state_folder.lower()],
            source="vault",
            status="vigente",
        ))
        vault_edges.append(Edge(
            source=parent_slug,
            target=state_slug,
            kind="has_child",
            note=state_folder,
        ))
        
        # Archivos .md en la subcarpeta
        if os.path.isdir(folder_path):
            for filename in os.listdir(folder_path):
                if not filename.endswith(".md"):
                    continue
                file_slug = _slugificar(filename.replace(".md", ""))
                vault_nodes.append(Node(
                    id=file_slug,
                    type=FOLDER_BY_NAME.get(folder_name, "BASE"),
                    title=filename.replace(".md", "").replace("-", " ").title(),
                    summary=f"Archivo: {folder_name}/{state_folder}/{filename}",
                    tags=["context-map", "archivo", filename.replace(".md", "").lower()],
                    source="vault",
                    status="vigente",
                ))
                vault_edges.append(Edge(
                    source=state_slug,
                    target=file_slug,
                    kind="contains",
                    note=filename,
                ))
    
    # Combinar nodos y edges finales
    final_nodes = vault_nodes + nodos_consolidados
    final_edges = vault_edges + edges
    
    # Generar notas individuales
    for node in nodos_consolidados:
        filepath = _obtener_ruta_nota(node, output_dir)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(_render_nota(node, final_nodes, final_edges))
        node_slugs[node.id] = _slugificar(node.title)
    
    _render_conexiones(output_dir, final_nodes, final_edges)
    
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

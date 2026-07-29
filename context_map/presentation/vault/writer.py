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
import subprocess
import shutil
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
    classif_line = f"\nclassification: {node.classification}" if getattr(node, "classification", "") else ""

    return f"""---
type: {node.type.lower()}{classif_line}
status: {node.status}
version: {node.version}
created: {node.created_at}
updated: {node.updated_at}
source: "{node.source}"
{tag_line}
---"""


def _wiki_links(node: Node, all_nodes: List[Node], edges: List[Edge]) -> List[str]:
    """Encuentra conexiones relacionadas basado únicamente en aristas directas (relaciones explícitas)."""
    links = []

    # Links por aristas directas (depends_on, blocks, supersedes)
    for e in edges:
        if e.source == node.id:
            target = next((n for n in all_nodes if n.id == e.target), None)
            if target and target.id != node.id:
                slug = _slugificar(target.title)
                links.append(f"[[{slug}|{target.title[:50]}]]")
        elif e.target == node.id:
            source = next((n for n in all_nodes if n.id == e.source), None)
            if source and source.id != node.id:
                slug = _slugificar(source.title)
                links.append(f"[[{slug}|{source.title[:50]}]]")

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

    # Contexto Narrativo Estructurado (Por qué, De dónde surgió, Para qué, Cómo, Pros y Contras)
    from context_map.core.generators import generar_contexto_narrativo
    partes.append("## 🧠 Contexto Narrativo con Alma")
    partes.append("")
    partes.append(generar_contexto_narrativo(node))
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

    # Find first # title line
    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("#!"):
            title_idx = i
            break

    if title_idx is None:
        return ""

    # After title, skip empty lines, badges, and TOC lines
    start_idx = title_idx + 1
    paragraphs = []
    current_para = []

    for line in lines[start_idx:]:
        stripped = line.strip()

        # Skip empty lines between paragraphs, but use as separator
        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        # Skip badge lines like [![...](...)]
        if stripped.startswith("[!["):
            continue

        # Skip TOC lines like - [Section](#section)
        if stripped.startswith("- [") or stripped.startswith("* ["):
            continue

        # Skip HTML comments
        if stripped.startswith("<!--"):
            continue

        # Skip horizontal rules
        if stripped.startswith("---") or stripped.startswith("___") or stripped.startswith("***"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        # Skip another heading (stop at next heading)
        if stripped.startswith("#"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            break

        # Accumulate paragraph text
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
    """Renderiza la bóveda Obsidian en modo consolidado (8 notas temáticas sintéticas).

    Siempre limpia el directorio del vault antes de regenerar para evitar
    mezclar archivos de generaciones anteriores (modo raw, etc.).

    Args:
        project_name: Nombre del proyecto
        nodes: Lista de nodos del mapa de contexto
        edges: Lista de aristas/relaciones
        output_dir: Directorio de salida del vault

    Returns:
        Ruta del directorio del vault
    """
    # Limpiar vault previo para no mezclar archivos raw viejos
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
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

    # Extraer propósito del proyecto
    proposito_texto = _extract_project_purpose(os.getcwd())

    # ============================================================
    # 1. 00-INDICE.md (Dashboard principal)
    # ============================================================
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

    # ============================================================
    # 2. 01-PROPOSITO.md (NUEVO)
    # ============================================================
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

    # Datos clave: BASE nodes relevantes (identidad del proyecto)
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

    # ============================================================
    # 3. 02-IDEAS.md (NUEVO - separado de estructura)
    # ============================================================
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
        # Agrupar por estado
        completadas = [n for n in idea_nodes if n.status == "completado"]
        pendientes = [n for n in idea_nodes if n.status == "pendiente"]
        activas = [n for n in idea_nodes if n.status == "activo"]

        seen_total = set()

        def _render_idea_group(parts, title, icon, nodes_list, emoji_prefix):
            if not nodes_list:
                return
            parts.append(f"## {icon} {title}")
            parts.append("")
            seen = set()
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

    # ============================================================
    # 4. 03-ESTRUCTURA.md (MODIFICADO - solo BASE)
    # ============================================================
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
        seen_base = set()
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

    # ============================================================
    # 5. 04-RIESGOS_Y_COMPLEJIDAD.md (renumerado)
    # ============================================================
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
        seen_riesgo = set()
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
        seen_prueba = set()
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

    # ============================================================
    # 6. 05-BACKLOG_Y_TODOS.md (renumerado)
    # ============================================================
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
        seen_futuro = set()
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

    # ============================================================
    # 7. 06-HISTORIAL_Y_DECISIONES.md (renumerado)
    # ============================================================
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
        seen_cambio = set()
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

    # Generar tabla de conexiones unificada
    _render_conexiones(output_dir, nodes, edges)

    return output_dir


def _safe_filename(text: str) -> str:
    """Convierte texto a nombre de archivo seguro (sin espacios, max 60 chars)."""
    text = re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip()
    text = re.sub(r'[-\s]+', '-', text)
    return text[:60] or 'untitled'


def _render_hierarchical_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo jerárquico.

    Estructura generada:
        vault-{Project}/
        ├── 00-INDICE.md
        ├── 1.0-PROPOSITO.md
        ├── 1.1-Mapa-Mental-Narrativo.md
        ├── 1.2-Datos-Clave.md
        ├── 1.3-Proposito.md
        ├── 2.0-IDEAS.md
        ├── 2.1-Ideas-Pendientes/  (carpeta con archivos individuales)
        ├── 2.2-Ideas-Futuras/
        ├── 2.3-Ideas-Completas-e-Implementadas/
        ├── 2.4-Ideas-Relevantes.md
        ├── 3.0-ESTRUCTURA.md
        ├── 4.0-RIESGOS.md
        ├── 5.0-BACKLOG.md
        ├── 6.0-HISTORIAL.md
        └── 00-CONEXIONES.md  (via _render_conexiones)

    Args:
        project_name: Nombre del proyecto
        nodes: Lista de nodos del mapa de contexto (ya deduplicados)
        edges: Lista de aristas/relaciones
        output_dir: Directorio de salida del vault

    Returns:
        Ruta del directorio del vault
    """
    # Limpiar vault previo para no mezclar archivos de generaciones anteriores
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir, exist_ok=True)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    # Clasificación de nodos por tipo
    base_nodes = [n for n in nodes if n.type == "BASE"]
    idea_nodes = [n for n in nodes if n.type == "IDEA"]
    riesgo_nodes = [n for n in nodes if n.type == "RIESGO"]
    cambio_nodes = [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")]
    futuro_nodes = [n for n in nodes if n.type == "FUTURO"]
    hito_nodes = [n for n in nodes if n.type == "HITO"]

    # Extraer propósito del proyecto desde README
    proposito_texto = _extract_project_purpose(os.getcwd())

    # Colectar todos los tags para el índice
    all_tags = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])

    # ============================================================
    # 00-INDICE.md (Map of Content principal)
    # ============================================================
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

    # ============================================================
    # 1.0-PROPOSITO/ (CARPETA - Sección Propósito)
    # ============================================================
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

    # Intentar leer README.md del proyecto para poblar la narrativa
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

    # ============================================================
    # 1.2-Datos-Clave.md (métricas)
    # ============================================================
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
    # Mostrar BASE nodes que contengan métricas (archivos, lineas)
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

    # ============================================================
    # 1.3-Proposito.md (Identidad)
    # ============================================================
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
    # BASE nodes de identidad (entrypoints, docs, configuracion)
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

    # ============================================================
    # 2.0-IDEAS/ (CARPETA - Sección Ideas)
    # ============================================================
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

    # ============================================================
    # 2.1-Ideas-Pendientes/ (carpeta con archivos individuales)
    # ============================================================
    if pendientes:
        pendientes_dir = os.path.join(ideas_dir, "2.1-Ideas-Pendientes")
        os.makedirs(pendientes_dir, exist_ok=True)

        # 2.1-Ideas-Pendientes.md — Nota índice de la subcarpeta
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

            # Contexto Narrativo Estructurado
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

    # ============================================================
    # 2.2-Ideas-Futuras/ (carpeta con archivos individuales)
    # ============================================================
    if activas:
        futuras_dir = os.path.join(output_dir, "2.2-Ideas-Futuras")
        os.makedirs(futuras_dir, exist_ok=True)

        # 2.2-Ideas-Futuras.md — Nota índice de la subcarpeta
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

            # Contexto Narrativo Estructurado
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

    # ============================================================
    # 2.3-Ideas-Completas-e-Implementadas/ (batches de 10)
    # ============================================================
    if completadas:
        completadas_dir = os.path.join(ideas_dir, "2.3-Ideas-Completas-e-Implementadas")
        os.makedirs(completadas_dir, exist_ok=True)

        # 2.3-Ideas-Completas.md — Nota índice de la subcarpeta
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

    # ============================================================
    # 2.4-Ideas-Relevantes.md
    # ============================================================
    # Tomar las primeras 20 ideas más cross-cutting
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

    # ============================================================
    # 3.0-ESTRUCTURA/ (CARPETA jerarquica)
    # ============================================================
    estructura_dir = os.path.join(output_dir, "3.0-ESTRUCTURA")
    os.makedirs(estructura_dir, exist_ok=True)

    # 3.0-ESTRUCTURA.md — Indice
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

    # 3.1-Fundamentos.md — Todos los BASE nodes
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
        seen_base = set()
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

    # ============================================================
    # 4.0-RIESGOS/ (CARPETA jerarquica)
    # ============================================================
    riesgos_dir = os.path.join(output_dir, "4.0-RIESGOS")
    os.makedirs(riesgos_dir, exist_ok=True)

    # 4.0-RIESGOS.md — Indice con links a cada riesgo
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

    # Archivo individual por cada riesgo
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

            # Contexto Narrativo Estructurado
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

    # ============================================================
    # 5.0-BACKLOG/ (CARPETA jerarquica)
    # ============================================================
    backlog_dir = os.path.join(output_dir, "5.0-BACKLOG")
    os.makedirs(backlog_dir, exist_ok=True)

    # 5.0-BACKLOG.md — Indice
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

    # 5.1-Tareas.md — Todos los FUTURO nodes
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

    # ============================================================
    # 6.0-HISTORIAL/ (CARPETA jerarquica)
    # ============================================================
    historial_dir = os.path.join(output_dir, "6.0-HISTORIAL")
    os.makedirs(historial_dir, exist_ok=True)

    # Separar CAMBIO y CORRECCION
    cambio_only = [n for n in cambio_nodes if n.type == "CAMBIO"]
    correccion_only = [n for n in cambio_nodes if n.type == "CORRECCION"]

    # 6.0-HISTORIAL.md — Indice
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

    # 6.1-Cambios.md — Solo CAMBIO nodes
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

    # 6.2-Correcciones.md — Solo CORRECCION nodes
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

    # ============================================================
    # 6.3-Versiones.md (Changelog / Historial de Versiones)
    # ============================================================
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
        # Obtener tags ordenados por fecha (mas reciente primero)
        result = subprocess.run(
            ["git", "tag", "--sort=-creatordate"],
            capture_output=True, text=True, cwd=project_root,
            timeout=10
        )
        all_tags = [t.strip() for t in result.stdout.split("\n")
                    if t.strip() and "desktop.ini" not in t]

        if all_tags:
            versiones_parts.append("## Versiones publicadas")
            versiones_parts.append("")

            prev_tag = None
            for tag in all_tags:
                # Fecha del tag
                date_result = subprocess.run(
                    ["git", "log", "-1", "--format=%ai", tag],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_date = date_result.stdout.strip()[:10] if date_result.stdout.strip() else "?"

                # Mensaje anotado del tag
                msg_result = subprocess.run(
                    ["git", "tag", "-l", tag, "--format=%(contents)"],
                    capture_output=True, text=True, cwd=project_root,
                    timeout=10
                )
                tag_msg = msg_result.stdout.strip()

                # Commits desde la version anterior
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
            # Sin tags: agrupar commits por mes
            versiones_parts.append("## Historial por Meses")
            versiones_parts.append("")

            log_result = subprocess.run(
                ["git", "log", "--oneline", "--format=%ai | %s"],
                capture_output=True, text=True, cwd=project_root,
                timeout=10
            )
            all_commits = log_result.stdout.strip().split("\n")

            meses = defaultdict(list)
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

    # Generar tabla de conexiones
    _render_conexiones(output_dir, nodes, edges)

    return output_dir


def render_obsidian_vault(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    output_dir: str = ".context-map/vault",
    mode: str = "hierarchical",
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
    elif mode == "hierarchical":
        return _render_hierarchical_vault(project_name, nodes, edges, output_dir)

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

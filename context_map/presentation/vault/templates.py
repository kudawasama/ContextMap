"""Plantillas, constantes y formateadores auxiliares para la generación del vault.

Este módulo provee utilidades puras para slugificación de textos,
normalización de etiquetas, formateo de YAML frontmatter y renderizado
de secciones Markdown.
"""

from __future__ import annotations

import re

from context_map.core.models import Edge, Node

# Mapeo de tipos a carpetas del vault
TYPE_TO_FOLDER: dict[str, str] = {
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
STATUS_FOLDERS: dict[str, str] = {
    "completado": "COMPLETADO",
    "en_progreso": "EN_PROGRESO",
    "pendiente": "PENDIENTE",
    "cancelado": "CANCELADO",
}

FOLDER_BY_NAME: dict[str, str] = {v: k for k, v in TYPE_TO_FOLDER.items()}

STANDARD_TAGS_BY_TYPE: dict[str, list[str]] = {
    "BASE": ["proyecto"],
    "IDEA": ["idea"],
    "RIESGO": ["riesgo"],
    "CAMBIO": ["cambio"],
    "PRUEBA": ["prueba"],
    "FUTURO": ["futuro"],
    "HITO": ["hito"],
    "CORRECCION": ["correccion"],
}

STANDARD_TAGS_COMMON: list[str] = ["context-map"]


def _clean_null_bytes(text: str) -> str:
    """Remueve caracteres nulos (NUL / \\x00) y de control del texto."""
    if not text:
        return ""
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)


def _slugificar(texto: str) -> str:
    """Convierte texto a slug seguro para nombres de archivo."""
    texto = _clean_null_bytes(texto)
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


def _safe_filename(text: str) -> str:
    """Limpia caracteres inválidos en el nombre de un archivo, incluyendo nulos."""
    text = _clean_null_bytes(text)
    safe = re.sub(r'[\\/*?:"<>|\x00-\x1f]', "", text)
    safe = safe.strip(". ")
    return safe[:100] or "nota"


def _mermaid_safe_id(text: str) -> str:
    """Convierte texto a un ID seguro para Mermaid."""
    text = _clean_null_bytes(text)
    safe = re.sub(r"[^a-zA-Z0-9]", "_", text)
    return safe[:30]


def _normalize_tags(tags: list[str], type_name: str) -> list[str]:
    """Normaliza y limita las etiquetas asociadas a un nodo.

    Aplica tres transformaciones:
    1. Conserva los tags del nodo que NO están en ``STANDARD_TAGS_COMMON``
       (p. ej. evita duplicar ``context-map``).
    2. Deduplica y limita a los primeros 5 ``topic_tags`` para que el
       ``frontmatter`` de Obsidian no se vuelva ruidoso.
    3. Antepone los tags semánticos derivados del tipo de nodo desde
       ``STANDARD_TAGS_BY_TYPE`` y vuelve a deduplicar para evitar
       repeticiones entre el prefijo y los topic_tags.
    """
    base_tags = STANDARD_TAGS_COMMON[:]
    topic_tags = [t for t in tags if t not in base_tags]
    topic_tags = list(dict.fromkeys(topic_tags))[:5]
    prefix = STANDARD_TAGS_BY_TYPE.get(type_name, [])
    combined = prefix + topic_tags
    # Deduplicar preservando orden: evita p. ej. ["riesgo", "class:other", "riesgo"].
    return list(dict.fromkeys(combined))


def _frontmatter(node: Node) -> str:
    """Genera el bloque YAML frontmatter para una nota de Obsidian."""
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


def _wiki_links(node: Node, all_nodes: list[Node], edges: list[Edge]) -> list[str]:
    """Encuentra conexiones relacionadas basado únicamente en aristas directas."""
    links: list[str] = []
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

    seen: set[str] = set()
    unique: list[str] = []
    for enlace in links:
        if enlace not in seen:
            seen.add(enlace)
            unique.append(enlace)
    return unique[:10]


def _section(title: str, body: str, level: int = 2) -> str:
    """Genera una sección Markdown con el nivel de encabezado especificado."""
    return f"{'#' * level} {title}\n\n{body.strip()}\n\n"


def _node_list(nodes: list[Node]) -> str:
    """Renderiza una lista de nodos agrupados por tipo."""
    if not nodes:
        return "_(sin registros)_"
    grouped: dict[str, list[Node]] = {t: [] for t in [
        "BASE", "IDEA", "PRUEBA", "FUTURO", "CORRECCION",
        "CAMBIO", "RIESGO", "HITO",
    ]}
    for n in nodes:
        grouped.setdefault(n.type, []).append(n)

    out: list[str] = []
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


def _edges_table(edges: list[Edge]) -> str:
    """Renderiza una tabla Markdown con las relaciones del grafo."""
    if not edges:
        return "_(sin conexiones)_"
    lines = ["| source | target | tipo | nota |", "|---|---|---|---|"]
    for e in edges[:200]:
        lines.append(
            f"| {e.source} | {e.target} | {e.kind} | {(e.note or '—')[:80]} |"
        )
    return "\n".join(lines)

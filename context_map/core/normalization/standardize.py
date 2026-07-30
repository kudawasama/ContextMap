from __future__ import annotations

"""Estandarización y clasificación semántica de nodos del grafo.

Proporciona funciones para:
- Clasificación semántica basada en Conventional Commits (feature, fix, refactor, docs, test, etc.).
- Normalización y estandarización de tags (elimina redundancias y mapea conceptos).
- Inferencia de estado del nodo (completado, pendiente, activo).
- Corrección de tipo según contenido real.
- Inferencia de evidencias (rutas de archivo, líneas, clases).
- Deduplicación de nodos por (tipo, título) para mantener el grafo limpio.
"""

import re
from typing import List, Dict, Tuple, Optional, Set

from context_map.core.models import Node


# ============================================================
# MAPEOS DE ESTANDARIZACIÓN Y CLASIFICACIÓN SEMÁNTICA
# ============================================================

# Tags a eliminar (redundantes o no informativos)
TAGS_ELIMINAR: set[str] = {
    "todo",
    "otro",
    "docstring",
    "__init__.py",
}

CLASSIFICATION_PATTERNS: List[Tuple[List[str], str, str]] = [
    (["feat", "feature", "nueva", "agregar", "añadir", "implementar", "crear", "soporte para"], "feature", "Feature"),
    (["fix", "corregir", "arreglar", "solucionar", "resolver", "patch", "bug", "error", "fallo"], "fix", "Fix"),
    (["update", "actualizar", "mejorar", "optimizar", "refactor", "refactorizar", "reestructurar", "limpiar"], "update", "Update"),
    (["chore", "mantenimiento", "config", "configurar", "dependenc", "build", "ci", "cd", "docker", "script"], "chore", "Chore"),
    (["refactor", "refactorizar", "reorganizar", "extraer", "modular", "separar", "mover archivo"], "refactor", "Refactor"),
    (["doc", "documentar", "readme", "changelog", "comentario", "docstring", "guia", "tutorial"], "docs", "Documentación"),
    (["test", "testing", "prueba", "cobertura", "mock", "spec", "e2e", "integracion"], "test", "Test"),
    (["style", "formato", "lint", "prettier", "espacios", "indent", "naming", "convencion"], "style", "Style"),
    (["perf", "performance", "rendimiento", "velocidad", "memoria", "cache", "latencia"], "perf", "Performance"),
    (["security", "seguridad", "auth", "autenticacion", "autorizacion", "vulnerabilidad", "cifrado"], "security", "Security"),
]

DEFAULT_CLASSIFICATION: Tuple[str, str] = ("other", "Otro")


def inferir_classification(node: Node) -> Tuple[str, str]:
    """Infiere el id y la etiqueta de clasificación semántica del nodo a partir de su contenido.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        Tuple[str, str]: Tupla con (classification_id, classification_label).
    """
    title_lower = node.title.lower()
    if title_lower.startswith("feat:") or title_lower.startswith("feature:"):
        return "feature", "Feature"
    elif title_lower.startswith("fix:"):
        return "fix", "Fix"
    elif title_lower.startswith("docs:"):
        return "docs", "Documentación"
    elif title_lower.startswith("refactor:"):
        return "refactor", "Refactor"
    elif title_lower.startswith("test:") or title_lower.startswith("tests:"):
        return "test", "Test"
    elif title_lower.startswith("chore:"):
        return "chore", "Chore"
    elif title_lower.startswith("style:"):
        return "style", "Style"
    elif title_lower.startswith("perf:"):
        return "perf", "Performance"

    text = f"{node.title} {node.summary or ''}".lower()

    for keywords, class_id, class_label in CLASSIFICATION_PATTERNS:
        for kw in keywords:
            if kw in text:
                return class_id, class_label

    return DEFAULT_CLASSIFICATION


def classification_tag(classification_id: str) -> str:
    """Genera la etiqueta estandarizada para una clasificación semántica.

    Args:
        classification_id (str): ID de la clasificación semántica.

    Returns:
        str: Etiqueta formateada como 'class:<classification_id>'.
    """
    return f"class:{classification_id}"


TAG_FILE_MAP: Dict[str, str] = {
    "antigravity.py": "integracion",
    "chat_export.py": "integracion",
    "checker.py": "analisis",
    "cli.py": "cli",
    "content.py": "analisis",
    "git.py": "integracion",
    "hermes.py": "integracion",
    "models.py": "modelos",
    "structure.py": "analisis",
    "brief.py": "presentacion",
    "generadores.py": "generadores",
    "parser.py": "parser",
    "reporter.py": "reportes",
    "scanner.py": "scanner",
    "smoke.py": "testing",
    "store.py": "persistencia",
    "sync.py": "sincronizacion",
    "writer.py": "presentacion",
}

TAG_MERGE: Dict[str, str] = {
    "doc": "documentacion",
    "docs": "documentacion",
    "commit": "git",
    "repo": "git",
    "riesgo": "riesgo",
    "complejidad": "riesgo",
    "clases": "modelos",
    "estructura": "arquitectura",
    "config": "configuracion",
    "entrypoint": "cli",
    "tests": "testing",
    "metricas": "analisis",
    "python": "lenguaje",
}


def estandarizar_tags(tags: List[str]) -> List[str]:
    """Estandariza, limpia y desduplica la lista de etiquetas de un nodo.

    Args:
        tags (List[str]): Lista de etiquetas originales.

    Returns:
        List[str]: Lista de etiquetas estandarizadas y ordenadas.
    """
    tags_estandarizados: List[str] = []

    for tag in tags:
        if tag in TAGS_ELIMINAR:
            continue
        if tag in TAG_FILE_MAP:
            tag = TAG_FILE_MAP[tag]
        if tag in TAG_MERGE:
            tag = TAG_MERGE[tag]

        tag = tag.lower().strip()
        tag = re.sub(r"[^a-z0-9:]", "", tag)

        if tag and tag not in tags_estandarizados:
            tags_estandarizados.append(tag)

    return sorted(tags_estandarizados)


def inferir_status(node: Node) -> str:
    """Infiere el estado del nodo según su origen, tipo, etiquetas y contenido.

    Args:
        node (Node): Nodo a procesar.

    Returns:
        str: Estado del nodo ('completado', 'pendiente', 'activo').
    """
    if node.source in ("git", "import-git") or node.title.startswith("[") or re.match(r"^\[[0-9a-f]{7}\]", node.title):
        return "completado"

    text = f"{node.title} {node.summary or ''}".lower()

    # Si es un TODO / FIXME o contiene marcas de pendiente explícitas
    pendiente_kw = ["todo:", "fixme:", "por hacer", "[ ]", "proxima version", "futura"]
    if any(kw in text for kw in pendiente_kw) or "todo" in node.tags:
        return "pendiente"

    # Elementos de estructura, documentación o código existente son completados
    if node.type in ("BASE", "CORRECCION", "HITO", "PRUEBA", "CAMBIO"):
        return "completado"

    if node.source == "scanner":
        if any(prefix in node.title for prefix in ["Función:", "Módulo:", "Clase:", "Documentación", "Entrypoint:", "Proyecto", "Archivo:", "Carpeta", "capa", "__init__"]):
            return "completado"

    # Patrones explícitos de completado en texto
    completado_kw = ["completad", "implementad", "hecho", "terminad", "listo", "resuelt", "aprobad", "finalizad", "[x]", "done", "fixed", "resolved"]
    if any(kw in text for kw in completado_kw):
        return "completado"

    # Patrones de en progreso / activo
    activo_kw = ["en_progreso", "en progreso", "haciendo", "wip", "working", "desarrollo", "activo"]
    if any(kw in text for kw in activo_kw) or node.type == "RIESGO":
        return "activo"

    return "completado"


def inferir_evidence(node: Node) -> List[str]:
    """Infiere evidencias técnicas (archivos, clases, líneas) a partir del texto del nodo.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        List[str]: Lista de evidencias extraídas.
    """
    evidence: List[str] = []

    if node.title:
        rutas = re.findall(r"[.\w/\\]+\.\w+", node.title)
        if rutas:
            evidence.extend([f"Archivo: {r}" for r in rutas[:3]])
        numeros = re.findall(r"\d+", node.title)
        if numeros:
            evidence.append(f"Cantidad: {numeros[0]}")

    if node.summary:
        lineas = re.findall(r"(\d+)\s*líneas?", node.summary)
        if lineas:
            evidence.append(f"Líneas de código: {lineas[0]}")
        clases = re.findall(r"clase[s]?\s*[:]\s*([A-Z]\w+)", node.summary)
        if clases:
            evidence.append(f"Clases: {', '.join(clases[:3])}")

    return evidence


def corregir_tipo(node: Node) -> str:
    """Corrige y ajusta el tipo de nodo según su contenido semántico.

    Args:
        node (Node): Nodo original.

    Returns:
        str: Tipo de nodo corregido (BASE, IDEA, RIESGO, CAMBIO, CORRECCION, PRUEBA, FUTURO, HITO).
    """
    title_lower = node.title.lower()
    summary_lower = node.summary.lower() if node.summary else ""
    text = f"{title_lower} {summary_lower}"

    if node.source == "git":
        if "feat:" in text or "feature:" in text:
            return "IDEA"
        elif "fix:" in text or "bug:" in text:
            return "CORRECCION"
        elif "docs:" in text or "chore:" in text:
            return "CAMBIO"
        elif "test:" in text:
            return "PRUEBA"
        else:
            return "CAMBIO"

    if any(kw in text for kw in ["riesgo", "complejidad", "complejo", "alerta", "vulnerabilidad", "sin test"]):
        return "RIESGO"

    if any(kw in text for kw in ["fix:", "corregir", "arreglar", "solucionar", "parche", "bug", "fallo"]):
        return "CORRECCION"

    if any(kw in text for kw in ["test:", "testing", "pytest", "unit test", "prueba unitaria", "cobertura", "conftest"]):
        return "PRUEBA"

    if any(kw in text for kw in ["todo:", "fixme:", "futuro", "roadmap", "proxima version", "tarea pendiente"]):
        return "FUTURO"

    if any(kw in text for kw in ["hito", "milestone", "release", "version", "v1.", "v2.", "v0."]):
        return "HITO"

    if any(kw in text for kw in ["proyecto", "estructura", "entrypoint", "readme", "configuracion", "paquete", "modulo", "base de datos", "fundamento", "archivos", "carpeta", "documentación", "capa", "__init__", "db_schema"]):
        return "BASE"

    if any(kw in text for kw in ["refactor", "chore", "cambio", "actualizacion", "modificacion", "update"]):
        return "CAMBIO"

    return "IDEA"


def estandarizar_nodo(node: Node) -> Node:
    """Aplica el proceso completo de estandarización y clasificación a un solo nodo.

    Args:
        node (Node): Nodo original.

    Returns:
        Node: Nuevo nodo estandarizado.
    """
    classif_id, _ = inferir_classification(node)
    tags = estandarizar_tags(node.tags)
    
    # Limpiar tags legacy "class{X}" sin colon (ej: "classchore", "classfeature")
    # que se generaron antes de que estandarizar_tags preservara ":"
    tags = [t for t in tags if not re.match(r'^class[a-z]+$', t)]
    
    # Agregar class_tag solo si no existe ya en formato limpio
    class_tag = classification_tag(classif_id)
    if class_tag not in tags:
        tags.append(class_tag)

    # Normalizar título para eliminar volátiles numéricos
    # Ej: "Archivo complejo: writer.py (2346 líneas)" → "Archivo complejo: writer.py"
    #     "Archivos de alta complejidad (24 total) consolidated.py (1441 líneas); parser.py (426 lín"
    #         → "Archivos de alta complejidad: consolidated.py, parser.py"
    title = node.title
    if node.type == "RIESGO":
        # Eliminar (N líneas), (N total), (N lín), (N l truncado) — con o sin cierre
        title = re.sub(r'\s*\(\d+\s*(?:l[ií]neas?|l[ií]n|total|l(?!\w))\)?', '', title)
        # Eliminar resto de ; file(N líneas) truncado
        title = re.sub(r';\s*[^;]+\(\d+\s*l[ií]neas?\)?', '', title)
        # Limpiar separadores residuales y espacios
        title = re.sub(r'\s*;\s*', ', ', title)
        title = title.rstrip(';,').strip()

    nuevo_tipo = corregir_tipo(node)
    nodo_temp = Node(
        id=node.id,
        type=nuevo_tipo,
        title=title,
        summary=node.summary,
        tags=tags,
        source=node.source,
        status=node.status,
        version=node.version,
        evidence=node.evidence,
        created_at=node.created_at,
        updated_at=node.updated_at,
        classification=classif_id,
    )

    return Node(
        id=node.id,
        type=nuevo_tipo,
        title=title,
        summary=node.summary,
        tags=tags,
        source=node.source,
        status=inferir_status(nodo_temp),
        version=node.version,
        evidence=inferir_evidence(node) or node.evidence,
        created_at=node.created_at,
        updated_at=node.updated_at,
        classification=classif_id,
    )


def estandarizar_nodos(nodes: List[Node]) -> List[Node]:
    """Aplica la estandarización a una lista completa de nodos.

    Args:
        nodes (List[Node]): Lista de nodos.

    Returns:
        List[Node]: Lista de nodos procesados.
    """
    return [estandarizar_nodo(n) for n in nodes]


def dedup_nodes(nodes: List[Node]) -> List[Node]:
    """Elimina nodos duplicados conservando la última ocurrencia por (type, title[:80]).

    Previene la acumulación de nodos duplicados en graph.jsonl después de
    múltiples ciclos de scan/build. Mantiene el nodo más reciente (último
    en aparecer) como representante de cada clave única.

    Args:
        nodes (List[Node]): Lista de nodos con posibles duplicados.

    Returns:
        List[Node]: Lista desduplicada, último nodo por clave gana.
    """
    seen: Dict[Tuple[str, str], Node] = {}
    for n in nodes:
        key = (n.type, n.title[:80].lower())
        seen[key] = n  # última ocurrencia gana
    return list(seen.values())

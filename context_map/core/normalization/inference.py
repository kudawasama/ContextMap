"""Inferencia de metadatos semánticos para nodos del grafo.

Proporciona funciones para inferir concepto, clasificación, estado, tipo
y evidencias técnicas de un nodo basándose en sus atributos y contenido.
"""

from __future__ import annotations

import re

from context_map.core.models import Node
from context_map.core.normalization.mappings import (
    CLASSIFICATION_PATTERNS,
    CONCEPT_PATTERNS,
    DEFAULT_CLASSIFICATION,
    DEFAULT_CONCEPT,
)


def inferir_concepto(node: Node) -> str:
    """Infiere el concepto/dominio técnico del nodo.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        str: ID de concepto ('BASEDEDATOS', 'TUI', 'CLI', 'ETL', ...).
    """
    text = f"{node.title} {node.summary or ''}".lower()

    for keywords, concept_id in CONCEPT_PATTERNS:
        for kw in keywords:
            if kw in text:
                return concept_id

    return DEFAULT_CONCEPT


def inferir_classification(node: Node) -> tuple[str, str]:
    """Infiere el id y la etiqueta de clasificación semántica del nodo a partir de su contenido.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        tuple[str, str]: Tupla con (classification_id, classification_label).
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
    if node.type in ("BASE", "CORRECCION", "HITO", "PRUEBA", "CAMBIO", "REGLA"):
        return "completado"

    if node.source == "scanner" and any(
        prefix in node.title
        for prefix in ["Función:", "Módulo:", "Clase:", "Documentación", "Entrypoint:", "Proyecto", "Archivo:", "Carpeta", "capa", "__init__"]
    ):
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


def inferir_evidence(node: Node) -> list[str]:
    """Infiere evidencias técnicas (archivos, clases, líneas) a partir del texto del nodo.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        list[str]: Lista de evidencias extraídas.
    """
    evidence: list[str] = []

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

    if node.type == "DOCUMENTO":
        return "DOCUMENTO"

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

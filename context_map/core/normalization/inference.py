"""Inferencia de metadatos semánticos para nodos del grafo.

Proporciona funciones para inferir concepto, clasificación, estado, tipo
y evidencias técnicas de un nodo basándose en sus atributos y contenido.

La inferencia de **clasificación**, **concepto** y **tipo** ya no resuelve con
«gana la primera palabra clave»: delega en el panel de decisiones tipadas
(:mod:`context_map.core.normalization.paneles`), que acumula evidencia
ponderada, publica una distribución de probabilidad y expone la confianza.
Las reglas duras (Conventional Commits, origen git, tipo explícito) siguen
decidiendo primero y tienen prioridad absoluta sobre el motor léxico.
"""

from __future__ import annotations

import re

from context_map.core.decisiones import Decision
from context_map.core.models import Node
from context_map.core.normalization.mappings import (
    CLASSIFICATION_PATTERNS,
    DEFAULT_CLASSIFICATION,
)
from context_map.core.normalization.paneles import (
    ETIQUETAS_TIPO,
    decidir_clasificacion,
    decidir_concepto,
    decidir_tipo,
)

#: Etiqueta legible de cada clasificación semántica.
_ETIQUETAS_CLASIFICACION: dict[str, str] = {
    class_id: label for _palabras, class_id, label in CLASSIFICATION_PATTERNS
}
_ETIQUETAS_CLASIFICACION.setdefault(DEFAULT_CLASSIFICATION[0], DEFAULT_CLASSIFICATION[1])

#: Prefijos *Conventional Commits* que deciden la clasificación sin ambigüedad.
_PREFIJOS_CONVENCIONALES: tuple[tuple[str, str], ...] = (
    ("feat:", "feature"),
    ("feature:", "feature"),
    ("fix:", "fix"),
    ("docs:", "docs"),
    ("refactor:", "refactor"),
    ("test:", "test"),
    ("tests:", "test"),
    ("chore:", "chore"),
    ("style:", "style"),
    ("perf:", "perf"),
    ("ci:", "chore"),
    ("build:", "chore"),
)


def _etiqueta_clasificacion(class_id: str) -> str:
    """Devuelve la etiqueta legible de una clasificación semántica.

    Args:
        class_id (str): Identificador de clasificación.

    Returns:
        str: Etiqueta legible; la de defecto si el identificador no existe.
    """
    return _ETIQUETAS_CLASIFICACION.get(class_id, DEFAULT_CLASSIFICATION[1])


def inferir_concepto(node: Node) -> str:
    """Infiere el concepto/dominio técnico del nodo.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        str: ID de concepto ('BASEDEDATOS', 'TUI', 'CLI', 'ETL', ...) o
            'GENERAL' cuando ninguna señal acumula evidencia.
    """
    return decidir_concepto(f"{node.title} {node.summary or ''}").eleccion


def inferir_classification(node: Node) -> tuple[str, str]:
    """Infiere el id y la etiqueta de clasificación semántica del nodo.

    Los prefijos *Conventional Commits* deciden primero; para el resto del
    corpus decide el motor de evidencia ponderada.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        tuple[str, str]: Tupla con (classification_id, classification_label).
    """
    title_lower = node.title.lower()
    for prefijo, class_id in _PREFIJOS_CONVENCIONALES:
        if title_lower.startswith(prefijo):
            return class_id, _etiqueta_clasificacion(class_id)

    class_id = decidir_clasificacion(f"{node.title} {node.summary or ''}").eleccion
    return class_id, _etiqueta_clasificacion(class_id)


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


#: Reglas duras de tipo, en orden de precedencia histórica.
#: Cada entrada es ``(tipo, motivo, palabras_clave)``; ``palabras_clave`` vacío
#: significa que la regla se decide por el origen o el tipo del nodo.
_REGLAS_TIPO_TEXTO: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("RIESGO", "palabra clave de riesgo", ("riesgo", "complejidad", "complejo", "alerta", "vulnerabilidad", "sin test")),
    (
        "CORRECCION",
        "palabra clave de corrección",
        ("fix:", "corregir", "arreglar", "solucionar", "parche", "bug", "fallo"),
    ),
    (
        "PRUEBA",
        "palabra clave de prueba",
        ("test:", "testing", "pytest", "unit test", "prueba unitaria", "cobertura", "conftest"),
    ),
    (
        "FUTURO",
        "marcador de trabajo pendiente",
        ("todo:", "fixme:", "futuro", "roadmap", "proxima version", "tarea pendiente"),
    ),
    ("HITO", "marcador de hito", ("hito", "milestone", "release", "version", "v1.", "v2.", "v0.")),
    (
        "BASE",
        "palabra clave estructural",
        (
            "proyecto",
            "estructura",
            "entrypoint",
            "readme",
            "configuracion",
            "paquete",
            "modulo",
            "base de datos",
            "fundamento",
            "archivos",
            "carpeta",
            "documentación",
            "capa",
            "__init__",
            "db_schema",
        ),
    ),
    (
        "CAMBIO",
        "palabra clave de cambio",
        ("refactor", "chore", "cambio", "actualizacion", "modificacion", "update"),
    ),
)


def _tipo_por_regla(node: Node, text: str) -> tuple[str, str] | None:
    """Resuelve el tipo con reglas duras (origen git, tipo explícito o palabras clave).

    Args:
        node (Node): Nodo original.
        text (str): Título y resumen en minúsculas.

    Returns:
        tuple[str, str] | None: Par ``(tipo, motivo)``, o ``None`` si ninguna
            regla aplica y debe decidir el motor de evidencia.
    """
    if node.type == "DOCUMENTO":
        return "DOCUMENTO", "tipo explícito del nodo"

    if node.source == "git":
        if "feat:" in text or "feature:" in text:
            return "IDEA", "Conventional Commit «feat»"
        if "fix:" in text or "bug:" in text:
            return "CORRECCION", "Conventional Commit «fix»"
        if "docs:" in text or "chore:" in text:
            return "CAMBIO", "Conventional Commit «docs/chore»"
        if "test:" in text:
            return "PRUEBA", "Conventional Commit «test»"
        return "CAMBIO", "commit de git sin prefijo conocido"

    for tipo, motivo, palabras in _REGLAS_TIPO_TEXTO:
        if any(kw in text for kw in palabras):
            return tipo, motivo

    return None


def clasificar_tipo(node: Node) -> tuple[str, Decision]:
    """Clasifica el tipo del nodo y devuelve la decisión que lo sustenta.

    Devuelve la decisión calibrada para que el consumidor pueda distinguir un
    acierto seguro de uno ambiguo: las reglas duras (git, DOCUMENTO, palabras
    clave) se marcan como ``por_regla`` y no entran en revisión; el resto expone
    confianza, evidencias y posible conflicto.

    Args:
        node (Node): Nodo original.

    Returns:
        tuple[str, Decision]: Tipo corregido y decisión asociada.
    """
    title_lower = node.title.lower()
    summary_lower = node.summary.lower() if node.summary else ""
    text = f"{title_lower} {summary_lower}"

    regla = _tipo_por_regla(node, text)
    if regla is not None:
        tipo, motivo = regla
        return tipo, Decision.por_regla_dura("tipo_nodo", tipo, ETIQUETAS_TIPO, motivo)

    decision = decidir_tipo(text)
    return decision.eleccion, decision


def corregir_tipo(node: Node) -> str:
    """Corrige y ajusta el tipo de nodo según su contenido semántico.

    Envoltorio compatible de :func:`clasificar_tipo` para los consumidores que
    solo necesitan la etiqueta.

    Args:
        node (Node): Nodo original.

    Returns:
        str: Tipo de nodo corregido (BASE, IDEA, RIESGO, CAMBIO, CORRECCION,
            PRUEBA, FUTURO, HITO, DOCUMENTO).
    """
    return clasificar_tipo(node)[0]

"""Panel de preguntas tipadas de ContextMap (estilo *System One*).

Traduce los catálogos históricos de ``mappings.py`` (conceptos y clasificación
semántica) y los patrones de tipo de evento a **señales ponderadas**, de modo
que la clasificación deje de depender del «gana el primer patrón» y pase a
apoyarse en evidencia acumulada, con confianza calibrada y traza auditable.

Tres decisiones se derivan del mismo texto:

* ``tipo`` — tipo de nodo/evento (IDEA, RIESGO, CORRECCION, …).
* ``clasificacion`` — clasificación semántica (feature, fix, docs, …).
* ``concepto`` — dominio técnico (CLI, ETL, TUI, …).

El orden de las etiquetas de cada pregunta es deliberado: la **primera** es el
valor por defecto histórico, de modo que cuando no hay ninguna evidencia la
distribución es uniforme y el desempate devuelve exactamente el valor que el
proyecto devolvía antes (IDEA, ``other`` y GENERAL respectivamente). Así el
motor solo cambia resultados cuando **hay** evidencia, nunca por accidente.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache

from context_map.core.decisiones import (
    Decision,
    MotorLexicoCalibrado,
    Pregunta,
    Senal,
)
from context_map.core.normalization.mappings import (
    CLASSIFICATION_PATTERNS,
    CONCEPT_PATTERNS,
    DEFAULT_CLASSIFICATION,
    DEFAULT_CONCEPT,
)

#: Tipos válidos del corpus JSONL (movido aquí desde ``clasificacion`` para que
#: el catálogo de tipos y su pregunta tipada vivan en el mismo sitio).
#: ``DOCUMENTO`` se admite como decisión de tipo, pero no como tipo de evento
#: JSONL: los documentos entran por el scanner, no por la ingesta de chats.
ETIQUETAS_TIPO: tuple[str, ...] = (
    "IDEA",
    "CORRECCION",
    "PRUEBA",
    "FUTURO",
    "RIESGO",
    "CAMBIO",
    "BASE",
    "HITO",
    "REGLA",
    "DOCUMENTO",
)

JSONL_TYPES: set[str] = set(ETIQUETAS_TIPO) - {"DOCUMENTO"}

#: Etiqueta de la cola de revisión humana: nodos con evidencia en conflicto.
TAG_REVISION: str = "revision:clasificacion"

#: Confianza mínima para dar una clasificación por buena sin revisión.
UMBRAL_CONFIANZA: float = 0.6

#: Margen máximo entre las dos primeras etiquetas para considerar conflicto.
MARGEN_CONFLICTO: float = 0.15

_SENALES_TIPO: tuple[Senal, ...] = (
    # --- IDEA: propuesta o funcionalidad nueva -------------------------------
    Senal.expresion(r"\b(adding|added|feat|feature)\b", "IDEA", 1.0, "feature/adding"),
    Senal.expresion(r"\b(agregar|añadir|implementar|soporte para|nueva funcionalidad)\b", "IDEA", 0.9, "propuesta nueva"),
    # --- CORRECCION: arreglo de un defecto -----------------------------------
    Senal.expresion(r"\b(fix|fixing|correc\w*|arregl\w*|patch)\b", "CORRECCION", 1.0, "fix/corrección"),
    Senal.expresion(r"\b(reparar|subsanar|solucionar|parchear)\b", "CORRECCION", 0.9, "reparación"),
    # --- PRUEBA: verificación ------------------------------------------------
    Senal.expresion(r"\b(test|tested|pytest|spec|qa)\b", "PRUEBA", 1.0, "test/qa"),
    Senal.expresion(r"\b(cobertura|unittest|smoke test|fixture)\b", "PRUEBA", 0.9, "cobertura"),
    # --- FUTURO: trabajo pendiente o planificado -----------------------------
    Senal.expresion(r"\b(next|future|planned|roadmap)\b", "FUTURO", 1.0, "plan/roadmap"),
    Senal.expresion(r"\b(?:TODO|FIXME|HACK)\b", "FUTURO", 1.0, "marcador TODO/FIXME", ignorar_caso=False),
    Senal.expresion(r"\b(por hacer|próxima versión|pendiente de)\b", "FUTURO", 0.9, "pendiente explícito"),
    # Anti-señal: «todo» en minúsculas es prosa en español, no una tarea.
    Senal.expresion(r"\btodo\b", "FUTURO", -0.6, "prosa «todo» (anti-señal)", ignorar_caso=False),
    # --- RIESGO: problema, bloqueo o deuda -----------------------------------
    Senal.expresion(r"\b(risk|bug|issue|danger|blocked)\b", "RIESGO", 0.95, "risk/bug/blocked"),
    Senal.expresion(
        r"\b(falla|fallo|fallan|rompe|rompió|no funciona|traceback|excepción|deuda técnica|sin tests?)\b",
        "RIESGO",
        0.9,
        "fallo o deuda técnica",
    ),
    # --- CAMBIO / BASE / HITO ------------------------------------------------
    Senal.expresion(r"\b(change|changed|update|updated)\b", "CAMBIO", 0.9, "cambio/actualización"),
    Senal.expresion(r"\b(base|init|seed|bootstrap|setup)\b", "BASE", 0.85, "base/inicialización"),
    Senal.expresion(r"\b(release|milestone)\b", "HITO", 0.9, "release/milestone"),
    Senal.expresion(r"\bv\d+\.\d+(?:\.\d+)?\b", "HITO", 0.8, "versión semántica"),
)

#: Pregunta canónica del tipo de nodo o evento.
PREGUNTA_TIPO = Pregunta(
    nombre="tipo",
    tipo="choice",
    instrucciones="¿Qué clase de información es este texto?",
    etiquetas=ETIQUETAS_TIPO,
    senales=_SENALES_TIPO,
)


def _senales_por_catalogo(
    catalogo: Sequence[tuple[Sequence[str], str] | tuple[Sequence[str], str, str]],
    decaimiento: float = 0.05,
) -> tuple[Senal, ...]:
    """Convierte un catálogo de palabras clave en señales ponderadas.

    El peso decae según la posición histórica del grupo en el catálogo. Así se
    conserva la precedencia original en caso de empate (los grupos que se
    evaluaban antes siguen ganando) sin perder la suma de evidencia.

    Args:
        catalogo (Sequence): Catálogo de ``(palabras_clave, id, etiqueta)`` o
            ``(palabras_clave, id)``.
        decaimiento (float): Cuánto peso se resta por cada posición.

    Returns:
        tuple[Senal, ...]: Señales listas para la pregunta.
    """
    senales: list[Senal] = []
    for indice, entrada in enumerate(catalogo):
        palabras, etiqueta_id = entrada[0], entrada[1]
        peso = round(max(0.25, 1.0 - decaimiento * indice), 4)
        for palabra in palabras:
            senales.append(
                Senal.literal(
                    palabra,
                    etiqueta_id,
                    peso=peso,
                    descripcion=f"«{palabra}»",
                )
            )
    return tuple(senales)


#: Etiquetas de clasificación semántica con el valor por defecto primero.
ETIQUETAS_CLASIFICACION: tuple[str, ...] = (
    DEFAULT_CLASSIFICATION[0],
    *tuple(class_id for _palabras, class_id, _label in CLASSIFICATION_PATTERNS),
)

#: Pregunta canónica de la clasificación semántica.
PREGUNTA_CLASIFICACION = Pregunta(
    nombre="clasificacion",
    tipo="choice",
    instrucciones="¿Qué tipo de trabajo describe este texto?",
    etiquetas=ETIQUETAS_CLASIFICACION,
    senales=_senales_por_catalogo(CLASSIFICATION_PATTERNS),
)

#: Etiquetas de concepto/dominio técnico con el valor por defecto primero.
ETIQUETAS_CONCEPTO: tuple[str, ...] = (
    DEFAULT_CONCEPT,
    *tuple(concept_id for _palabras, concept_id in CONCEPT_PATTERNS),
)

#: Pregunta canónica del dominio técnico.
PREGUNTA_CONCEPTO = Pregunta(
    nombre="concepto",
    tipo="choice",
    instrucciones="¿A qué dominio técnico pertenece este texto?",
    etiquetas=ETIQUETAS_CONCEPTO,
    senales=_senales_por_catalogo(CONCEPT_PATTERNS, decaimiento=0.03),
)

#: Panel completo: las tres preguntas se responden sobre el mismo estado.
PANEL_CLASIFICACION: tuple[Pregunta, ...] = (
    PREGUNTA_TIPO,
    PREGUNTA_CLASIFICACION,
    PREGUNTA_CONCEPTO,
)

#: Motor del proyecto para este panel.
MOTOR_CLASIFICACION = MotorLexicoCalibrado(
    umbral_revision=UMBRAL_CONFIANZA,
    margen_conflicto=MARGEN_CONFLICTO,
)


@lru_cache(maxsize=8192)
def decidir_tipo(texto: str) -> Decision:
    """Clasifica el tipo de información de un texto.

    Args:
        texto (str): Texto a clasificar.

    Returns:
        Decision: Decisión con distribución, confianza y evidencias.
    """
    return MOTOR_CLASIFICACION.decidir(texto, PREGUNTA_TIPO)


@lru_cache(maxsize=8192)
def decidir_clasificacion(texto: str) -> Decision:
    """Clasifica semánticamente un texto (feature, fix, docs, …).

    Args:
        texto (str): Texto a clasificar.

    Returns:
        Decision: Decisión con distribución, confianza y evidencias.
    """
    return MOTOR_CLASIFICACION.decidir(texto, PREGUNTA_CLASIFICACION)


@lru_cache(maxsize=8192)
def decidir_concepto(texto: str) -> Decision:
    """Infiere el dominio técnico de un texto.

    Args:
        texto (str): Texto a clasificar.

    Returns:
        Decision: Decisión con distribución, confianza y evidencias.
    """
    return MOTOR_CLASIFICACION.decidir(texto, PREGUNTA_CONCEPTO)


@lru_cache(maxsize=4096)
def evaluar(texto: str) -> dict[str, Decision]:
    """Responde las tres preguntas del panel en una sola pasada.

    Es el punto de entrada para auditar la clasificación de un texto: devuelve
    decisiones tipadas, no etiquetas sueltas.

    Args:
        texto (str): Texto a evaluar.

    Returns:
        dict[str, Decision]: Decisiones por nombre de pregunta.
    """
    return MOTOR_CLASIFICACION.decidir_panel(texto, PANEL_CLASIFICACION)


def limpiar_cache() -> None:
    """Vacía las memorias internas de decisión.

    Necesario cuando un proceso de larga vida cambia los catálogos (tests que
    parchean ``mappings``) o cuando se quiere medir coste real.
    """
    decidir_tipo.cache_clear()
    decidir_clasificacion.cache_clear()
    decidir_concepto.cache_clear()
    evaluar.cache_clear()


__all__ = [
    "ETIQUETAS_TIPO",
    "ETIQUETAS_CLASIFICACION",
    "ETIQUETAS_CONCEPTO",
    "JSONL_TYPES",
    "TAG_REVISION",
    "UMBRAL_CONFIANZA",
    "MARGEN_CONFLICTO",
    "PREGUNTA_TIPO",
    "PREGUNTA_CLASIFICACION",
    "PREGUNTA_CONCEPTO",
    "PANEL_CLASIFICACION",
    "MOTOR_CLASIFICACION",
    "decidir_tipo",
    "decidir_clasificacion",
    "decidir_concepto",
    "evaluar",
    "limpiar_cache",
]

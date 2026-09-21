"""Pruebas de la clasificación heurística de texto libre (chats/sesiones).

Regresión de la auditoría 2026-09-21: `todo` en minúsculas marcaba como FUTURO
cualquier frase en español, y `hit` marcaba como HITO usos verbales.
"""

from __future__ import annotations

from context_map.core.parsing.clasificacion import _heuristic_event


def test_clasificacion_basica_se_mantiene() -> None:
    """Los casos que ya cubría el suite siguen funcionando."""
    assert _heuristic_event("Fix error in main loop", "chat").type == "CORRECCION"
    assert _heuristic_event("Feature nueva implementada", "chat").type == "IDEA"
    assert _heuristic_event("Pytest unit tests passing", "chat").type == "PRUEBA"


def test_prosa_en_espanol_no_es_tarea_futura() -> None:
    """«todo» en minúsculas es prosa, no una tarea pendiente."""
    for frase in (
        "revisa todo el rango de fechas",
        "ya está todo listo",
        "cargar todo de nuevo",
    ):
        assert _heuristic_event(frase, "chat").type != "FUTURO", frase


def test_marcador_en_mayusculas_si_es_tarea_futura() -> None:
    """El marcador canónico TODO/FIXME sí clasifica como FUTURO."""
    assert _heuristic_event("TODO: unificar el descubrimiento", "chat").type == "FUTURO"
    assert _heuristic_event("queda un FIXME pendiente", "chat").type == "FUTURO"


def test_hit_ya_no_es_hito() -> None:
    """«hit» verbal no es un hito de release."""
    assert _heuristic_event("hit the API endpoint twice", "chat").type != "HITO"
    assert _heuristic_event("release milestone v2", "chat").type == "HITO"


def test_correccion_en_espanol_se_detecta() -> None:
    """`correc` era un patrón muerto: no casaba con «corrección»."""
    assert _heuristic_event("aplicar la corrección del reporte", "chat").type == "CORRECCION"
    assert _heuristic_event("hay que arreglar el cálculo", "chat").type == "CORRECCION"

"""Pruebas unitarias para el módulo context_map.domain.normalization.similarity."""

from context_map.domain.normalization.similarity import (
    deduplicar_elementos_similares,
    distancia_levenshtein,
    similitud_jaccard_ngramas,
    son_textos_similares,
)


def test_distancia_levenshtein() -> None:
    """Verifica el cálculo de distancia de edición."""
    assert distancia_levenshtein("gato", "gato") == 0
    assert distancia_levenshtein("casa", "caza") == 1


def test_similitud_jaccard() -> None:
    """Verifica el índice de similitud de Jaccard por n-gramas."""
    sim = similitud_jaccard_ngramas("Falta de pruebas unitarias", "Falta de tests unitarios")
    assert sim > 0.4


def test_son_textos_similares() -> None:
    """Verifica la detección de similitud difusa."""
    t1 = "Falta de pruebas unitarias en el módulo de autenticación"
    t2 = "Ausencia de pruebas unitarias en el módulo autenticación"
    assert son_textos_similares(t1, t2, umbral=0.75)


def test_deduplicar_elementos_similares() -> None:
    """Verifica la deduplicación de listas por texto similar."""
    items = [
        "Riesgo 1: Falta de cobertura de pruebas unitarias",
        "Riesgo 1: Ausencia de cobertura de pruebas unitarias",
        "Riesgo 2: Vulnerabilidad de seguridad en dependencias",
    ]
    filtrados = deduplicar_elementos_similares(items, lambda x: x, umbral=0.75)
    assert len(filtrados) == 2
    assert filtrados[0] == items[0]
    assert filtrados[1] == items[2]

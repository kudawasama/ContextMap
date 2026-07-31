"""Pruebas unitarias para el submódulo de estandarización y clasificación semántica."""

from __future__ import annotations

from context_map.core.models import Node
from context_map.core.normalization import (
    classification_tag,
    estandarizar_nodo,
    inferir_classification,
)


def test_inferir_classification_feature() -> None:
    """Verifica que las palabras clave de feature infieran correctamente el id 'feature'."""
    node = Node(id="IDEA-01", type="IDEA", title="Agregar nueva funcionalidad de autenticación")
    class_id, label = inferir_classification(node)
    assert class_id == "feature"
    assert label == "Feature"


def test_inferir_classification_fix() -> None:
    """Verifica que un bug o corrección se clasifique como 'fix'."""
    node = Node(id="CORRECCION-01", type="CORRECCION", title="Corregir bug en la serialización JSON")
    class_id, label = inferir_classification(node)
    assert class_id == "fix"
    assert label == "Fix"


def test_inferir_classification_git_prefix() -> None:
    """Verifica que los commits de git usen el prefijo Conventional Commits."""
    node = Node(id="COMMIT-01", type="CAMBIO", title="refactor: reorganizar interfaz del escáner", source="git")
    class_id, label = inferir_classification(node)
    assert class_id == "refactor"
    assert label == "Refactor"


def test_classification_tag() -> None:
    """Verifica la generación de etiquetas de clasificación."""
    assert classification_tag("feature") == "class:feature"


def test_estandarizar_nodo_clasificacion_semantica() -> None:
    """Verifica que estandarizar_nodo asigne la propiedad classification y la etiqueta class:<id>."""
    node = Node(
        id="NODE-10",
        type="IDEA",
        title="test: agregar cobertura de pruebas para el parser",
        tags=["parser"],
    )
    node_est = estandarizar_nodo(node)
    assert node_est.classification == "test"
    assert "class:test" in node_est.tags

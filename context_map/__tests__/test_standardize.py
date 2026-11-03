"""Pruebas unitarias para el submódulo de estandarización y clasificación semántica."""

from __future__ import annotations

from context_map.core.models import Node
from context_map.core.normalization import (
    classification_tag,
    estandarizar_nodo,
    inferir_classification,
)
from context_map.core.normalization.cleaning import ajustar_tags, normalizar_titulo


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


def test_normalizar_titulo_riesgo_quita_volatiles_y_restaura_paths() -> None:
    """El título de un RIESGO queda estable: sin ``(n líneas)`` y con paths legibles.

    Los volátiles numéricos cambian con cualquier edición y rompían la
    deduplicación por (tipo, título); los scans antiguos además aplanaban los
    separadores de los paths.
    """
    node = Node(
        id="RIESGO-01",
        type="RIESGO",
        title=(
            "Archivos de alta complejidad: "
            "context_mapcorenormalizationstandardize.py (151 líneas)"
        ),
    )
    assert (
        normalizar_titulo(node)
        == "Archivos de alta complejidad: context_map/core/normalization/standardize.py"
    )


def test_normalizar_titulo_riesgo_une_listas_con_coma() -> None:
    """Varias rutas con su recuento quedan como una lista limpia de comas."""
    node = Node(
        id="RIESGO-02",
        type="RIESGO",
        title="Duplicación de riesgo: a.py (20 líneas); b.py (30 líneas)",
    )
    assert normalizar_titulo(node) == "Duplicación de riesgo: a.py, b.py"


def test_normalizar_titulo_no_toca_otros_tipos() -> None:
    """Un título ajeno a RIESGO se respeta tal cual, números incluidos."""
    node = Node(id="BASE-01", type="BASE", title="Sprint 2012 (151 líneas)")
    assert normalizar_titulo(node) == "Sprint 2012 (151 líneas)"


def test_ajustar_tags_retira_legacy_y_garantiza_class_tag() -> None:
    """Las etiquetas ``classxxx`` sin dos puntos desaparecen y queda ``class:fix``."""
    assert ajustar_tags(["classchore", "bug"], "fix") == ["bug", "class:fix"]


def test_ajustar_tags_no_duplica_class_tag() -> None:
    """Si la etiqueta ya está en formato limpio, no se repite."""
    assert ajustar_tags(["class:test"], "test") == ["class:test"]


def test_estandarizar_nodo_documento_conserva_ingesta() -> None:
    """Un DOCUMENTO mantiene el estado y la clasificación que le dio la ingesta."""
    node = Node(
        id="DOC-01",
        type="DOCUMENTO",
        title="informe",
        summary="citas",
        source="ingest",
        status="vigente",
        classification="docs",
        concept="VALOR",
    )
    node_est = estandarizar_nodo(node)
    assert node_est.status == "vigente"
    assert node_est.classification == "docs"
    assert node_est.concept == "VALOR"
    assert node_est.tags == ["class:docs"]

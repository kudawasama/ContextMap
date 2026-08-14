"""El refresh sugiere limpiar carpetas temporales sin trackear (R9).

Auditoría 2026-08-14: en Gobernanza quedaron ``piloto_reglas_rut/`` y
``scripts/debug/`` sin trackear. ``refresh`` debe avisar de estos
artefactos para mantener la raíz limpia (regla del AGENTS.md).
"""

from __future__ import annotations

from context_map.application.commands.refresh import _detectar_temporales


def test_detecta_piloto_y_debug(tmp_path):
    """Carpetas tipo piloto_* y scripts/debug sin git se reportan."""
    (tmp_path / "piloto_reglas_rut").mkdir()
    (tmp_path / "scripts" / "debug").mkdir(parents=True)
    (tmp_path / "src").mkdir()

    temporales = _detectar_temporales(str(tmp_path))
    assert len(temporales) == 2
    assert any("piloto_reglas_rut" in t for t in temporales)
    assert any("scripts/debug" in t for t in temporales)


def test_ignora_carpetas_normales(tmp_path):
    """Carpetas de código normales no se reportan como temporales."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    assert _detectar_temporales(str(tmp_path)) == []


def test_sin_carpetas_no_avisa(tmp_path):
    """Proyecto limpio → lista vacía."""
    assert _detectar_temporales(str(tmp_path)) == []

"""Tests de la señal de readiness 'pytest.ini/conftest' (fix falso negativo).

Antes del fix, la señal solo miraba archivos en la raíz del proyecto y
pasaba por alto un ``conftest.py`` anidado (p. ej. ``context_map/__tests__/``)
o la configuración de pytest embebida en ``pyproject.toml``
(``[tool.pytest.ini_options]``), aunque el proyecto sí tuviera tests
configurados.
"""

from __future__ import annotations

import os

from context_map.domain.analysis.signals import analizar_readiness


def _senal(ruta: str, nombre: str):
    resultado = analizar_readiness(ruta)
    return next(s for s in resultado.senales if s.nombre == nombre)


def test_detecta_conftest_anidado_en_directorio_de_tests(tmp_path) -> None:
    """Un conftest.py dentro de context_map/__tests__ debe contar como presente."""
    tests_dir = tmp_path / "context_map" / "__tests__"
    tests_dir.mkdir(parents=True)
    (tests_dir / "conftest.py").write_text("# conftest\n", encoding="utf-8")

    señal = _senal(str(tmp_path), "pytest.ini/conftest")
    assert señal.presente is True


def test_detecta_config_pytest_en_pyproject(tmp_path) -> None:
    """[tool.pytest.ini_options] en pyproject.toml debe contar como presente."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n', encoding="utf-8"
    )

    señal = _senal(str(tmp_path), "pytest.ini/conftest")
    assert señal.presente is True


def test_sin_configuracion_pytest_la_senal_esta_ausente(tmp_path) -> None:
    """Sin ningún indicio de pytest, la señal no debe activarse por error."""
    os.makedirs(tmp_path / "src", exist_ok=True)

    señal = _senal(str(tmp_path), "pytest.ini/conftest")
    assert señal.presente is False

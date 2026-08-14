"""Tests de la señal de frescura del contexto (R1, auditoría 2026-08-14).

Verifica que ``check`` (y por tanto ``refresh``) detecta actividad posterior
al último build: commits git y sesiones de Hermes sin importar.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from context_map.domain.analysis.checker import (
    analizar_readiness,
    _sesiones_posteriores,
    _ultima_actividad,
)


def _hacer_repo(tmp_path, con_build: bool = True, con_git: bool = True) -> str:
    """Crea un mini proyecto con ``.context-map/state/last_build.json``.

    Args:
        tmp_path: Fixture de pytest con directorio temporal.
        con_build (bool): Si se crea el last_build.json.
        con_git (bool): Si se crea la carpeta .git.

    Returns:
        str: Ruta del mini proyecto.
    """
    ctx = tmp_path / ".context-map" / "state"
    ctx.mkdir(parents=True)
    if con_build:
        (ctx / "last_build.json").write_text(
            json.dumps({"clean": False, "manuales_preservadas": 0,
                        "timestamp": "2000-01-01T00:00:00"}),
            encoding="utf-8",
        )
    if con_git:
        (tmp_path / ".git").mkdir(exist_ok=True)
    return str(tmp_path)


def _sesion(fecha_inicio: str) -> SimpleNamespace:
    """Crea una sesión fake de Hermes con la fecha de inicio dada.

    Args:
        fecha_inicio (str): Timestamp (epoch o ISO) de inicio de la sesión.

    Returns:
        SimpleNamespace: Sesión mínima compatible con el modelo.
    """
    return SimpleNamespace(fecha_inicio=fecha_inicio)


def test_ultima_actividad_detecta_commit_posterior_al_build(tmp_path, monkeypatch):
    """Si hay un commit posterior al last_build, la señal avisa."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        if args and args[0] == "log":
            return "1800000000"  # epoch posterior al build (2000-01-01)
        return ""

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    monkeypatch.setattr("context_map.domain.analysis.checker.leer_sesiones", lambda *_: [])
    actividad = _ultima_actividad(ruta)
    assert actividad["commits_posteriores"] > 0
    assert "commit" in actividad["aviso"].lower()


def test_check_avisa_con_sesiones_sin_importar(tmp_path, monkeypatch):
    """Si hay sesiones de Hermes posteriores al build, la señal avisa."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        return ""

    def _fake_leer(db_path=None, limite=None):  # noqa: ANN001
        return [_sesion("1800000000"), _sesion("1800000000"), _sesion("1800000000")]

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    monkeypatch.setattr("context_map.domain.analysis.checker.leer_sesiones", _fake_leer)
    resultado = analizar_readiness(ruta)
    assert any("sin importar" in s for s in resultado.sugerencias)


def test_check_sin_actividad_no_avisa(tmp_path, monkeypatch):
    """Sin commits ni sesiones posteriores, no hay falso aviso."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        return ""

    def _fake_leer(db_path=None, limite=None):  # noqa: ANN001
        return [_sesion("100")]  # anterior al build

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    monkeypatch.setattr("context_map.domain.analysis.checker.leer_sesiones", _fake_leer)
    resultado = analizar_readiness(ruta)
    assert not any("sin importar" in s for s in resultado.sugerencias)


def test_sesiones_posteriores_cuenta_solo_las_recientes(tmp_path, monkeypatch):
    """Cuenta sesiones cuya fecha de inicio supera el timestamp del build."""
    ruta = _hacer_repo(tmp_path)

    def _fake_leer(db_path=None, limite=None):  # noqa: ANN001
        return [
            _sesion("1800000000"),  # posterior a 2000-01-01
            _sesion("1800000000"),
            _sesion("100"),         # anterior al build
        ]

    monkeypatch.setattr("context_map.domain.analysis.checker.leer_sesiones", _fake_leer)
    assert _sesiones_posteriores(ruta) == 2


def test_sin_build_previo_avisa_nunca_build(tmp_path):
    """Si no existe last_build.json, el aviso indica que nunca se ha construido."""
    ruta = _hacer_repo(tmp_path, con_build=False)
    actividad = _ultima_actividad(ruta)
    assert "nunca" in actividad["aviso"].lower()

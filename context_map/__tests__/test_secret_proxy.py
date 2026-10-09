"""Tests del proxy de secretos (Fase 2): inyectar sin exponer, autorizar y auditar."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from context_map.application.commands.secrets import (
    _cmd_secret_exec,
    _cmd_secret_receta,
)
from context_map.core.secrets import entorno_con_secretos, normalizar_var, sanear_salida
from context_map.core.secrets.vault import agregar, crear_documento, guardar

FRASE = "Frase-De-Test-2026"
ITER = 10_000
VALOR = "valor-secreto-abc"


def _eco() -> str:
    return "echo %CTXMAP_SECRET_TK%" if os.name == "nt" else "echo $CTXMAP_SECRET_TK"


def _preparar_baul(tmp_path) -> str:
    ruta = os.path.join(str(tmp_path), ".context-map", "secure", "vault.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "tk", VALOR, scope="proyecto", proyecto="P")
    guardar(ruta, doc)
    return ruta


def test_sanear_salida_redacta_valores() -> None:
    assert sanear_salida(f"token={VALOR} fin", {"tk": VALOR}) == "token=*** fin"


def test_normalizar_var_es_seguro() -> None:
    assert normalizar_var("cl banca!") == "CTXMAP_SECRET_CL_BANCA_"


def test_entorno_inyecta() -> None:
    env = entorno_con_secretos({"tk": VALOR}, base_env={})
    assert env["CTXMAP_SECRET_TK"] == VALOR


def test_exec_sin_autorizacion_se_niega(tmp_path) -> None:
    _preparar_baul(tmp_path)
    args = SimpleNamespace(
        target=str(tmp_path), global_=False, autorizado=False,
        ids="tk", comando="echo x", timeout=30,
    )
    with pytest.raises(SystemExit):
        _cmd_secret_exec(args)


def test_exec_inyecta_y_sanea(tmp_path, monkeypatch, capsys) -> None:
    """El comando ve el valor en su entorno, pero la salida al llamante está saneada."""
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    args = SimpleNamespace(
        target=str(tmp_path), global_=False, autorizado=True,
        ids="tk", comando=_eco(), timeout=30,
    )
    with pytest.raises(SystemExit) as exc:
        _cmd_secret_exec(args)
    assert exc.value.code in (0,)
    salida = capsys.readouterr().out
    assert VALOR not in salida
    assert "***" in salida

    ruta_audit = os.path.join(str(tmp_path), ".context-map", "secure", "audit.log")
    with open(ruta_audit, encoding="utf-8") as f:
        linea = f.read()
    assert "exec ids=tk" in linea
    assert VALOR not in linea


def test_receta_ejecuta_y_sanea(tmp_path, monkeypatch, capsys) -> None:
    """Una receta aprobada se ejecuta con el secreto en el entorno; la salida sale saneada."""
    _preparar_baul(tmp_path)
    recetas = os.path.join(str(tmp_path), ".context-map", "secure", "recetas")
    os.makedirs(recetas, exist_ok=True)
    with open(os.path.join(recetas, "demo.cmd"), "w", encoding="utf-8") as f:
        f.write("@echo off\necho %CTXMAP_SECRET_TK%\n")
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)

    args = SimpleNamespace(
        target=str(tmp_path), global_=False, nombre="demo",
        ids="tk", autorizado=True, timeout=60, rest=[],
    )
    with pytest.raises(SystemExit) as exc:
        _cmd_secret_receta(args)
    assert exc.value.code in (0,)
    salida = capsys.readouterr().out
    assert VALOR not in salida
    assert "***" in salida


def test_mcp_secret_exec_sanea(tmp_path, monkeypatch) -> None:
    """La tool MCP devuelve la salida saneada (el agente nunca ve el valor)."""
    from context_map.infrastructure.mcp_server import secret_exec

    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    salida = secret_exec(ids="tk", comando=_eco(), autorizado=True, target=str(tmp_path), timeout=30)
    assert VALOR not in salida
    assert "***" in salida or "[exit 0]" in salida


def test_mcp_secret_exec_sin_frase_da_error(tmp_path, monkeypatch) -> None:
    """Sin la frase en el servidor, la tool lo indica (no filtra el valor)."""
    from context_map.infrastructure.mcp_server import secret_exec

    _preparar_baul(tmp_path)
    salida = secret_exec(ids="tk", comando="echo x", autorizado=True, target=str(tmp_path), timeout=30)
    assert "ERROR" in salida
    assert VALOR not in salida

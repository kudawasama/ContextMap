"""Tests del proxy de secretos (Fase 2): inyectar sin exponer, autorizar y auditar."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from context_map.application.commands.secrets import (
    _cmd_secret_approve,
    _cmd_secret_exec,
    _cmd_secret_receta,
    _cmd_secret_rekey,
)
from context_map.core.secrets import entorno_con_secretos, sanear_salida, validar_ids_sin_colision
from context_map.core.secrets.vault import agregar, crear_documento, guardar
from context_map.infrastructure import mcp_server

FRASE = "Frase-De-Test-2026"
ITER = 10_000
VALOR = "valor-secreto-abc"


@pytest.fixture(autouse=True)
def _reset_frase_maestra(monkeypatch):
    """Aísla la caché en memoria de la frase maestra entre tests."""
    monkeypatch.setattr(mcp_server, "_FRASE_MAESTRA", None, raising=False)


def _eco() -> str:
    return "echo %CTXMAP_SECRET_TK%" if os.name == "nt" else "echo $CTXMAP_SECRET_TK"


def _eco_var(nombre: str) -> str:
    return f"echo %{nombre}%" if os.name == "nt" else f"echo ${nombre}"


def _preparar_baul(tmp_path) -> str:
    ruta = os.path.join(str(tmp_path), ".context-map", "secure", "vault.json")
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "tk", VALOR, scope="proyecto", proyecto="P")
    guardar(ruta, doc)
    return ruta


def test_sanear_salida_redacta_variantes() -> None:
    texto = f"rev={VALOR[::-1]} b64={__import__('base64').b64encode(VALOR.encode()).decode()} hex={VALOR.encode().hex()}"
    assert "***" in sanear_salida(texto, {"tk": VALOR}, variantes=True)
    # sin variantes, el invertido queda
    assert VALOR[::-1] in sanear_salida(f"rev={VALOR[::-1]}", {"tk": VALOR}, variantes=False)


def test_validar_ids_sin_colision_detecta() -> None:
    with pytest.raises(ValueError):
        validar_ids_sin_colision(["a-b", "a_b"])


def test_entorno_inyecta() -> None:
    env = entorno_con_secretos({"tk": VALOR}, base_env={})
    assert env["CTXMAP_SECRET_TK"] == VALOR


def test_entorno_no_hereda_variables_ctxmap() -> None:
    """La frase maestra, el flag de autorización y secretos previos no pasan al hijo."""
    base = {
        "PATH": "/bin",
        "CTXMAP_MASTER_PHRASE": FRASE,
        "CTXMAP_SECRET_AUTORIZA": "1",
        "CTXMAP_SECRET_VIEJO": "valor-viejo",
        "OTRA": "ok",
    }
    env = entorno_con_secretos({"tk": VALOR}, base_env=base)
    assert env["CTXMAP_SECRET_TK"] == VALOR
    assert "CTXMAP_MASTER_PHRASE" not in env
    assert "CTXMAP_SECRET_AUTORIZA" not in env
    assert "CTXMAP_SECRET_VIEJO" not in env
    assert env["PATH"] == "/bin"
    assert env["OTRA"] == "ok"


def test_exec_no_hereda_frase_maestra(tmp_path, monkeypatch, capsys) -> None:
    """El comando ejecutado no puede leer CTXMAP_MASTER_PHRASE del entorno."""
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    args = SimpleNamespace(
        target=str(tmp_path), global_=False, autorizado=True,
        ids="tk", comando=_eco_var("CTXMAP_MASTER_PHRASE"), timeout=30,
    )
    with pytest.raises(SystemExit):
        _cmd_secret_exec(args)
    salida = capsys.readouterr().out
    assert FRASE not in salida


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
    if os.name == "nt":
        nombre_archivo, contenido = "demo.cmd", "@echo off\necho %CTXMAP_SECRET_TK%\n"
    else:
        nombre_archivo, contenido = "demo.sh", "#!/bin/sh\necho \"$CTXMAP_SECRET_TK\"\n"
    with open(os.path.join(recetas, nombre_archivo), "w", encoding="utf-8") as f:
        f.write(contenido)
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
    monkeypatch.setenv("CTXMAP_MCP_SECRET_EXEC", "1")
    salida = secret_exec(ids="tk", comando=_eco(), autorizado=True, target=str(tmp_path), timeout=30)
    assert VALOR not in salida
    assert "***" in salida or "[exit 0]" in salida


def test_mcp_secret_exec_sin_frase_da_error(tmp_path, monkeypatch) -> None:
    """Sin la frase en el servidor, la tool lo indica (no filtra el valor)."""
    from context_map.infrastructure.mcp_server import secret_exec

    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MCP_SECRET_EXEC", "1")
    salida = secret_exec(ids="tk", comando="echo x", autorizado=True, target=str(tmp_path), timeout=30)
    assert "ERROR" in salida
    assert VALOR not in salida


def test_mcp_secret_exec_no_hereda_frase(tmp_path, monkeypatch) -> None:
    """El hijo del MCP tampoco puede leer la frase maestra."""
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    monkeypatch.setenv("CTXMAP_MCP_SECRET_EXEC", "1")
    salida = mcp_server.secret_exec(
        ids="tk",
        comando=_eco_var("CTXMAP_MASTER_PHRASE"),
        autorizado=True,
        target=str(tmp_path),
        timeout=30,
    )
    assert FRASE not in salida


def test_mcp_frase_maestra_se_borra_del_entorno(monkeypatch) -> None:
    """La frase se conserva en memoria, pero desaparece de os.environ."""
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    assert mcp_server._frase_maestra() == FRASE
    assert "CTXMAP_MASTER_PHRASE" not in os.environ


def test_mcp_no_autorizado_antes_de_descifrar(tmp_path, monkeypatch) -> None:
    """Sin autorización no se intenta descifrar ni se revela si la frase es válida."""
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", "frase-equivocada")
    monkeypatch.setenv("CTXMAP_MCP_SECRET_EXEC", "1")
    salida = mcp_server.secret_exec(
        ids="tk",
        comando="echo x",
        autorizado=False,
        target=str(tmp_path),
        timeout=30,
    )
    assert "no autorizado" in salida
    assert "frase" not in salida.lower()

def test_mcp_deshabilitado_por_defecto(tmp_path, monkeypatch) -> None:
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    # sin CTXMAP_MCP_SECRET_EXEC ni token -> deshabilitado
    salida = mcp_server.secret_exec(ids="tk", comando="echo x", autorizado=True, target=str(tmp_path), timeout=30)
    assert "deshabilitado" in salida


def test_token_flujo_cli(tmp_path, monkeypatch, capsys) -> None:
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    # generar token
    args_app = SimpleNamespace(target=str(tmp_path), global_=False, ids="tk", ttl=300)
    _cmd_secret_approve(args_app)
    out = capsys.readouterr().out
    token = out.splitlines()[0].split(":")[-1].strip()
    # usar token
    args_exec = SimpleNamespace(
        target=str(tmp_path), global_=False, autorizado=False, token=token,
        ids="tk", comando=_eco(), timeout=30,
    )
    with pytest.raises(SystemExit) as exc:
        _cmd_secret_exec(args_exec)
    assert exc.value.code in (0,)
    salida = capsys.readouterr().out
    assert VALOR not in salida
    # segundo uso: token consumido -> denegado
    args_exec2 = SimpleNamespace(
        target=str(tmp_path), global_=False, autorizado=False, token=token,
        ids="tk", comando="echo x", timeout=30,
    )
    with pytest.raises(SystemExit) as exc2:
        _cmd_secret_exec(args_exec2)
    assert "DENEGADA" in str(exc2.value.code)


def test_rekey_cambia_frase(tmp_path, monkeypatch) -> None:
    _preparar_baul(tmp_path)
    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", FRASE)
    # rekey con nueva frase
    monkeypatch.setattr("context_map.application.commands.secrets.getpass.getpass", lambda prompt="": "NuevaFrase-2026")
    # _leer_frase lee env primero
    args = SimpleNamespace(target=str(tmp_path), global_=False)
    _cmd_secret_rekey(args)
    # verificar que el nuevo baúl se descifra con la nueva frase
    from context_map.core.secrets.vault import cargar, obtener
    doc = cargar(os.path.join(str(tmp_path), ".context-map", "secure", "vault.json"))
    assert obtener(doc, "NuevaFrase-2026", "tk") == VALOR

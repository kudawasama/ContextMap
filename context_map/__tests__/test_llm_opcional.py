"""Síntesis generativa opcional con LLM (G6): hook en ``sintetizar``.

Ninguna prueba hace red: cuando se necesita un "LLM" se inyecta un **generador
falso**, y el cliente HTTP se prueba simulando un fallo.
"""

from __future__ import annotations

import json
import os
from types import SimpleNamespace as NS

from context_map.application.commands import wiki as cmd_wiki
from context_map.domain.knowledge import llm
from context_map.domain.knowledge import wiki as kb
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento

_VARIABLES = (llm.VARIABLE_CLAVE, llm.VARIABLE_MODELO, llm.VARIABLE_BASE)


def _vault(tmp_path) -> str:
    """Vault sembrado con una página sobre recuperación de documentos."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    kb.ingresar(
        vdir,
        "Sistemas RAG",
        "RAG combina la recuperación de documentos con la generación de texto natural.",
        entidades="RAG",
    )
    return vdir


def _sin_entorno(monkeypatch) -> None:
    """Elimina las variables del LLM para simular 'no configurado'."""
    for var in _VARIABLES:
        monkeypatch.delenv(var, raising=False)


def test_sin_clave_no_esta_disponible(monkeypatch) -> None:
    """Sin CTXMAP_LLM_API_KEY la síntesis generativa queda apagada."""
    _sin_entorno(monkeypatch)
    ok, motivo = llm.disponible()
    assert ok is False
    assert llm.VARIABLE_CLAVE in motivo, "El motivo debe decir qué variable definir"


def test_configuracion_lee_el_entorno(monkeypatch) -> None:
    """El entorno define modelo y endpoint; sin él se usan los valores por defecto."""
    _sin_entorno(monkeypatch)
    assert llm.configuracion() == {
        "clave": "",
        "modelo": llm.MODELO_DEFAULT,
        "base_url": llm.BASE_DEFAULT,
    }

    monkeypatch.setenv(llm.VARIABLE_CLAVE, "clave-secreta")
    monkeypatch.setenv(llm.VARIABLE_MODELO, "mi-modelo")
    monkeypatch.setenv(llm.VARIABLE_BASE, "https://mi-endpoint/v1/")
    cfg = llm.configuracion()
    assert cfg["clave"] == "clave-secreta"
    assert cfg["modelo"] == "mi-modelo"
    assert cfg["base_url"] == "https://mi-endpoint/v1/"
    assert llm.disponible() == (True, "mi-modelo")


def test_prompt_numerado_con_reglas() -> None:
    """El prompt numera las fuentes y prohíbe inventar."""
    prompt = llm.construir_prompt("¿qué es RAG?", [("Sistemas RAG", "RAG recupera y genera.")])
    assert "[1] Sistemas RAG" in prompt
    assert "RAG recupera y genera." in prompt
    assert "Pregunta: ¿qué es RAG?" in prompt
    assert "no inventes" in prompt
    assert prompt.rstrip().endswith("Respuesta:")


def test_sintetizar_usa_el_generador_inyectado(tmp_path) -> None:
    """Con hook inyectado la respuesta es generativa y conserva las citas."""
    vdir = _vault(tmp_path)
    prompts: list[str] = []

    def _generador(prompt: str) -> str:
        prompts.append(prompt)
        return "RAG une recuperación y generación [1]."

    res = kb.sintetizar(vdir, "¿cómo funciona RAG?", generador=_generador)

    assert res["motor"] == "llm"
    assert res["respuesta"] == "RAG une recuperación y generación [1]."
    assert res["fuentes"], "Debe conservar las fuentes citables"
    assert prompts and "Sistemas RAG" in prompts[0], "El prompt debe llevar el contexto"
    assert res["respuesta_extractiva"], "Debe guardar la versión local trazable"


def test_usar_llm_false_fuerza_lo_extractivo(tmp_path) -> None:
    """``--no-llm`` ignora el hook y responde en local (determinista)."""
    vdir = _vault(tmp_path)
    llamado = False

    def _generador(_prompt: str) -> str:
        nonlocal llamado
        llamado = True
        return "no debería usarse"

    res = kb.sintetizar(vdir, "¿cómo funciona RAG?", generador=_generador, usar_llm=False)

    assert llamado is False
    assert res["motor"] == "extractivo"
    assert "respuesta_extractiva" not in res


def test_sin_configuracion_responde_extractivo(tmp_path, monkeypatch) -> None:
    """Sin LLM configurado la wiki sigue respondiendo con su extracción local."""
    _sin_entorno(monkeypatch)
    vdir = _vault(tmp_path)
    res = kb.sintetizar(vdir, "¿cómo funciona RAG?")
    assert res["motor"] == "extractivo"
    assert "recuperación" in res["respuesta"].lower()


def test_llm_que_falla_cae_en_la_version_extractiva(tmp_path) -> None:
    """Un generador que revienta no rompe la wiki: se devuelve lo extractivo."""
    vdir = _vault(tmp_path)

    def _explotar(_prompt: str) -> str:
        raise RuntimeError("proveedor caído")

    res = kb.sintetizar(vdir, "¿cómo funciona RAG?", generador=_explotar)
    assert res["motor"] == "extractivo"
    assert res["respuesta"], "Debe conservar la respuesta extractiva"


def test_generar_tolera_fallos_de_red(monkeypatch) -> None:
    """El cliente HTTP nunca lanza: ante error devuelve cadena vacía."""
    monkeypatch.setenv(llm.VARIABLE_CLAVE, "clave")

    def _urlopen(*_a, **_k):
        raise OSError("sin conexión")

    monkeypatch.setattr(llm.urllib.request, "urlopen", _urlopen)
    assert llm.generar("pregunta", [("T", "texto")]) == ""


def test_generar_sin_contexto_no_llama_al_modelo(monkeypatch) -> None:
    """Sin fragmentos no hay nada que sintetizar (ni llamada)."""
    monkeypatch.setenv(llm.VARIABLE_CLAVE, "clave")

    def _urlopen(*_a, **_k):  # pragma: no cover - no debe ejecutarse
        raise AssertionError("no debe llamarse")

    monkeypatch.setattr(llm.urllib.request, "urlopen", _urlopen)
    assert llm.generar("pregunta", []) == ""


def test_estado_nunca_expone_la_clave(monkeypatch) -> None:
    """El diagnóstico informa si hay clave, pero jamás la imprime."""
    monkeypatch.setenv(llm.VARIABLE_CLAVE, "clave-secreta")
    diag = llm.estado()
    assert diag["disponible"] is True
    assert diag["clave_configurada"] is True
    assert "clave-secreta" not in json.dumps(diag)
    assert llm.VARIABLE_CLAVE in diag["variables"]


def test_cli_ask_con_llm_sin_configurar_avisa(tmp_path, monkeypatch, capsys) -> None:
    """``wiki ask --llm`` sin clave responde en local y lo advierte."""
    _sin_entorno(monkeypatch)
    vdir = _vault(tmp_path)
    monkeypatch.setattr(cmd_wiki, "_resolver_vault", lambda _args: vdir)

    cmd_wiki.cmd_wiki(NS(
        wiki_cmd="ask", pregunta="¿cómo funciona RAG?", limite=5,
        llm=True, no_llm=False, json=False, target=".",
    ))

    salida = capsys.readouterr().out
    assert "no está configurado" in salida
    assert "(extractivo)" in salida
    assert "Fuentes:" in salida


def test_cli_wiki_llm_muestra_estado(tmp_path, monkeypatch, capsys) -> None:
    """``wiki llm`` explica cómo activarlo cuando no está configurado."""
    _sin_entorno(monkeypatch)
    vdir = _vault(tmp_path)
    monkeypatch.setattr(cmd_wiki, "_resolver_vault", lambda _args: vdir)

    cmd_wiki.cmd_wiki(NS(wiki_cmd="llm", probar=False, json=False, target="."))
    salida = capsys.readouterr().out
    assert "NO configurado" in salida
    assert llm.VARIABLE_CLAVE in salida

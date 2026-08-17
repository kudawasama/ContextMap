"""Pruebas unitarias para el módulo de tokenización context_map.core.tokenization."""

import pytest
from context_map.core.tokenization import TokenCounter, contar_tokens_texto


def test_contar_tokens_texto_vacio() -> None:
    """Verifica que un texto vacío devuelva 0 tokens."""
    assert contar_tokens_texto("") == 0
    assert contar_tokens_texto(None) == 0  # type: ignore


def test_contar_tokens_texto_simple() -> None:
    """Verifica la estimación de tokens para texto plano en español."""
    texto = "Este es un proyecto de prueba para medir tokens en ContextMap."
    tokens = contar_tokens_texto(texto, model_name="gpt-4o")
    assert tokens > 0
    assert 10 <= tokens <= 25


def test_contar_tokens_codigo_python() -> None:
    """Verifica que el tokenizador pondere adecuadamente los caracteres de sintaxis de código."""
    codigo = """def calcular_total(items: list[dict]) -> float:
    total = 0.0
    for item in items:
        total += item.get("precio", 0.0) * item.get("cantidad", 1)
    return total
"""
    tokens = contar_tokens_texto(codigo, model_name="claude-3-5-sonnet")
    assert tokens > 20


def test_token_counter_modelos_variados() -> None:
    """Verifica que la clase TokenCounter responda adecuadamente para distintos modelos."""
    texto = "Demostración de consistencia multi-modelo."
    counter_gpt = TokenCounter("gpt-4o")
    counter_claude = TokenCounter("claude-3-5-sonnet")
    counter_gemini = TokenCounter("gemini-1.5-pro")

    t1 = counter_gpt.count_tokens(texto)
    t2 = counter_claude.count_tokens(texto)
    t3 = counter_gemini.count_tokens(texto)

    assert t1 > 0
    assert t2 > 0
    assert t3 > 0

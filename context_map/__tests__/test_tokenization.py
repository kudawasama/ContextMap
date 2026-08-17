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
    """Verifica que la clase TokenCounter responda adecuadamente para distintos modelos principales."""
    texto = "Demostración de consistencia multi-modelo en ContextMap para desarrollo agéntico."
    modelos = [
        "gpt-4o",
        "gpt-4o-mini",
        "o1-mini",
        "claude-3-5-sonnet",
        "claude-3-5-haiku",
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-3.6-flash",
        "deepseek-r1",
        "deepseek-v3",
        "llama-3.1",
        "mistral-large",
    ]

    for model in modelos:
        counter = TokenCounter(model)
        tokens = counter.count_tokens(texto)
        assert tokens > 0, f"Error en modelo: {model}"
        assert 10 <= tokens <= 35, f"Rango fuera de lugar para: {model} ({tokens} tokens)"

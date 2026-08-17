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


def test_token_counter_catalogo_completo_2026() -> None:
    """Verifica que TokenCounter soporte el catálogo completo de modelos 2026."""
    texto = "Demostración de consistencia multi-modelo en ContextMap para desarrollo agéntico avanzado."
    
    # Catálogo completo de modelos probados
    modelos_2026 = [
        # OpenAI
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o1-mini",
        "o3-mini",
        # Google DeepMind
        "gemini-1.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-3.6-flash",
        "gemma-2-27b",
        # Anthropic
        "claude-3-5-sonnet",
        "claude-3-5-haiku",
        "claude-3-opus",
        # Meta AI
        "llama-3.3-70b",
        "llama-3.2-11b-vision",
        "llama-3.1-405b",
        # DeepSeek AI
        "deepseek-v3",
        "deepseek-r1",
        "deepseek-coder-v2",
        # Qwen / Alibaba
        "qwen-2.5-coder",
        "qwen-2.5-72b",
        # xAI
        "grok-3",
        "grok-2",
        # Mistral / Perplexity / Cohere
        "codestral",
        "mistral-large",
        "sonar-pro",
        "command-r-plus",
    ]

    for model in modelos_2026:
        counter = TokenCounter(model)
        tokens = counter.count_tokens(texto)
        assert tokens > 0, f"Error de cálculo en modelo: {model}"
        assert 10 <= tokens <= 35, f"Rango fuera de límite para: {model} ({tokens} tokens)"

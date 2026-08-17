"""Pruebas unitarias para el módulo de tokenización context_map.core.tokenization."""

import pytest
from context_map.core.tokenization import TokenCounter, contar_tokens_texto, normalize_model_name


def test_normalize_model_name() -> None:
    """Verifica la normalización de nombres de modelo con espacios y mayúsculas."""
    assert normalize_model_name("GPT 5.4 Mini") == "gpt-5.4-mini"
    assert normalize_model_name("Claude Opus 4.5") == "claude-opus-4.5"
    assert normalize_model_name("Gemini 3.7 Flash") == "gemini-3.7-flash"
    assert normalize_model_name("DeepSeek V4 Pro") == "deepseek-v4-pro"
    assert normalize_model_name("Nemotron 3.5 Lightning Free") == "nemotron-3.5-lightning-free"


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
    tokens = contar_tokens_texto(codigo, model_name="Claude Sonnet 5")
    assert tokens > 20


def test_token_counter_modelos_solicitados_usuario() -> None:
    """Verifica que TokenCounter soporte todos los modelos específicos provistos por el usuario."""
    texto = "Demostración de consistencia multi-modelo para la lista avanzada."

    modelos_solicitados = [
        "Big Pickle",
        "Claude Fable 5",
        "Claude Haiku 4.5",
        "Claude Opus 4.5",
        "Claude Opus 4.6",
        "Claude Opus 4.7",
        "Claude Opus 4.8",
        "Claude Opus 5",
        "Claude Sonnet 4",
        "Claude Sonnet 4.5",
        "Claude Sonnet 4.6",
        "Claude Sonnet 5",
        "GPT 5",
        "GPT 5 Codex",
        "GPT 5 Nano",
        "GPT 5.1",
        "GPT 5.1 Codex",
        "GPT 5.1 Codex Max",
        "GPT 5.1 Codex Mini",
        "GPT 5.2",
        "GPT 5.2 Codex",
        "GPT 5.3 Codex",
        "GPT 5.3 Codex Spark",
        "GPT 5.4",
        "GPT 5.4 Mini",
        "GPT 5.4 Nano",
        "GPT 5.4 Pro",
        "GPT 5.5",
        "GPT 5.5 Pro",
        "GPT 5.6 Luna",
        "GPT 5.6 Sol",
        "GPT 5.6 Terra",
        "Gemini 3 Flash",
        "Gemini 3.1 Pro",
        "Gemini 3.5 Flash",
        "Gemini 3.5 Flash Lite",
        "Gemini 3.6 Flash",
        "Gemini 3.7 Flash",
        "DeepSeek V4 Flash",
        "DeepSeek V4 Flash Free",
        "DeepSeek V4 Pro",
        "GLM 5",
        "GLM 5.1",
        "GLM 5.2",
        "Kimi K2.5",
        "Kimi K2.6",
        "Kimi K2.7 Code",
        "Kimi K3",
        "Qwen3.5 Plus",
        "Qwen3.6 Plus",
        "Grok 4.5",
        "Grok 4.6",
        "Grok Build 0.1",
        "MiniMax M2.5",
        "MiniMax M2.7",
        "MiniMax M3",
        "MiMo V2.5 Free",
        "Hy3 Free",
        "Laguna S 2.1 Free",
        "Muse Spark 1.2",
        "Nemotron 3 Ultra Free",
        "Nemotron 3.5 Lightning Free",
    ]

    for model in modelos_solicitados:
        counter = TokenCounter(model)
        tokens = counter.count_tokens(texto)
        assert tokens > 0, f"Error de cálculo en modelo: {model}"
        assert 8 <= tokens <= 35, f"Rango fuera de límite para: {model} ({tokens} tokens)"

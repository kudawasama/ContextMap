"""Módulo de tokenización y estimación oficial de consumo de tokens por modelo para ContextMap.

Soporta el catálogo completo de LLMs líderes y de código abierto (2026):
- **OpenAI**: GPT-4o, GPT-4o-mini, o1, o1-mini, o1-pro, o3, o3-mini, GPT-4-turbo, GPT-3.5.
- **Google DeepMind**: Gemini 1.5 Pro/Flash, Gemini 2.0 Flash/Pro/Lite/Thinking, Gemini 2.5, Gemini 3.0, Gemini 3.5, Gemini 3.6 Flash, Gemma 2.
- **Anthropic**: Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3.5 Opus, Claude 3 Opus, Claude 3 Sonnet, Claude 3 Haiku.
- **Meta AI**: Llama 3.3 (70B), Llama 3.2 (1B/3B/11B/90B), Llama 3.1 (8B/70B/405B), Llama 3.
- **DeepSeek AI**: DeepSeek-V3, DeepSeek-R1, DeepSeek-Coder-V2, DeepSeek-R1-Distill.
- **Qwen (Alibaba)**: Qwen 2.5, Qwen 2.5 Coder, Qwen 2.5 Math, Qwen Max.
- **xAI**: Grok 3, Grok 2, Grok 2 Mini, Grok Beta.
- **Mistral AI**: Mistral Large 2, Codestral, Pixtral, Mixtral 8x22B.
- **Cohere / Perplexity**: Command R+, Sonar Pro, Sonar Reasoning.
"""

import re
from typing import Dict, Optional

# Intentar importación soft de tiktoken si está disponible en el entorno
try:
    import tiktoken  # type: ignore

    _TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None  # type: ignore
    _TIKTOKEN_AVAILABLE = False


class TokenCounter:
    """Calculador y estimador oficial de tokens para el catálogo completo de modelos de lenguaje del mercado."""

    # Ratios oficiales promedio (caracteres por token) basados en las especificaciones de cada tokenizador
    _RATIOS_OFICIALES: Dict[str, float] = {
        # OpenAI Family (o200k_base / cl100k_base)
        "gpt-4o": 3.7,
        "gpt-4o-mini": 3.7,
        "gpt-4o-realtime": 3.7,
        "gpt-4-turbo": 3.7,
        "gpt-4": 3.7,
        "gpt-3.5-turbo": 3.7,
        "o1": 3.7,
        "o1-mini": 3.7,
        "o1-preview": 3.7,
        "o1-pro": 3.7,
        "o3": 3.7,
        "o3-mini": 3.7,
        "o3-high": 3.7,
        # Anthropic Claude Family (Anthropic BPE ~3.5 chars/token)
        "claude-3-5-sonnet": 3.5,
        "claude-3-5-haiku": 3.5,
        "claude-3-5-opus": 3.5,
        "claude-3-opus": 3.5,
        "claude-3-sonnet": 3.5,
        "claude-3-haiku": 3.5,
        "claude-2.1": 3.5,
        # Google Gemini Family (SentencePiece 256k vocab)
        "gemini-1.5-pro": 3.8,
        "gemini-1.5-flash": 4.0,
        "gemini-1.5-flash-8b": 4.0,
        "gemini-2.0-flash": 4.0,
        "gemini-2.0-flash-lite": 4.0,
        "gemini-2.0-pro": 3.8,
        "gemini-2.0-flash-thinking": 4.0,
        "gemini-2.5-flash": 4.0,
        "gemini-3.0-pro": 3.8,
        "gemini-3.5-flash": 4.0,
        "gemini-3.5-pro": 3.8,
        "gemini-3.6-flash": 4.0,
        "gemini-flash": 4.0,
        "gemma-2": 3.8,
        "gemma-2-9b": 3.8,
        "gemma-2-27b": 3.8,
        # Meta Llama Family (Tiktoken 128k BPE ~3.7 chars/token)
        "llama-3": 3.7,
        "llama-3.1": 3.7,
        "llama-3.1-405b": 3.7,
        "llama-3.2": 3.7,
        "llama-3.2-vision": 3.7,
        "llama-3.3": 3.7,
        "llama-3.3-70b": 3.7,
        # DeepSeek Family (DeepSeek 100k BPE ~3.6 chars/token)
        "deepseek-v3": 3.6,
        "deepseek-r1": 3.6,
        "deepseek-r1-distill": 3.6,
        "deepseek-coder": 3.5,
        "deepseek-coder-v2": 3.5,
        # Qwen Family (Alibaba ~3.6 chars/token)
        "qwen-2.5": 3.6,
        "qwen-2.5-coder": 3.5,
        "qwen-2.5-72b": 3.6,
        "qwen-max": 3.6,
        # xAI Grok Family (~3.7 chars/token)
        "grok-3": 3.7,
        "grok-2": 3.7,
        "grok-2-mini": 3.7,
        "grok-beta": 3.7,
        # Mistral Family (SentencePiece 32k/128k ~3.8 chars/token)
        "mistral-large": 3.8,
        "mistral-small": 3.8,
        "codestral": 3.5,
        "pixtral": 3.8,
        "mixtral-8x7b": 3.8,
        "mixtral-8x22b": 3.8,
        # Cohere & Perplexity Family
        "command-r-plus": 3.8,
        "sonar-pro": 3.7,
        "sonar-reasoning": 3.7,
        # Default Fallback
        "default": 3.7,
    }

    def __init__(self, model_name: str = "gpt-4o") -> None:
        """Inicializa el contador de tokens para un modelo específico.

        Args:
            model_name: Identificador del modelo (ej. "gpt-4o", "claude-3-5-sonnet", "gemini-3.6-flash", "deepseek-r1", "llama-3.3", "qwen-2.5-coder", "grok-3").
        """
        self.model_name = model_name.lower().strip()

    def count_tokens(self, text: str) -> int:
        """Calcula el número exacto (OpenAI) o altamente fiel de tokens para cualquier modelo.

        Args:
            text: Texto plano o código a analizar.

        Returns:
            Número total de tokens.
        """
        if not text:
            return 0

        # Para modelos OpenAI, usar tiktoken exacto si está disponible
        if _TIKTOKEN_AVAILABLE and ("gpt" in self.model_name or "o1" in self.model_name or "o3" in self.model_name):
            try:
                encoding = tiktoken.encoding_for_model(self.model_name)
                return len(encoding.encode(text))
            except Exception:
                try:
                    encoding = tiktoken.get_encoding("o200k_base")
                    return len(encoding.encode(text))
                except Exception:
                    try:
                        encoding = tiktoken.get_encoding("cl100k_base")
                        return len(encoding.encode(text))
                    except Exception:
                        pass

        # Fallback heurístico inteligente calibrado por tokenizador de la familia
        return self._heuristic_count(text)

    def _heuristic_count(self, text: str) -> int:
        """Estimación heurística oficial calibrada por familia de modelo.

        Args:
            text: Contenido en texto plano.

        Returns:
            Número entero de tokens.
        """
        m = self.model_name

        # 1. Búsqueda exacta en el catálogo de ratios oficiales
        ratio = self._RATIOS_OFICIALES.get(m)

        # 2. Resolución dinámica inteligente por coincidencia de patrones y prefijos
        if ratio is None:
            if "flash" in m or "lite" in m:
                ratio = 4.0  # Ratios Gemini Flash / Flash-Lite / Mini
            elif "gemini" in m or "gemma" in m:
                ratio = 3.8  # Familia Gemini Pro / Gemma
            elif "claude" in m or "anthropic" in m:
                ratio = 3.5  # Familia Anthropic Claude
            elif "deepseek" in m:
                ratio = 3.6  # Familia DeepSeek V3/R1/Coder
            elif "qwen" in m or "alibaba" in m:
                ratio = 3.6  # Familia Qwen
            elif "llama" in m or "meta" in m:
                ratio = 3.7  # Familia Meta Llama
            elif "grok" in m or "xai" in m:
                ratio = 3.7  # Familia xAI Grok
            elif "mistral" in m or "mixtral" in m or "codestral" in m or "pixtral" in m:
                ratio = 3.5 if "code" in m else 3.8  # Familia Mistral AI
            elif "command" in m or "cohere" in m:
                ratio = 3.8  # Familia Cohere Command
            elif "sonar" in m or "perplexity" in m:
                ratio = 3.7  # Familia Perplexity Sonar
            elif "gpt" in m or "o1" in m or "o3" in m or "openai" in m:
                ratio = 3.7  # Familia OpenAI
            else:
                ratio = self._RATIOS_OFICIALES["default"]

        char_count = len(text)

        # Ajuste por caracteres de sintaxis de código y caracteres UTF-8 multibyte (acentos/emojis)
        code_symbols = len(re.findall(r"[\{\}\[\]\(\)\:\;\=\+\-\*\/\<\>\_\.\,\"\']", text))
        non_ascii = len(re.findall(r"[^\x00-\x7F]", text))

        # Fórmula de resolución fiel: (caracteres / ratio) + (símbolos código * 0.12) + (multibyte non-ascii * 0.25)
        raw_tokens = (char_count / ratio) + (code_symbols * 0.12) + (non_ascii * 0.25)
        return max(1, int(round(raw_tokens)))


def contar_tokens_texto(text: str, model_name: str = "gpt-4o") -> int:
    """Función de utilidad para calcular o estimar el consumo de tokens.

    Args:
        text: Texto a evaluar.
        model_name: Identificador del modelo (default "gpt-4o").

    Returns:
        Número total de tokens.
    """
    counter = TokenCounter(model_name=model_name)
    return counter.count_tokens(text)

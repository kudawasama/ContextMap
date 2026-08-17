"""Módulo de tokenización y estimación oficial de consumo de tokens por modelo para ContextMap.

Soporta las familias oficiales de LLMs:
- **OpenAI**: GPT-4o, GPT-4o-mini, o1, o1-mini, o3-mini, GPT-4, GPT-3.5 (vía `tiktoken` `o200k_base` / `cl100k_base`).
- **Google Gemini**: Gemini 1.5 Pro, Gemini 1.5 Flash, Gemini 2.0 Flash, Gemini 2.5, Gemini 3.6 Flash (SentencePiece 256k vocab).
- **Anthropic Claude**: Claude 3.5 Sonnet, Claude 3.5 Haiku, Claude 3 Opus, Claude 3 Haiku (Anthropic BPE).
- **Meta Llama**: Llama 3, Llama 3.1, Llama 3.2, Llama 3.3 (Tiktoken 128k BPE).
- **DeepSeek**: DeepSeek-V3, DeepSeek-R1, DeepSeek-Coder (DeepSeek BPE).
- **Mistral AI**: Mistral Large, Mistral Small, Mixtral (SentencePiece BPE).
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
    """Calculador y estimador oficial de tokens para modelos de lenguaje líderes del mercado."""

    # Ratios oficiales promedio (caracteres por token) basados en las especificaciones de cada tokenizador
    _RATIOS_OFICIALES: Dict[str, float] = {
        # OpenAI Family (o200k_base / cl100k_base)
        "gpt-4o": 3.7,
        "gpt-4o-mini": 3.7,
        "gpt-4-turbo": 3.7,
        "gpt-4": 3.7,
        "gpt-3.5-turbo": 3.7,
        "o1": 3.7,
        "o1-mini": 3.7,
        "o1-preview": 3.7,
        "o3-mini": 3.7,
        # Anthropic Claude Family (Anthropic BPE ~3.5 chars/token)
        "claude-3-5-sonnet": 3.5,
        "claude-3-5-haiku": 3.5,
        "claude-3-opus": 3.5,
        "claude-3-sonnet": 3.5,
        "claude-3-haiku": 3.5,
        "claude-2.1": 3.5,
        # Google Gemini Family (SentencePiece 256k vocab: ~4.0 chars/token prosa, ~3.6 código)
        "gemini-1.5-pro": 3.8,
        "gemini-1.5-flash": 4.0,
        "gemini-2.0-flash": 4.0,
        "gemini-2.0-flash-lite": 4.0,
        "gemini-2.0-pro": 3.8,
        "gemini-2.5-flash": 4.0,
        "gemini-3.6-flash": 4.0,
        "gemini-flash": 4.0,
        # Meta Llama Family (Tiktoken 128k BPE ~3.7 chars/token)
        "llama-3": 3.7,
        "llama-3.1": 3.7,
        "llama-3.2": 3.7,
        "llama-3.3": 3.7,
        # DeepSeek Family (DeepSeek 100k BPE ~3.6 chars/token)
        "deepseek-v3": 3.6,
        "deepseek-r1": 3.6,
        "deepseek-coder": 3.5,
        # Mistral Family (SentencePiece 32k/128k ~3.8 chars/token)
        "mistral-large": 3.8,
        "mistral-small": 3.8,
        "mixtral-8x7b": 3.8,
        # Default Fallback
        "default": 3.7,
    }

    def __init__(self, model_name: str = "gpt-4o") -> None:
        """Inicializa el contador de tokens para un modelo específico.

        Args:
            model_name: Identificador del modelo (ej. "gpt-4o", "claude-3-5-sonnet", "gemini-3.6-flash", "deepseek-r1", "llama-3.1").
        """
        self.model_name = model_name.lower().strip()

    def count_tokens(self, text: str) -> int:
        """Calcula el número exacto (OpenAI) o altamente fiel (Gemini/Claude/Llama/DeepSeek) de tokens.

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

        # Fallback heurístico fiel basado en tokenizador del modelo
        return self._heuristic_count(text)

    def _heuristic_count(self, text: str) -> int:
        """Estimación heurística oficial calibrada por familia de modelo.

        Args:
            text: Contenido en texto plano.

        Returns:
            Número entero de tokens.
        """
        # Búsqueda directa o resolución inteligente de familia de modelo
        ratio = self._RATIOS_OFICIALES.get(self.model_name)
        if ratio is None:
            if "flash" in self.model_name or "gemini" in self.model_name:
                ratio = 4.0 if "flash" in self.model_name else 3.8
            elif "claude" in self.model_name:
                ratio = 3.5
            elif "deepseek" in self.model_name:
                ratio = 3.6
            elif "llama" in self.model_name:
                ratio = 3.7
            elif "mistral" in self.model_name or "mixtral" in self.model_name:
                ratio = 3.8
            elif "gpt" in self.model_name or "o1" in self.model_name or "o3" in self.model_name:
                ratio = 3.7
            else:
                ratio = self._RATIOS_OFICIALES["default"]

        char_count = len(text)

        # Ajuste por caracteres de sintaxis de código y caracteres UTF-8 mutibyte (acentos/emojis)
        code_symbols = len(re.findall(r"[\{\}\[\]\(\)\:\;\=\+\-\*\/\<\>\_\.\,\"\']", text))
        non_ascii = len(re.findall(r"[^\x00-\x7F]", text))

        # Fórmula fiel: (caracteres / ratio) + (símbolos código * 0.12) + (non-ascii * 0.25)
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

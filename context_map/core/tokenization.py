"""Módulo de tokenización y estimación de consumo de tokens por modelo para ContextMap.

Proporciona utilidades para calcular el número aproximado o exacto de tokens
que consume un texto o documento según el modelo de lenguaje de destino
(GPT-4o, Claude 3.5, Gemini 1.5).
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
    """Calculador y estimador de tokens para diversos modelos de lenguaje."""

    # Ratios promedio de caracteres por token para fallback heurístico
    _RATIOS_FALLBACK: Dict[str, float] = {
        "gpt-4o": 3.7,
        "claude-3-5-sonnet": 3.6,
        "gemini-1.5-pro": 3.8,
        "default": 3.7,
    }

    def __init__(self, model_name: str = "gpt-4o") -> None:
        """Inicializa el contador de tokens para un modelo específico.

        Args:
            model_name: Nombre del modelo ("gpt-4o", "claude-3-5-sonnet", "gemini-1.5-pro").
        """
        self.model_name = model_name.lower()

    def count_tokens(self, text: str) -> int:
        """Calcula o estima el número de tokens en un texto.

        Args:
            text: Texto plano a analizar.

        Returns:
            Número total de tokens estimados o exactos.
        """
        if not text:
            return 0

        # Intentar usar tiktoken si está disponible para modelos OpenAI
        if _TIKTOKEN_AVAILABLE and ("gpt" in self.model_name or "o1" in self.model_name or "o3" in self.model_name):
            try:
                encoding = tiktoken.encoding_for_model(self.model_name)
                return len(encoding.encode(text))
            except Exception:
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")
                    return len(encoding.encode(text))
                except Exception:
                    pass

        # Fallback heurístico inteligente (palabras + caracteres especiales)
        return self._heuristic_count(text)

    def _heuristic_count(self, text: str) -> int:
        """Estimación heurística precisa basada en tokens de código y prosa en español.

        Args:
            text: Contenido en texto plano.

        Returns:
            Número entero estimado de tokens.
        """
        ratio = self._RATIOS_FALLBACK.get(self.model_name, self._RATIOS_FALLBACK["default"])
        char_count = len(text)

        # Ajuste para bloques de código (los símbolos y puntuación aumentan el token count)
        code_symbol_count = len(re.findall(r"[\{\}\[\]\(\)\:\;\=\+\-\*\/\<\>\_\.\,\"]", text))
        
        # Base estimada por caracteres + ponderador de símbolos de sintaxis
        raw_tokens = (char_count / ratio) + (code_symbol_count * 0.15)
        return max(1, int(round(raw_tokens)))


def contar_tokens_texto(text: str, model_name: str = "gpt-4o") -> int:
    """Función de utilidad rápida para contar tokens de un texto.

    Args:
        text: Texto a evaluar.
        model_name: Identificador del modelo (default "gpt-4o").

    Returns:
        Número de tokens.
    """
    counter = TokenCounter(model_name=model_name)
    return counter.count_tokens(text)

"""Cliente de integración con Ollama Local para ContextMap.

Proporciona soporte de inferencia local sin costo para la generación de docstrings
y resúmenes con verificación previa de RAM y compatibilidad de hardware.
"""

import json
import os
import urllib.error
import urllib.request

from context_map.domain.health.hardware import evaluar_hardware_pc


def ollama_desactivado() -> bool:
    """True si el usuario ha desactivado explícitamente Ollama mediante entorno."""
    val = os.environ.get("CTXMAP_NO_OLLAMA", "").strip().lower()
    return val in ("1", "true", "yes", "on")


class OllamaLocalClient:
    """Cliente HTTP local para la API de Ollama (http://localhost:11434)."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model_name: str | None = None,
        opt_out: bool = False,
    ) -> None:
        """Inicializa el cliente de Ollama local.

        Args:
            host: URL base del servidor Ollama.
            model_name: Modelo preferido (opcional). Si es None, se usa la sugerencia del hardware.
            opt_out: Si es True, desactiva la conexión a Ollama forzando fallback local.
        """
        self.host = host.rstrip("/")
        self.opt_out = opt_out or ollama_desactivado()
        self.hardware = evaluar_hardware_pc()
        sugerido = model_name or self.hardware.modelo_recomendado
        self.model_name = self._resolver_modelo_instalado(sugerido)

    def _resolver_modelo_instalado(self, modelo_deseado: str) -> str:
        """Selecciona el modelo deseado si está instalado o hace fallback al mejor disponible.

        Args:
            modelo_deseado: Nombre del modelo preferido.

        Returns:
            Nombre del modelo final a utilizar.
        """
        if self.opt_out:
            return modelo_deseado

        instalados = self.listar_modelos_instalados()
        if not instalados:
            return modelo_deseado

        # Coincidencia exacta
        for m in instalados:
            if m.lower() == modelo_deseado.lower() or m.lower().startswith(modelo_deseado.lower()):
                return m

        # Fallback preferencial a modelos de código / ligeros
        for m in instalados:
            m_lower = m.lower()
            if any(k in m_lower for k in ["coder", "qwen", "llama", "deepseek", "phi", "mistral"]):
                return m

        return instalados[0]

    def esta_disponible(self) -> bool:
        """Comprueba si el servidor local de Ollama está activo y respondiendo.

        Returns:
            True si Ollama responde en localhost; False en caso contrario.
        """
        if self.opt_out or not self.hardware.es_apto_para_ollama:
            return False

        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def listar_modelos_instalados(self) -> list[str]:
        """Obtiene la lista de modelos de lenguaje instalados localmente en Ollama.

        Returns:
            Lista de nombres de modelos disponibles (ej. ["qwen2.5-coder:1.5b", "llama3.2:3b"]).
        """
        if self.opt_out:
            return []

        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return [item.get("name", "") for item in data.get("models", []) if item.get("name")]
        except Exception:
            return []

    def generar_docstring_funcion(self, nombre_funcion: str, codigo_funcion: str) -> str | None:
        """Genera un docstring formal en español técnico (Google Style) para una función.

        Args:
            nombre_funcion: Nombre de la función o método.
            codigo_funcion: Fragmento de código de la función.

        Returns:
            String con el docstring generado o None si falló/offline.
        """
        if not self.esta_disponible():
            return None

        prompt = (
            f"Escribe un docstring breve en español técnico (estilo Google Style) para la función '{nombre_funcion}'. "
            "Responde ÚNICAMENTE con el bloque del docstring delimitado por triples comillas. "
            "No incluyas explicaciones previas ni posteriores.\n\n"
            f"Código:\n{codigo_funcion[:1500]}"
        )

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 150},
        }

        try:
            url = f"{self.host}/api/generate"
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=body, headers={"Content-Type": "application/json"}, method="POST"
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                respuesta = data.get("response", "").strip()
                if respuesta:
                    return respuesta
        except Exception:
            pass

        return None

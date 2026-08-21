"""Pruebas unitarias para el módulo context_map.infrastructure.integrations.ollama."""

from context_map.infrastructure.integrations.ollama import OllamaLocalClient


def test_ollama_client_init() -> None:
    """Verifica la inicialización del cliente de Ollama local."""
    client = OllamaLocalClient()
    assert client.host == "http://localhost:11434"
    assert client.hardware is not None
    # Si no hay Ollama corriendo en el entorno de test, esta_disponible() debe retornar False sin lanzar excepción
    disponible = client.esta_disponible()
    assert isinstance(disponible, bool)

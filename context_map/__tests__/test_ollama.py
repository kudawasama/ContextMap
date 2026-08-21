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


def test_ollama_client_opt_out_parametro() -> None:
    """Verifica que el parámetro opt_out desactive inmediatamente el cliente."""
    client = OllamaLocalClient(opt_out=True)
    assert client.opt_out is True
    assert client.esta_disponible() is False
    assert client.listar_modelos_instalados() == []


def test_ollama_client_opt_out_entorno(monkeypatch) -> None:
    """Verifica que la variable de entorno CTXMAP_NO_OLLAMA desactive el cliente."""
    monkeypatch.setenv("CTXMAP_NO_OLLAMA", "1")
    client = OllamaLocalClient()
    assert client.opt_out is True
    assert client.esta_disponible() is False

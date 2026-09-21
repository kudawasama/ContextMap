"""Prueba de guardia de dependencias del extra ``mcp``.

FastMCP construye el modelo de salida de cada tool con
``create_model(nombre, result=<tipo>)``. pydantic 2.9.2 rechaza esa llamada con
``PydanticUserError: A non-annotated attribute was detected``, y como
``context_map/infrastructure/mcp_server.py`` registra sus tools al importarse,
el fallo tumbaba la recolección COMPLETA del suite (no solo los tests de MCP).

Este test fija el comportamiento del que depende el import, sin necesidad de
tener el paquete ``mcp`` instalado.
"""

from __future__ import annotations


def test_pydantic_soporta_create_model_con_tipo_desnudo() -> None:
    """``create_model(nombre, result=str)`` debe funcionar (pydantic >= 2.13)."""
    from pydantic import create_model

    modelo = create_model("SalidaDeTool", result=str)

    assert modelo(result="ok").result == "ok"


def test_mcp_server_se_importa_sin_error() -> None:
    """El módulo del servidor MCP se importa (registra sus tools al importarse)."""
    import pytest

    pytest.importorskip("mcp", reason="extra 'mcp' no instalado en este entorno")

    from context_map.infrastructure import mcp_server

    assert callable(mcp_server.refresh)
    assert callable(mcp_server.personal_query)

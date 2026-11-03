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


#: Inventario histórico de tools MCP. Se fija aquí para que un futuro
#: refactor (o un import olvidado) no haga desaparecer tools en silencio.
TOOLS_ESPERADAS = frozenset({
    "adapt",
    "build",
    "check",
    "context",
    "context_diff",
    "context_search",
    "doctor",
    "export",
    "import_chat",
    "import_git",
    "import_sessions",
    "install_hooks",
    "knowledge_inbox_add",
    "knowledge_inbox_list",
    "knowledge_inbox_move",
    "knowledge_ingest",
    "knowledge_purge",
    "knowledge_review_due",
    "knowledge_review_grade",
    "knowledge_wiki_ask",
    "knowledge_wiki_embeddings",
    "knowledge_wiki_ingest",
    "knowledge_wiki_lint",
    "knowledge_wiki_moc",
    "knowledge_wiki_query",
    "personal_panorama",
    "personal_query",
    "personal_repair",
    "personal_timeline",
    "refresh",
    "scan",
    "secret_exec",
    "secret_list",
})


def test_inventario_de_tools_completo() -> None:
    """El servidor expone exactamente las 33 tools del inventario histórico."""
    import asyncio

    import pytest

    pytest.importorskip("mcp", reason="extra 'mcp' no instalado en este entorno")

    from context_map.infrastructure import mcp_server

    registradas = {t.name for t in asyncio.run(mcp_server._fastmcp.list_tools())}

    assert registradas == TOOLS_ESPERADAS
    assert len(registradas) == 33

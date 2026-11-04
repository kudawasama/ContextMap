"""Servidor MCP de ContextMap.

Expone las herramientas de ctxmap como tools MCP (transporte stdio) para que
cualquier agente compatible con MCP (Hermes Agent, Claude Desktop, Cursor,
Windsurf...) las llame directamente como herramientas, sin shell:

- ``refresh``   — el flujo completo (scan + build preservando manuales + check)
- ``scan``      — escanear cambios del código
- ``build``     — regenerar vault + brief
- ``check``     — readiness + salud del vault
- ``import_git`` / ``import_chat`` / ``import_sessions`` — historia
- ``adapt``     — reglas por agente (AGENTS.md, CLAUDE.md, .cursorrules...)
- ``context``   — leer el CONTEXT.md (brief) del proyecto

Este módulo es la **fachada**: crea el servidor y reexporta las 33 tools, que
viven repartidas por dominio en ``context_map.infrastructure.mcp_tools``. Las
importaciones de abajo no son decorativas: importar cada grupo es lo que
registra sus tools en FastMCP, y el orden de importación es el orden en que el
servidor las publica.

Uso (desde la raíz de un proyecto): ``ctxmap mcp`` — el servidor queda a la
escucha en stdio; conéctalo como servidor MCP en tu agente (ej. en Hermes:

.. code-block:: yaml

    mcp_servers:
      ctxmap:
        command: "ctxmap"
        args: ["mcp"]
)
"""

from __future__ import annotations

from context_map.infrastructure.mcp_tools.base import (
    _ejecutar,
    _ejecutar_con_target,
    _fastmcp,
    _frase_maestra,
    _leer_brief,
    _leer_brief_min,
    _requiere_confirmacion,
    _seccion_brief,
    _target_abs,
    _tool,
)
from context_map.infrastructure.mcp_tools.conocimiento import (
    _vault_de,
    knowledge_inbox_add,
    knowledge_inbox_list,
    knowledge_inbox_move,
    knowledge_ingest,
    knowledge_purge,
    knowledge_review_due,
    knowledge_review_grade,
    knowledge_wiki_ask,
    knowledge_wiki_embeddings,
    knowledge_wiki_ingest,
    knowledge_wiki_lint,
    knowledge_wiki_moc,
    knowledge_wiki_query,
)
from context_map.infrastructure.mcp_tools.core import (
    adapt,
    build,
    check,
    context,
    context_diff,
    context_search,
    context_search_vault,
    doctor,
    export,
    import_chat,
    import_git,
    import_sessions,
    install_hooks,
    refresh,
    scan,
)
from context_map.infrastructure.mcp_tools.personal import (
    personal_panorama,
    personal_query,
    personal_repair,
    personal_timeline,
)
from context_map.infrastructure.mcp_tools.secretos import secret_exec, secret_list

__all__ = [
    "_ejecutar",
    "_ejecutar_con_target",
    "_fastmcp",
    "_frase_maestra",
    "_leer_brief",
    "_leer_brief_min",
    "_requiere_confirmacion",
    "_seccion_brief",
    "_target_abs",
    "_tool",
    "_vault_de",
    "adapt",
    "build",
    "check",
    "context",
    "context_diff",
    "context_search",
    "context_search_vault",
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
    "run",
    "scan",
    "secret_exec",
    "secret_list",
]


def run() -> None:
    """Arranca el servidor MCP en stdio (bloqueante)."""
    if _fastmcp is None:
        raise SystemExit("mcp no instalado. Ejecuta: pip install mcp  (o: uv pip install mcp)")
    # La frase se toma al arrancar y se borra del entorno: los hijos de
    # secret_exec no deben poder heredarla (ver _frase_maestra).
    _frase_maestra()
    _fastmcp.run()

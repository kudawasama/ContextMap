"""Tools del servidor MCP de ContextMap, agrupadas por dominio.

El módulo ``context_map.infrastructure.mcp_server`` era un único archivo de 1091
líneas con 33 tools. Aquí se reparten por territorio, sin cambiar nombres ni
comportamiento observable:

- ``base``: instancia FastMCP y utilidades compartidas (registro, ejecución,
  lectura del brief, validaciones de seguridad).
- ``core``: ciclo de vida del proyecto (refresh, scan, build, check, context,
  import_git/chat/sessions, adapt, export, doctor, install_hooks...).
- ``secretos``: baúl de secretos (listar y ejecutar comandos con credenciales).
- ``personal``: memoria personal multi-proyecto (consulta, panorama, timeline).
- ``conocimiento``: Second Brain (inbox, wiki, repaso y captura externa).

El orden de importación en ``mcp_server`` define el orden en que el servidor
registra las tools, así que se mantiene el orden histórico.
"""

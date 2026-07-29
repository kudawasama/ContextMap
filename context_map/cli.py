"""CLI principal de Context Map.

Este archivo es el punto de entrada principal. Toda la lógica reside en:
- context_map/application/cli/cli.py (parser)
- context_map/application/commands/ (comandos)
"""

from context_map.application.cli import main


"""
# --- Generar agentes ---
# ctxmap init            # Solo la primera vez
# ctxmap build --brief   # Actualiza CONTEXT.md y AGENTS.md

# --- Flujo normal ---
# ctxmap scan .
# ctxmap sync .
# ctxmap build
# ctxmap build --brief
"""


if __name__ == "__main__":
    main()

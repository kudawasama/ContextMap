"""CLI principal de Context Map.

Este archivo es el punto de entrada. Toda la lógica está en:
- context_map/application/cli.py (parser)
- context_map/application/commands/__init__.py (comandos)
"""

from context_map.application.cli import main

if __name__ == "__main__":
    main()

"""CLI principal de Context Map.

Este archivo es el punto de entrada principal. Toda la lógica reside en:
- context_map/application/cli/cli.py (parser)
- context_map/application/commands/ (comandos)
"""

from context_map.application.cli import main

if __name__ == "__main__":
    main()

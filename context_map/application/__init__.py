"""Capa de Aplicación de context_map.

Re-exporta la interfaz CLI y los comandos integrados.
"""

from context_map.application.cli import main, create_parser

__all__ = ["main", "create_parser"]

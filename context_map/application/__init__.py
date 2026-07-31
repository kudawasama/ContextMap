"""Capa de Aplicación de context_map.

Re-exporta la interfaz CLI y los comandos integrados.
"""

from __future__ import annotations

from context_map.application.cli import create_parser, main

__all__ = ["main", "create_parser"]

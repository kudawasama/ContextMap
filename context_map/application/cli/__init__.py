"""Submódulo CLI de aplicación."""

from __future__ import annotations

from context_map.application.cli.cli import main
from context_map.application.cli.parser import create_parser

__all__ = ["main", "create_parser"]

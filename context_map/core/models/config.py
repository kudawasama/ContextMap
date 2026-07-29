from __future__ import annotations

"""Modelo de configuración declarativa del proyecto para ContextMap."""

from dataclasses import dataclass, field
from typing import List, Set


@dataclass
class ContextMapConfig:
    """Configuración declarativa leída desde .contextmap.toml o pyproject.toml."""

    project_name: str = ""
    ignore_dirs: List[str] = field(default_factory=list)
    custom_tags: List[str] = field(default_factory=list)
    mode: str = "hierarchical"
    brief_enabled: bool = True
    quiet: bool = False

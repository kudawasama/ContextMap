"""Modelo de configuración declarativa del proyecto para ContextMap."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContextMapConfig:
    """Configuración declarativa leída desde .contextmap.toml o pyproject.toml."""

    project_name: str = ""
    ignore_dirs: list[str] = field(default_factory=list)
    custom_tags: list[str] = field(default_factory=list)
    mode: str = "hierarchical"
    brief_enabled: bool = True
    quiet: bool = False

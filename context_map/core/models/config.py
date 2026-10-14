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
    # Retención del historial de snapshots (incidente 2026-10-13: 148 GB en maps/HISTORY)
    max_snapshots: int = 20
    history_max_mb: int = 512
    history_min_free_mb: int = 512
    # Watcher: intervalo mínimo entre refrescos consecutivos
    watch_min_interval_s: int = 60

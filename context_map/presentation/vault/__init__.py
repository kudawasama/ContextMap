"""Submódulo de generación de vault Obsidian."""

from __future__ import annotations

from context_map.presentation.vault.templates import (
    STATUS_FOLDERS,
    TYPE_TO_FOLDER,
)
from context_map.presentation.vault.writer import (
    render_active_map,
    render_mermaid,
    render_obsidian_vault,
)

# Alias para mantener compatibilidad semántica
generar_vault_obsidian = render_obsidian_vault

__all__ = [
    "render_obsidian_vault",
    "generar_vault_obsidian",
    "render_active_map",
    "render_mermaid",
    "TYPE_TO_FOLDER",
    "STATUS_FOLDERS",
]

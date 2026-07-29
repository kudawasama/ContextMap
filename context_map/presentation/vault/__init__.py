"""Submódulo de generación de vault Obsidian."""

from context_map.presentation.vault.writer import (
    render_obsidian_vault,
    render_active_map,
    render_mermaid,
    TYPE_TO_FOLDER,
    STATUS_FOLDERS,
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

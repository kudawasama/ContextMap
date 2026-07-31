"""Capa de Presentación de context_map.

Re-exporta símbolos principales de los submódulos:
- `briefs`: Generación de CONTEXT.md.
- `vault`: Generación del Vault Obsidian (render_obsidian_vault).
"""

from __future__ import annotations

from context_map.presentation.briefs import generar_brief
from context_map.presentation.vault import (
    generar_vault_obsidian,
    render_obsidian_vault,
)

__all__ = [
    "generar_brief",
    "render_obsidian_vault",
    "generar_vault_obsidian",
]

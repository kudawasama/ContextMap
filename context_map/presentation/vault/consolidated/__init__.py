"""Renderizado de vaults consolidados y jerárquicos.

Este paquete implementa la generación de la estructura temática consolidada
y jerárquica del vault de Obsidian para consumo óptimo por agentes de IA.

Submódulos:
- common: Utilidades compartidas entre los dos modos de renderizado.
- consolidado: Modo consolidado (8 notas temáticas sintéticas).
- jerarquico: Modo jerárquico en árbol (secciones 1.0-6.0 y notas atómicas).
"""

from __future__ import annotations

from context_map.presentation.vault.consolidated.common import _extract_project_purpose
from context_map.presentation.vault.consolidated.consolidado import _render_consolidated_vault
from context_map.presentation.vault.consolidated.jerarquico import _render_hierarchical_vault

__all__ = [
    "_extract_project_purpose",
    "_render_consolidated_vault",
    "_render_hierarchical_vault",
]

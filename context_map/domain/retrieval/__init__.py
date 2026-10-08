"""Recuperación de contexto del proyecto (nodos + notas) para agentes."""

from __future__ import annotations

from context_map.domain.retrieval.busqueda import (
    buscar_contexto,
    formatear_resultados,
)

__all__ = ["buscar_contexto", "formatear_resultados"]

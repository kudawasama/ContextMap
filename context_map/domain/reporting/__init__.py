"""Submódulo de generación de reportes del dominio."""

from __future__ import annotations

from context_map.domain.reporting.reporter import (
    generar_semanal,
    guardar_reporte,
)

__all__ = [
    "generar_semanal",
    "guardar_reporte",
]

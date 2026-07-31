"""Submódulo de escaneo de código del dominio."""

from __future__ import annotations

from context_map.domain.scanning.scanner import (
    escanear_y_generar_eventos,
    guardar_eventos_escaneados,
)

__all__ = [
    "escanear_y_generar_eventos",
    "guardar_eventos_escaneados",
]

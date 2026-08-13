"""Submódulo personal: base de datos global consolidada y transportable."""

from __future__ import annotations

from context_map.core.personal.bd import (
    ENV_DB_PATH,
    FALLBACK_DIR,
    Decision,
    Leccion,
    PersonalDB,
    ResultadoBusqueda,
    resolver_ruta_bd,
)

__all__ = [
    "PersonalDB",
    "Leccion",
    "Decision",
    "ResultadoBusqueda",
    "resolver_ruta_bd",
    "FALLBACK_DIR",
    "ENV_DB_PATH",
]

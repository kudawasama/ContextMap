"""Mundo CONOCIMIENTO (PKM): captura, clasificación y wiki personal.

Re-exporta la lógica del inbox (Second Brain) que vive separada del mundo de
código (namespace ``knowledge`` vs ``code``).
"""

from __future__ import annotations

from context_map.domain.knowledge.inbox import (
    CATEGORIAS,
    DESTINOS,
    NS_CONOCIMIENTO,
    clasificar,
    crear_nota,
    leer_titulo,
    listar_notas,
    mover_nota,
    purgar,
    ruta_categoria,
    ruta_conocimiento,
)

__all__ = [
    "CATEGORIAS",
    "DESTINOS",
    "NS_CONOCIMIENTO",
    "clasificar",
    "crear_nota",
    "leer_titulo",
    "listar_notas",
    "mover_nota",
    "purgar",
    "ruta_categoria",
    "ruta_conocimiento",
]

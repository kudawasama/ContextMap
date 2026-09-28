"""Mundo CONOCIMIENTO (PKM): captura, clasificación y wiki personal.

Re-exporta la lógica del inbox (Second Brain) que vive separada del mundo de
código (namespace ``knowledge`` vs ``code``).
"""

from __future__ import annotations

from context_map.domain.knowledge.captura import (
    capturar,
    capturar_desde_url,
    descargar_html,
    descargar_transcripcion_youtube,
    html_a_markdown,
    vtt_a_texto,
)
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
from context_map.domain.knowledge.wiki import (
    consultar,
    ingresar,
    lint,
    ruta_entidades,
    ruta_resumenes,
    ruta_wiki,
)

__all__ = [
    "CATEGORIAS",
    "DESTINOS",
    "NS_CONOCIMIENTO",
    "capturar",
    "capturar_desde_url",
    "clasificar",
    "consultar",
    "crear_nota",
    "descargar_html",
    "descargar_transcripcion_youtube",
    "html_a_markdown",
    "ingresar",
    "leer_titulo",
    "lint",
    "listar_notas",
    "mover_nota",
    "purgar",
    "ruta_categoria",
    "ruta_conocimiento",
    "ruta_entidades",
    "ruta_resumenes",
    "ruta_wiki",
    "vtt_a_texto",
]

"""Construcción segura de wikilinks de Obsidian.

Obsidian delimita un enlace con ``[[`` … ``]]`` y separa destino y alias con
``|``. Un alias que contenga corchetes —por ejemplo el título de una idea
``[f51c772] feat: …``— cierra el enlace antes de tiempo: el Graph View pierde la
arista y el validador de topología (``topologia.py``) ya no ve el padre, así que
la nota aparece huérfana aunque su pie diga lo contrario.

Ese fue el origen de los ``SIN PADRE`` de los batches de ideas completadas: el
índice de concepto escribía ``[[01-GENERAL-01-01.md|[f51c772] feat: …]]`` y la
expresión regular de enlaces (``\\[\\[([^\\]]+)\\]\\]``) no podía casar nada.

Este módulo centraliza la construcción del enlace para que ningún renderizador
vuelva a interpolar un título a pelo.
"""

from __future__ import annotations

import re

#: Sustituciones para los caracteres que rompen un wikilink o confunden al
#: Graph View. Se busca legibilidad antes que fidelidad: el alias es texto
#: de presentación, nunca una ruta.
_SUSTITUCIONES = str.maketrans(
    {
        "[": "(",
        "]": ")",
        "|": "·",
        "#": "♯",
        "^": "",
        "\r": " ",
        "\n": " ",
        "\t": " ",
    }
)

_ESPACIOS = re.compile(r"\s{2,}")


def alias_seguro(texto: str | None, limite: int | None = None) -> str:
    """Devuelve un alias de wikilink sin caracteres que rompan el enlace.

    Args:
        texto (str | None): Título o texto de presentación del enlace.
        limite (int | None): Longitud máxima opcional; ``None`` no recorta.

    Returns:
        str: Alias de una sola línea, sin ``[``, ``]``, ``|``, ``#`` ni ``^``.
    """
    limpio = (texto or "").translate(_SUSTITUCIONES)
    limpio = _ESPACIOS.sub(" ", limpio).strip()
    if limite is not None and len(limpio) > limite:
        limpio = limpio[:limite].rstrip()
    return limpio


def destino_seguro(destino: str) -> str:
    """Normaliza el destino de un enlace: sin extensión ``.md`` y con ``/``.

    Args:
        destino (str): Ruta o nombre de nota, con o sin extensión.

    Returns:
        str: Destino listo para un wikilink de Obsidian.
    """
    limpio = (destino or "").strip().replace("\\", "/")
    if limpio.endswith(".md"):
        limpio = limpio[:-3]
    return limpio.strip("/")


def enlace(destino: str, alias: str | None = None, tabla: bool = False) -> str:
    """Construye un wikilink válido de Obsidian.

    Args:
        destino (str): Ruta o nombre único de la nota destino (con o sin ``.md``).
        alias (str | None): Texto visible; se sanea con :func:`alias_seguro`.
        tabla (bool): Si ``True`` escapa el separador (``\\|``), obligatorio
            dentro de una tabla Markdown para no romper las columnas.

    Returns:
        str: ``[[destino|alias]]`` o ``[[destino]]`` si no hay alias.
    """
    ruta = destino_seguro(destino)
    texto = alias_seguro(alias)
    if not texto:
        return f"[[{ruta}]]"
    separador = "\\|" if tabla else "|"
    return f"[[{ruta}{separador}{texto}]]"


__all__ = ["alias_seguro", "destino_seguro", "enlace"]

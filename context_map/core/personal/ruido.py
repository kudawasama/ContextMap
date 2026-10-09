"""Detección de eventos de ruido técnico para la BD personal.

Centraliza el criterio que decide si un evento es basura (falsos positivos del
extractor antiguo de TODO, cachés de despliegue, archivos del sistema). Lo usan:

- la **ingesta** (`sincronizar_proyecto_automatico`, `personal sync`) para no
  guardar ruido nuevo, y
- el **saneamiento** (`personal repair --purge-ruido`) para limpiar bases que ya
  lo contienen.

Al vivir en un único lugar, lo que se deja de ingerir es exactamente lo que la
purga elimina.
"""

from __future__ import annotations

import re

#: Marcador de TODO/FIXME real dentro de un comentario (no una mención suelta).
_MARCADOR_REAL = re.compile(r"(?:#|//|/\*|<!--|--)\s*(?:TODO|FIXME|HACK|XXX)\b", re.IGNORECASE)

#: Fragmentos de rutas vendorizadas o cachés de despliegue.
_PATRONES_TEXTO = (".vercel/", ".next/", "archive-v0/")

#: Archivos del sistema que algunos clientes siembran en cada carpeta.
_PATRONES_FUENTE = ("desktop.ini", "thumbs.db")


def es_evento_ruido(tipo: str, texto: str, fuente: str) -> bool:
    """Indica si un evento es ruido técnico que no aporta a la memoria.

    Criterios (los mismos que aplicaba la purga histórica):

    - Texto vacío o un simple ``[`` (restos de parseo).
    - Fuente de archivo de sistema (``desktop.ini``, ``thumbs.db``).
    - Rutas vendorizadas o cachés de despliegue (``.vercel/``, ``.next/``,
      ``archive-v0/``).
    - ``FUTURO`` cuyo texto dice ``TODO (...)`` pero cuyo cuerpo no contiene un
      marcador real en un comentario (falsos positivos del extractor antiguo).

    Args:
        tipo: Tipo del evento (p. ej. ``FUTURO``).
        texto: Contenido textual del evento.
        fuente: Fuente u origen del evento.

    Returns:
        bool: True si el evento debe descartarse.
    """
    t = texto or ""
    f = (fuente or "").lower()

    if t == "" or t == "[":
        return True
    if any(p in f for p in _PATRONES_FUENTE):
        return True

    tl = t.lower()
    if any(p in tl for p in _PATRONES_TEXTO):
        return True

    if (tipo or "").upper() == "FUTURO" and "TODO (" in t:
        cuerpo = t.split("):", 1)[-1] if "):" in t else t
        if not _MARCADOR_REAL.search(cuerpo):
            return True

    return False

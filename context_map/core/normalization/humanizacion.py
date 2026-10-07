"""Predicados de humanización: excluyen ruido del scanner de las notas narrativas.

El scanner y los importadores (chats/IDE, git, sesiones) generan eventos que son
útiles como *historia* pero **ensucian la narrativa** del vault: métricas
repetitivas ("Proyecto 'X' — N archivos"), TODOs crudos del código y mensajes de
conversación. Este módulo centraliza el criterio para que ``1.1``, ``1.3`` y
``2.4`` hablen del proyecto y no del proceso.

Uso típico::

    from context_map.core.normalization.humanizacion import es_ruido_narrativo

    nodos_legibles = [n for n in nodes if not es_ruido_narrativo(n)]
"""

from __future__ import annotations

import re

from context_map.core.models import Node

# Métrica repetitiva del scanner: "Proyecto 'X' — 275 archivos, 37683 líneas...".
_METRICA_SCAN = re.compile(
    r"^proyecto\s+['\"][^'\"]*['\"]\s*[—\-]\s*\d+\s*archivos",
    re.IGNORECASE,
)

# TODO/FIXME crudo del código: "TODO (context_map/foo.py:L10): ...".
_TODO_CRUDO = re.compile(r"^\s*(todo|fixme)\s*\(", re.IGNORECASE)

# Resúmenes plantilla que la ingesta repite sin aportar contenido propio.
_RESUMENES_PLANTILLA = (
    "este evento forma parte del mapa contextual",
    "idea o implementación relevante",
)

# Orígenes (campo ``source`` del nodo) que corresponden a conversaciones.
_FUENTES_CHAT = {"chat", "antigravity-ide"}

# Marcas que delatan mensajes de chat/IDE (no son contenido del proyecto).
_MARCAS_CHAT = (
    "◕‿◕",
    "commit + push",
    "binario~",
    "ahora actualizo el contexto",
    "ahora quiero que actualices",
)

# Entrypoints de directorios de trabajo/scratch: no son arquitectura del proyecto.
_RUTAS_DESCARTABLES = ("scratch", ".work", "/tmp/", "\\temp\\", "appdata")


def es_metrica_scan(n: Node) -> bool:
    """True si el nodo es una métrica repetitiva del scanner.

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True para títulos tipo ``Proyecto 'X' — N archivos``.
    """
    return bool(_METRICA_SCAN.match((n.title or "").strip()))


def es_todo_crudo(n: Node) -> bool:
    """True si el nodo es un TODO/FIXME crudo del código.

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True si el título empieza por ``TODO (`` o ``FIXME (``.
    """
    return bool(_TODO_CRUDO.match(n.title or ""))


def es_mensaje_chat(n: Node) -> bool:
    """True si el nodo proviene de una conversación/IDE y no del proyecto.

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True si ``source`` es de chat/IDE o el texto tiene marcas de chat.
    """
    if (n.source or "").strip().lower() in _FUENTES_CHAT:
        return True
    texto = f"{n.title or ''} {n.summary or ''}".lower()
    return any(marca in texto for marca in _MARCAS_CHAT)


def es_entrypoint_descartable(n: Node) -> bool:
    """True si el nodo es un entrypoint de un directorio de trabajo/scratch.

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True para entrypoints dentro de ``.work``/scratch/temp.
    """
    titulo = (n.title or "").lower()
    if not titulo.startswith("entrypoint:"):
        return False
    return any(marca in titulo for marca in _RUTAS_DESCARTABLES)


def es_resumen_plantilla(n: Node) -> bool:
    """True si el resumen es una plantilla repetida por la ingesta.

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True si el resumen empieza por una frase plantilla.
    """
    resumen = (n.summary or "").strip().lower()
    return any(resumen.startswith(p) or p in resumen[:90] for p in _RESUMENES_PLANTILLA)


def es_ruido_narrativo(n: Node) -> bool:
    """Predicado único de ruido para notas narrativas generadas.

    Combina métricas del scanner, TODOs crudos y mensajes de chat. NO incluye
    los resúmenes plantilla (esos solo se filtran en la identidad del 1.3).

    Args:
        n (Node): Nodo del mapa conceptual.

    Returns:
        bool: True si el nodo debe excluirse de narrativa/principios/diagrama.
    """
    return (
        es_metrica_scan(n)
        or es_todo_crudo(n)
        or es_mensaje_chat(n)
        or es_entrypoint_descartable(n)
    )

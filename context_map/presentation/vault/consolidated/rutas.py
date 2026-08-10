"""Resolución de rutas reales y conexiones semánticas del vault jerárquico.

Pieza clave del mapa mental conectado: dado un nodo, saber QUÉ archivo .md lo
materializa en el vault (para wikilinks sin nodos fantasma) y con qué otros
nodos se relaciona semánticamente (mismo concepto, misma fecha de ingreso,
menciones cruzadas).

Regla de oro: SOLO se devuelven rutas de archivos que el renderizador genera
realmente. Los nodos agrupados (BASE→3.1, FUTURO→5.1, CAMBIO/CORRECCION→6.1/6.2,
PRUEBA, DOCUMENTO) devuelven ``None`` — conectarlos crearía nodos fantasma.
"""

from __future__ import annotations

import re

from context_map.core.models import Node
from context_map.presentation.vault.templates import _safe_filename

# Misma lógica de nombre de archivo que secciones_ideas (DRY: importar helpers)
from context_map.presentation.vault.consolidated.secciones_ideas import (
    _accion_nodo,
    _concepto_nodo,
)


def _id_limpio(node: Node) -> str:
    """ID sanitizado para el nombre de archivo (igual criterio que secciones_ideas)."""
    return re.sub(r"[^a-zA-Z0-9_-]", "", node.id or "")[:40] or "sin-id"


def ruta_archivo_nodo(node: Node | None) -> str | None:
    """Ruta relativa (al vault) del archivo que materializa el nodo, o None.

    Args:
        node (Node | None): Nodo del mapa.

    Returns:
        str | None: Ruta tipo ``2.0-IDEAS/.../idea_X.md``, o None si el nodo
        se renderiza agrupado (sin archivo individual) o no existe.
    """
    if node is None:
        return None

    if node.type == "IDEA":
        concepto = _concepto_nodo(node)
        if node.status == "pendiente":
            return (
                f"2.0-IDEAS/2.1-Ideas-Pendientes/{concepto}/"
                f"idea_{_id_limpio(node)}_{_accion_nodo(node)}.md"
            )
        if node.status == "activo":
            return (
                f"2.0-IDEAS/2.2-Ideas-Futuras/{concepto}/"
                f"idea_{_id_limpio(node)}_{_accion_nodo(node)}.md"
            )
        if node.status == "completado":
            # Las completadas se agrupan en batches; el wikilink apunta al
            # índice de concepto (archivo real, sin nodo fantasma).
            return (
                f"2.0-IDEAS/2.3-Ideas-Completas-e-Implementadas/{concepto}/"
                f"{concepto}-Completas.md"
            )
        return None

    if node.type == "RIESGO":
        return f"4.0-RIESGOS/{_safe_filename(node.title)}.md"

    # Agrupados (BASE→3.1, FUTURO→5.1, CAMBIO/CORRECCION→6.1/6.2, PRUEBA,
    # DOCUMENTO, HITO): sin archivo individual → None para evitar fantasmas.
    return None


def conexiones_de_nodo(
    node: Node,
    todos: list[Node],
    limite: int = 5,
) -> list[Node]:
    """Nodos relacionados semánticamente con ``node`` (top-N, archivos reales).

    Scoring:
    - +3 mismo concepto técnico (ambos con concept).
    - +2 misma fecha de ingreso (``created_at[:10]`` igual — misma sesión).
    - +1 título del candidato aparece en el summary del nodo (o viceversa).

    Args:
        node (Node): Nodo base.
        todos (list[Node]): Todos los nodos del mapa.
        limite (int): Máximo de conexiones a devolver (default 5).

    Returns:
        list[Node]: Nodos relacionados, ordenados por score desc.
    """
    candidatos: list[tuple[int, str, Node]] = []
    base_concept = _concepto_nodo(node)
    base_fecha = (node.created_at or "")[:10]
    base_title = (node.title or "").lower()
    base_summary = (node.summary or "").lower()

    for otro in todos:
        if otro.id == node.id:
            continue
        if ruta_archivo_nodo(otro) is None:
            continue

        score = 0
        otro_concept = _concepto_nodo(otro)
        if base_concept and otro_concept and base_concept == otro_concept:
            score += 3
        if base_fecha and (otro.created_at or "")[:10] == base_fecha:
            score += 2
        otro_title = (otro.title or "").lower()
        if (otro_title and otro_title in base_summary) or (
            base_title and base_title in (otro.summary or "").lower()
        ):
            score += 1

        if score > 0:
            candidatos.append((score, (otro.created_at or ""), otro))

    # Orden: score desc, luego más reciente primero
    candidatos.sort(key=lambda t: -t[0])
    return [c[2] for c in candidatos[:limite]]

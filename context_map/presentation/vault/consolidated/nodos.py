"""Utilidades de clasificación y deduplicación de nodos del grafo de contexto."""

from __future__ import annotations

from context_map.core.models import Node


def _clasificar_nodos(nodes: list[Node]) -> dict[str, list[Node]]:
    """Clasifica los nodos del grafo según su tipo semántico.

    Args:
        nodes (list[Node]): Lista completa de nodos del mapa de contexto.

    Returns:
        dict[str, list[Node]]: Diccionario con listas de nodos agrupadas por
        tipo ('BASE', 'IDEA', 'RIESGO', 'CAMBIO', 'PRUEBA', 'FUTURO', 'HITO').
        CAMBIO agrupa también los nodos de tipo 'CORRECCION'.
    """
    return {
        "BASE": [n for n in nodes if n.type == "BASE"],
        "IDEA": [n for n in nodes if n.type == "IDEA"],
        "RIESGO": [n for n in nodes if n.type == "RIESGO"],
        "CAMBIO": [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")],
        "PRUEBA": [n for n in nodes if n.type == "PRUEBA"],
        "FUTURO": [n for n in nodes if n.type == "FUTURO"],
        "HITO": [n for n in nodes if n.type == "HITO"],
        "DOCUMENTO": [n for n in nodes if n.type == "DOCUMENTO"],
    }


def _mencion_nodo_en_lista(nodo: Node, vistos: set[str], clave_limite: int = 80) -> bool:
    """Verifica si un nodo ya fue incluido en el listado.

    Args:
        nodo (Node): Nodo a evaluar.
        vistos (set[str]): Conjunto de claves ya procesadas.
        clave_limite (int): Límite de caracteres para la clave de deduplicación.

    Returns:
        bool: True si el nodo ya fue procesado, False en caso contrario.
    """
    clave = nodo.title[:clave_limite]
    if clave in vistos:
        return True
    vistos.add(clave)
    return False

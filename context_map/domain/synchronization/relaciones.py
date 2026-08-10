"""Conexiones `relaciona` derivadas de la historia conversada.

Cuando un evento importado (chat, sesión, commit) menciona 2+ nodos del mapa,
se crea un edge ``relaciona`` entre ellos: el mapa mental conecta lo que la
conversación conectó.
"""

from __future__ import annotations

from context_map.core.models import Edge, Event, Node


def crear_edges_por_menciones(
    nodes: list[Node],
    edges: list[Edge],
    eventos: list[Event],
) -> list[Edge]:
    """Edges ``relaciona`` por menciones cruzadas en eventos.

    Para cada evento cuyo texto menciona 2+ títulos de nodos existentes, crea
    un edge ``relaciona`` entre el primero y los demás (estrella acotada).
    Deduplica por (source, target, kind) en ambas direcciones.

    Args:
        nodes (list[Node]): Nodos actuales del mapa.
        edges (list[Edge]): Aristas ya existentes.
        eventos (list[Event]): Eventos con su texto (chats, sesiones, git).

    Returns:
        list[Edge]: Nuevas aristas ``relaciona`` (no persistidas aún).
    """
    existentes: set[tuple[str, str, str]] = {
        (e.source, e.target, e.kind) for e in edges
    }

    idx: list[tuple[str, Node]] = []
    for n in nodes:
        titulo = (n.title or "").lower().strip()
        if len(titulo) >= 4:
            idx.append((titulo, n))

    nuevos: list[Edge] = []
    for ev in eventos:
        texto = (ev.text or "").lower()
        mencionados: list[Node] = []
        vistos: set[str] = set()
        for titulo, n in idx:
            if n.id in vistos:
                continue
            if titulo in texto:
                mencionados.append(n)
                vistos.add(n.id)
        if len(mencionados) >= 2:
            base = mencionados[0]
            for otro in mencionados[1:]:
                clave = (base.id, otro.id, "relaciona")
                clave_inv = (otro.id, base.id, "relaciona")
                if clave not in existentes and clave_inv not in existentes:
                    nuevos.append(Edge(
                        source=base.id,
                        target=otro.id,
                        kind="relaciona",
                        note=f"mencion cruzada en {ev.source or 'conversacion'}",
                    ))
                    existentes.add(clave)

    return nuevos

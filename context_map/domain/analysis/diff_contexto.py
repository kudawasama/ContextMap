"""Diff de contexto: qué cambió en el grafo entre dos estados (digests).

Base de la tool MCP ``context_diff``: permite que un agente vuelva a una sesión
y reciba **solo los nodos que cambiaron** desde un *digest* anterior, en vez de
releer el brief completo. El índice ``digest -> snapshot`` se guarda en
``.context-map/state/digest_index.json`` con retención (nada se borra del grafo).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from context_map.core.models import Node
from context_map.core.storage import nodes_to_digest

logger = logging.getLogger(__name__)

#: Cuántos digests recientes se recuerdan en el índice.
RETENCION_INDICE = 50


def digest_de(nodes: list[Node]) -> str:
    """Devuelve el digest del conjunto de nodos (huella agregada)."""
    return nodes_to_digest(nodes)


def snapshot_de_nodos(nodes: list[Node]) -> dict[str, dict[str, str]]:
    """Construye un snapshot ``{id: {fp, t}}`` del estado actual.

    ``fp`` es la huella por nodo (``updated_at|summary[:60]``, el mismo material
    que usa el digest agregado) y ``t`` el título legible.
    """
    return {
        n.id: {
            "fp": f"{n.updated_at or ''}|{(n.summary or '')[:60]}",
            "t": n.title or n.id,
        }
        for n in nodes
    }


def cargar_indice(path: str) -> dict[str, Any]:
    """Carga el índice ``digest -> snapshot`` (vacío si no existe o está roto)."""
    try:
        with open(path, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else {}
    except Exception as err:  # noqa: BLE001 — el índice es una caché
        logger.debug("No se pudo leer el índice de digests %s: %s", path, err)
        return {}


def guardar_indice(path: str, indice: dict[str, Any], retencion: int = RETENCION_INDICE) -> None:
    """Persiste el índice recortando a los ``retencion`` digests más recientes."""
    recortado = dict(list(indice.items())[-max(1, retencion) :])
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(recortado, f, ensure_ascii=False)
    except Exception as err:  # noqa: BLE001 — best-effort
        logger.debug("No se pudo guardar el índice de digests %s: %s", path, err)


def comparar(
    antes: dict[str, dict[str, str]],
    despues: dict[str, dict[str, str]],
) -> dict[str, list[str]]:
    """Compara dos snapshots y devuelve los títulos agregados/cambiados/eliminados."""
    agregados = [despues[i]["t"] for i in despues if i not in antes]
    eliminados = [antes[i]["t"] for i in antes if i not in despues]
    cambiados = [
        despues[i]["t"]
        for i in antes
        if i in despues and antes[i].get("fp") != despues[i].get("fp")
    ]
    return {"agregados": agregados, "cambiados": cambiados, "eliminados": eliminados}


def formatear_diff(
    since: str,
    digest: str,
    cambios: dict[str, list[str]],
    max_por_grupo: int = 20,
) -> str:
    """Formatea los cambios para devolverlos al agente de forma compacta."""
    if not any(cambios.values()):
        return f"Sin cambios de nodos desde {since} (digest actual {digest})."
    lineas = [f"Cambios desde {since} (digest actual {digest}):"]
    for clave, etiqueta in (("agregados", "+"), ("cambiados", "~"), ("eliminados", "-")):
        titulos = cambios[clave]
        if titulos:
            muestra = "; ".join(titulos[:max_por_grupo])
            extra = f" (+{len(titulos) - max_por_grupo} más)" if len(titulos) > max_por_grupo else ""
            lineas.append(f"{etiqueta} {len(titulos)}: {muestra}{extra}")
    return "\n".join(lineas)

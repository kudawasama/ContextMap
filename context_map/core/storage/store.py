from __future__ import annotations

"""Persistencia de `Node` y `Edge` en la carpeta `.context-map/`.

Maneja operaciones de lectura y escritura en formato JSONL con append atómico
para prevenir pérdida de eventos, generación de vistas legibles y creación de snapshots históricos.
"""

import hashlib
import json
import os
import re
import shutil
from datetime import datetime
from typing import Iterable, List, Optional, Set, Tuple

from context_map.core.models import Node, Edge


def _ensure(path: str) -> None:
    """Crea los directorios padres si no existen.

    Args:
        path (str): Ruta completa al archivo o directorio target.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)


def append_jsonl(path: str, records: Iterable[dict]) -> None:
    """Agrega registros serializados en formato JSONL con creación automática de carpetas.

    Args:
        path (str): Ruta del archivo JSONL.
        records (Iterable[dict]): Iterable de diccionarios a guardar.
    """
    _ensure(path)
    try:
        with open(path, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as err:
        raise OSError(f"Error al escribir en {path}: {err}") from err


def load_jsonl(path: str) -> List[dict]:
    """Lee un archivo JSONL y devuelve una lista de diccionarios, ignorando líneas corruptas.

    Args:
        path (str): Ruta del archivo JSONL.

    Returns:
        List[dict]: Registros JSON deserializados.
    """
    if not os.path.exists(path):
        return []
    out: List[dict] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        out.append(json.loads(line_str))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return out


def write_map(md: str, rel: str = "maps/ACTIVE.md") -> None:
    """Escribe el contenido Markdown del mapa activo en `.context-map/`.

    Args:
        md (str): Contenido Markdown del mapa conceptual.
        rel (str): Ruta relativa dentro de `.context-map/`.
    """
    base = os.path.join(".context-map", rel)
    _ensure(base)
    with open(base, "w", encoding="utf-8") as f:
        f.write(md)


def _generar_nombre_descriptivo(nodes: List[Node], edges: List[Edge]) -> str:
    """Genera un nombre descriptivo para los archivos de snapshot basado en su contenido.

    Args:
        nodes (List[Node]): Lista de nodos.
        edges (List[Edge]): Lista de aristas.

    Returns:
        str: Nombre descriptivo final finalizado en `.md`.
    """
    if not nodes:
        return "mapa-vacio.md"

    tipos: dict[str, int] = {}
    for n in nodes:
        tipos[n.type] = tipos.get(n.type, 0) + 1

    total = len(nodes)
    tipos_str = "-".join(sorted(tipos.keys())).lower()
    es_seed = all(n.source == "seed" for n in nodes)

    partes = []
    if es_seed:
        partes.append("mapa-inicial-seed")
    else:
        partes.append(f"{total}-nodos-{tipos_str}")

    if "RIESGO" in tipos:
        partes.append("con-riesgos")
    if "CAMBIO" in tipos:
        partes.append("con-cambios")
    if "PRUEBA" in tipos:
        partes.append("con-pruebas")

    nombre = "-".join(partes)
    nombre = re.sub(r"[^a-z0-9\-]", "", nombre)
    nombre = re.sub(r"-{2,}", "-", nombre).strip("-")
    return f"{nombre}.md"


def snapshot_map(
    from_rel: str = "maps/ACTIVE.md",
    name: Optional[str] = None,
    nodes: Optional[List[Node]] = None,
    edges: Optional[List[Edge]] = None,
) -> Optional[str]:
    """Guarda una copia de respaldo (snapshot) del mapa en `.context-map/maps/HISTORY/`.

    Args:
        from_rel (str): Origen relativo del mapa activo.
        name (Optional[str]): Nombre explícito para el snapshot.
        nodes (Optional[List[Node]]): Nodos del grafo.
        edges (Optional[List[Edge]]): Aristas del grafo.

    Returns:
        Optional[str]: Ruta completa del snapshot creado o None en caso de fallo.
    """
    src = os.path.join(".context-map", from_rel)
    if not os.path.exists(src):
        return None

    if name:
        out_name = name
    elif nodes is not None and edges is not None:
        out_name = _generar_nombre_descriptivo(nodes, edges)
    else:
        try:
            with open(src, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:8]
        except Exception:
            h = "00000000"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_name = f"{ts}-{h}.md"

    dst = os.path.join(".context-map", "maps", "HISTORY", out_name)
    if os.path.exists(dst):
        base_name = out_name.rsplit(".", 1)[0]
        contador = 2
        while os.path.exists(dst):
            dst = os.path.join(
                ".context-map", "maps", "HISTORY", f"{base_name}-{contador}.md"
            )
            contador += 1

    _ensure(dst)
    try:
        shutil.copy2(src, dst)
        return dst
    except Exception:
        return None


def nodes_to_digest(nodes: List[Node]) -> str:
    """Genera un md5 digest único para auditar cambios en el conjunto de nodos.

    Args:
        nodes (List[Node]): Lista de nodos.

    Returns:
        str: Huella md5 abreviada de 12 caracteres.
    """
    payload = "|".join(
        f"{n.id}:{n.updated_at}:{n.summary[:60]}" for n in sorted(nodes, key=lambda x: x.id)
    )
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:12]


def edges_dedup(edges: List[Edge]) -> List[Edge]:
    """Elimina aristas duplicadas preservando relaciones únicas.

    Args:
        edges (List[Edge]): Lista de aristas.

    Returns:
        List[Edge]: Lista de aristas desduplicadas.
    """
    seen: Set[Tuple[str, str, str, str]] = set()
    out: List[Edge] = []
    for e in edges:
        k = (e.source, e.target, e.kind, e.note)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

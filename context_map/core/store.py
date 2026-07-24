from __future__ import annotations

"""Persistencia de `Node` y `Edge` en `.context-map/`.
Lee y escribe JSONL con append atómico para no perder eventos.
También genera vistas legibles y snapshots históricos.
"""

import os
import json
import hashlib
import re
import shutil
from typing import Iterable, List, Optional

from context_map.core.models import Node, Edge


def _ensure(path: str) -> None:
    """Crea directorios padres si no existen."""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def append_jsonl(path: str, records: Iterable[dict]) -> None:
    """Agrega registros a un JSONL, creando directorio si hace falta."""
    _ensure(path)
    with open(path, "a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def load_jsonl(path: str) -> List[dict]:
    """Lee un JSONL y tolera líneas inválidas."""
    if not os.path.exists(path):
        return []
    out: List[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def write_map(md: str, rel: str = "maps/ACTIVE.md") -> None:
    """Escribe el Markdown del mapa activo."""
    base = os.path.join(".context-map", rel)
    _ensure(base)
    with open(base, "w", encoding="utf-8") as f:
        f.write(md)


def _generar_nombre_descriptivo(nodes: List[Node], edges: List[Edge]) -> str:
    """Genera nombre de archivo descriptivo basado en el contenido del mapa.

    Ejemplos de salida:
    - "mapa-inicial-seed.md"
    - "3-nodos-base-idea-cambio.md"
    - "mapa-con-riesgos-y-4-nodos.md"
    """
    if not nodes:
        return "mapa-vacio.md"

    # Contar nodos por tipo
    tipos = {}
    for n in nodes:
        tipos[n.type] = tipos.get(n.type, 0) + 1

    total = len(nodes)
    tipos_str = "-".join(sorted(tipos.keys())).lower()

    # Detectar si es solo seed (todos de source="seed")
    es_seed = all(n.source == "seed" for n in nodes)

    # Detectar riesgos
    tiene_riesgos = "RIESGO" in tipos
    tiene_cambios = "CAMBIO" in tipos
    tiene_pruebas = "PRUEBA" in tipos

    partes = []
    if es_seed:
        partes.append("mapa-inicial-seed")
    else:
        partes.append(f"{total}-nodos-{tipos_str}")

    if tiene_riesgos:
        partes.append("con-riesgos")
    if tiene_cambios:
        partes.append("con-cambios")
    if tiene_pruebas:
        partes.append("con-pruebas")

    nombre = "-".join(partes)

    # Limpiar: solo minusculas, numeros, guiones
    nombre = re.sub(r"[^a-z0-9\-]", "", nombre)
    # Evitar guiones dobles
    nombre = re.sub(r"-{2,}", "-", nombre)
    nombre = nombre.strip("-")

    return f"{nombre}.md"


def snapshot_map(
    from_rel: str = "maps/ACTIVE.md",
    name: Optional[str] = None,
    nodes: Optional[List[Node]] = None,
    edges: Optional[List[Edge]] = None,
) -> Optional[str]:
    """Copia ACTIVE.md a HISTORY con nombre descriptivo.

    Si se provee `name`, se usa ese nombre. Si no, se genera uno
    descriptivo basado en los nodos y aristas del mapa.
    Si no falla, devuelve la ruta del snapshot; de lo contrario, None.
    """
    src = os.path.join(".context-map", from_rel)
    if not os.path.exists(src):
        return None

    if name:
        out_name = name
    elif nodes is not None and edges is not None:
        out_name = _generar_nombre_descriptivo(nodes, edges)
    else:
        h = hashlib.md5(open(src, "rb").read()).hexdigest()[:8]
        from datetime import datetime
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_name = f"{ts}-{h}.md"

    # Evitar sobrescribir: agregar sufijo numerico si ya existe
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
    shutil.copy2(src, dst)
    return dst


def nodes_to_digest(nodes: List[Node]) -> str:
    """Huella simple del set de nodos para cambios o auditoria."""
    payload = "|".join(
        f"{n.id}:{n.updated_at}:{n.summary[:60]}" for n in sorted(nodes, key=lambda x: x.id)
    )
    return hashlib.md5(payload.encode()).hexdigest()[:12]


def edges_dedup(edges: List[Edge]) -> List[Edge]:
    """Elimina aristas duplicadas por clave compuesta."""
    seen = set()
    out: List[Edge] = []
    for e in edges:
        k = (e.source, e.target, e.kind, e.note)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

"""Persistencia de `Node` y `Edge` en la carpeta `.context-map/`.


Maneja operaciones de lectura y escritura en formato JSONL con append atómico
para prevenir pérdida de eventos, generación de vistas legibles y creación de snapshots históricos.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
from collections.abc import Iterable
from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.core.storage.config_loader import load_project_config
from context_map.core.storage.history import (
    HISTORY_DIR,
    es_duplicado,
    espacio_libre_mb,
    hay_espacio,
    huella_archivo,
    podar,
)

logger = logging.getLogger(__name__)


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


def load_jsonl(path: str) -> list[dict]:
    """Lee un archivo JSONL y devuelve una lista de diccionarios, ignorando líneas corruptas.

    Args:
        path (str): Ruta del archivo JSONL.

    Returns:
        List[dict]: Registros JSON deserializados.
    """
    if not os.path.exists(path):
        return []
    out: list[dict] = []
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        out.append(json.loads(line_str))
                    except json.JSONDecodeError as err:
                        logger.debug("Línea JSON inválida ignorada en %s: %s", path, err)
    except Exception as err:
        logger.warning("No se pudo leer el archivo JSONL %s: %s", path, err)
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


def _generar_nombre_descriptivo(nodes: list[Node], edges: list[Edge]) -> str:
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
    name: str | None = None,
    nodes: list[Node] | None = None,
    edges: list[Edge] | None = None,
    keep: int | None = None,
    max_mb: int | None = None,
    min_free_mb: int | None = None,
) -> str | None:
    """Guarda una copia de respaldo (snapshot) del mapa en `.context-map/maps/HISTORY/`.

    Guardas añadidas tras el incidente 2026-10-13 (148 GB acumulados en el
    historial): nunca escribe si quedan menos de ``min_free_mb`` MB libres,
    nunca duplica un contenido idéntico al último snapshot y poda el historial a
    ``keep`` elementos / ``max_mb`` MB. Las colisiones de nombre se resuelven con
    marca temporal (y huella de contenido como desempate), sin series ``-2..-N``
    sin cota.

    Args:
        from_rel (str): Origen relativo del mapa activo.
        name (Optional[str]): Nombre explícito para el snapshot.
        nodes (Optional[List[Node]]): Nodos del grafo.
        edges (Optional[List[Edge]]): Aristas del grafo.
        keep (Optional[int]): Snapshots a conservar (default: configuración).
        max_mb (Optional[int]): Tope de tamaño del historial en MB.
        min_free_mb (Optional[int]): Espacio libre mínimo exigido en MB.

    Returns:
        Optional[str]: Ruta completa del snapshot creado o None si se omitió.
    """
    cfg = load_project_config(".")
    keep = cfg.max_snapshots if keep is None else keep
    max_mb = cfg.history_max_mb if max_mb is None else max_mb
    min_free_mb = cfg.history_min_free_mb if min_free_mb is None else min_free_mb

    src = os.path.join(".context-map", from_rel)
    if not os.path.exists(src):
        return None

    # Guarda 1 — disco: jamás escribir con el sistema al borde del colapso.
    if not hay_espacio(".", min_free_mb=min_free_mb):
        logger.warning(
            "Snapshot omitido: solo %.0f MB libres (mínimo %s MB). Revisa maps/HISTORY",
            espacio_libre_mb("."),
            min_free_mb,
        )
        return None

    # Guarda 2 — contenido idéntico al último snapshot: no aporta historial.
    if es_duplicado(src, HISTORY_DIR):
        logger.info(
            "Snapshot omitido: contenido idéntico al último snapshot de %s", HISTORY_DIR
        )
        return None

    if name:
        out_name = name
    elif nodes is not None and edges is not None:
        out_name = _generar_nombre_descriptivo(nodes, edges)
    else:
        try:
            with open(src, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()[:8]
        except Exception as err:
            logger.warning("No se pudo calcular hash del snapshot %s: %s", src, err)
            h = "00000000"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_name = f"{ts}-{h}.md"

    dst = os.path.join(HISTORY_DIR, out_name)
    if os.path.exists(dst):
        base_name, ext = os.path.splitext(out_name)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = os.path.join(HISTORY_DIR, f"{base_name}-{ts}{ext}")
        if os.path.exists(dst):  # misma marca temporal: desempata por contenido
            dst = os.path.join(
                HISTORY_DIR, f"{base_name}-{ts}-{huella_archivo(src) or 'na'}{ext}"
            )

    _ensure(dst)
    try:
        shutil.copy2(src, dst)
    except Exception as err:
        logger.warning("No se pudo crear snapshot %s: %s", dst, err)
        return None

    # Guarda 3 — retención: el historial no puede crecer sin cota.
    res = podar(HISTORY_DIR, keep=int(keep), max_mb=int(max_mb))
    if res.borrados:
        logger.info(
            "Historial podado: %d snapshots eliminados (%.2f MB liberados), %d restantes",
            len(res.borrados),
            res.liberado_mb,
            res.restantes,
        )
    return dst


def nodes_to_digest(nodes: list[Node]) -> str:
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


def edges_dedup(edges: list[Edge]) -> list[Edge]:
    """Elimina aristas duplicadas preservando relaciones únicas.

    Args:
        edges (List[Edge]): Lista de aristas.

    Returns:
        List[Edge]: Lista de aristas desduplicadas.
    """
    seen: set[tuple[str, str, str, str]] = set()
    out: list[Edge] = []
    for e in edges:
        k = (e.source, e.target, e.kind, e.note)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out

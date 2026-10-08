"""Persistencia de `Node` y `Edge` en la carpeta `.context-map/`.


Maneja operaciones de lectura y escritura en formato JSONL con append atómico
para prevenir pérdida de eventos, generación de vistas legibles y creación de snapshots históricos.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
from collections.abc import Iterable
from datetime import datetime

from context_map.core.models import Edge, Node

logger = logging.getLogger(__name__)


def _ensure(path: str) -> None:
    """Crea los directorios padres si no existen.

    Args:
        path (str): Ruta completa al archivo o directorio target.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)


# --- Retención de snapshots (plan de revisión 2026-10-08) -------------------
# El historial creaba un snapshot en CADA build: 482 ficheros y 52 MB (93% del
# peso de .context-map) con el grafo en 0,3 MB. Se conserva el detalle reciente
# y lo antiguo se ARCHIVA comprimido (nada se borra salvo que se pida).
SNAPSHOT_KEEP_DEFAULT = 20
SNAPSHOT_KEEP_DAYS_DEFAULT = 7


def _hash_contenido(ruta: str) -> str:
    """md5 del contenido de un fichero (cadena vacía si no se puede leer)."""
    try:
        with open(ruta, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return ""


def _listar_snapshots(history_dir: str) -> list[str]:
    """Rutas de los snapshots (``*.md``) del historial, sin entrar en subcarpetas."""
    if not os.path.isdir(history_dir):
        return []
    return [
        os.path.join(history_dir, nombre)
        for nombre in os.listdir(history_dir)
        if nombre.endswith(".md") and os.path.isfile(os.path.join(history_dir, nombre))
    ]


def purgar_snapshots(
    history_dir: str,
    *,
    keep: int | None = None,
    keep_days: int | None = None,
    archivar: bool | None = None,
) -> dict[str, object]:
    """Poda el historial de snapshots conservando lo reciente y archivando el resto.

    Se conservan intactos los ``keep`` más recientes **y** el más reciente de cada
    uno de los últimos ``keep_days`` días; lo demás se comprime en un ``.tar.gz``
    dentro de ``maps/archive/`` (nada se pierde).

    Configurable por entorno: ``CTXMAP_SNAPSHOT_KEEP`` (20),
    ``CTXMAP_SNAPSHOT_KEEP_DAYS`` (7) y ``CTXMAP_SNAPSHOT_ARCHIVE`` (``0`` para
    borrar en vez de archivar).

    Args:
        history_dir (str): Carpeta ``maps/HISTORY``.
        keep (int | None): Snapshots recientes a conservar.
        keep_days (int | None): Días (uno por día) a conservar.
        archivar (bool | None): Archivar (True) o borrar (False) los sobrantes.

    Returns:
        dict[str, object]: ``conservados``, ``archivados``, ``eliminados`` y
        ``archivo`` (ruta del tar.gz creado, si lo hubo).
    """
    if keep is None:
        keep = int(os.environ.get("CTXMAP_SNAPSHOT_KEEP", SNAPSHOT_KEEP_DEFAULT) or 0)
    if keep_days is None:
        keep_days = int(os.environ.get("CTXMAP_SNAPSHOT_KEEP_DAYS", SNAPSHOT_KEEP_DAYS_DEFAULT) or 0)
    if archivar is None:
        archivar = os.environ.get("CTXMAP_SNAPSHOT_ARCHIVE", "1") != "0"

    archivos = _listar_snapshots(history_dir)
    resultado: dict[str, object] = {
        "conservados": len(archivos), "archivados": 0, "eliminados": 0, "archivo": "",
    }
    if not archivos or (keep <= 0 and keep_days <= 0):
        return resultado

    orden = sorted(archivos, key=os.path.getmtime, reverse=True)
    proteger = set(orden[:keep])
    dias_vistos: set[str] = set()
    for ruta in orden:
        dia = datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%Y-%m-%d")
        if dia in dias_vistos:
            continue
        dias_vistos.add(dia)
        if len(dias_vistos) <= keep_days:
            proteger.add(ruta)

    sobrantes = [r for r in orden if r not in proteger]
    if not sobrantes:
        return resultado

    archivo_tar = ""
    if archivar:
        import tarfile

        carpeta = os.path.join(os.path.dirname(history_dir), "archive")
        os.makedirs(carpeta, exist_ok=True)
        # Un tar POR MES que se completa: así no se acumulan cientos de tars
        # minúsculos (una poda por build crearía uno cada vez).
        archivo_tar = os.path.join(carpeta, f"{datetime.now().strftime('%Y-%m')}.tar.gz")
        temporal = archivo_tar + ".tmp"
        try:
            ya_dentro: set[str] = set()
            with tarfile.open(temporal, "w:gz") as destino:
                if os.path.exists(archivo_tar):
                    with tarfile.open(archivo_tar, "r:gz") as previo:
                        for miembro in previo.getmembers():
                            contenido = previo.extractfile(miembro)
                            if contenido is None:
                                continue
                            destino.addfile(miembro, contenido)
                            ya_dentro.add(miembro.name)
                for ruta in sobrantes:
                    nombre = os.path.basename(ruta)
                    if nombre in ya_dentro:
                        continue
                    destino.add(ruta, arcname=nombre)
                    ya_dentro.add(nombre)
            os.replace(temporal, archivo_tar)  # atómico
        except Exception as err:  # noqa: BLE001 — si falla el archivado, NO se borra nada
            logger.warning("No se pudo archivar snapshots: %s", err)
            with contextlib.suppress(OSError):
                os.remove(temporal)
            return resultado

    eliminados = 0
    for ruta in sobrantes:
        try:
            os.remove(ruta)
            eliminados += 1
        except OSError as err:
            logger.warning("No se pudo podar %s: %s", ruta, err)

    resultado.update({
        "conservados": len(archivos) - eliminados,
        "archivados": eliminados if archivar else 0,
        "eliminados": 0 if archivar else eliminados,
        "archivo": archivo_tar,
    })
    if eliminados:
        logger.info("Snapshots podados: %s (%s)", eliminados, archivo_tar or "borrados")
    return resultado


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
) -> str | None:
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

    history_dir = os.path.join(".context-map", "maps", "HISTORY")
    hash_src = _hash_contenido(src)

    # Idempotencia (plan de revisión 2026-10-08): si el mapa no cambió desde el
    # último snapshot, no se crea otro (evita 482 copias idénticas y 52 MB).
    existentes = sorted(_listar_snapshots(history_dir), key=os.path.getmtime, reverse=True)
    if existentes and hash_src and _hash_contenido(existentes[0]) == hash_src:
        # El mapa no cambió: no se duplica, pero el historial puede estar gordo
        # (la retención debe aplicarse también en este camino).
        purgar_snapshots(history_dir)
        return existentes[0]

    if name:
        out_name = name
    elif nodes is not None and edges is not None:
        out_name = _generar_nombre_descriptivo(nodes, edges)
    else:
        h = hash_src[:8] or "00000000"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_name = f"{ts}-{h}.md"

    dst = os.path.join(history_dir, out_name)
    if os.path.exists(dst):
        base_name = out_name.rsplit(".", 1)[0]
        contador = 2
        while os.path.exists(dst):
            dst = os.path.join(history_dir, f"{base_name}-{contador}.md")
            contador += 1

    _ensure(dst)
    try:
        shutil.copy2(src, dst)
    except Exception as err:
        logger.warning("No se pudo crear snapshot %s: %s", dst, err)
        return None

    # Retención: conserva lo reciente y archiva el resto comprimido.
    purgar_snapshots(history_dir)
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

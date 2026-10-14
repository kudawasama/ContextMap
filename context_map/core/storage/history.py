"""Gestión del historial de snapshots (`.context-map/maps/HISTORY/`).

Motivo (incidente 2026-10-13): `snapshot_map` copiaba el mapa completo en cada
`build`/`refresh` sin límite de cantidad ni de tamaño, sin deduplicado por
contenido y sin comprobar el espacio libre. Con `ctxmap watch` sobre un árbol
multi-proyecto con escrituras externas constantes el historial alcanzó
103.354 archivos / 148 GB y llenó la raíz del servidor.

Este módulo centraliza: métricas del historial, huella de contenido, poda por
cantidad y por tamaño, y comprobación de espacio libre. No importa nada de
`context_map.application` para no invertir las capas.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HISTORY_DIR: str = os.path.join(".context-map", "maps", "HISTORY")
KEEP_DEFAULT: int = 20
MAX_MB_DEFAULT: int = 512
MIN_FREE_MB_DEFAULT: int = 512


@dataclass
class HistoryStats:
    """Métricas del directorio de historial.

    Attributes:
        files (int): Cantidad de snapshots `.md`.
        bytes (int): Tamaño total en bytes.
    """

    files: int = 0
    bytes: int = 0

    @property
    def mb(self) -> float:
        """Tamaño total en megabytes (2 decimales)."""
        return round(self.bytes / (1024 * 1024), 2)


@dataclass
class PodaResult:
    """Resultado de una poda del historial.

    Attributes:
        borrados (List[str]): Rutas eliminadas (o que se eliminarían con dry-run).
        liberado_bytes (int): Bytes liberados.
        restantes (int): Snapshots que quedan tras la poda.
    """

    borrados: list[str] = field(default_factory=list)
    liberado_bytes: int = 0
    restantes: int = 0

    @property
    def liberado_mb(self) -> float:
        """Bytes liberados expresados en megabytes (2 decimales)."""
        return round(self.liberado_bytes / (1024 * 1024), 2)


def _snapshots(history_dir: str) -> list[tuple[float, int, str]]:
    """Lista los snapshots del historial ordenados del más nuevo al más viejo.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        List[Tuple[float, int, str]]: Tuplas `(mtime, tamaño, ruta)`.
    """
    if not os.path.isdir(history_dir):
        return []
    items: list[tuple[float, int, str]] = []
    with os.scandir(history_dir) as entradas:
        for entrada in entradas:
            if not entrada.is_file() or not entrada.name.endswith(".md"):
                continue
            try:
                st = entrada.stat()
            except OSError as err:  # carrera con la poda u otro proceso
                logger.debug("Snapshot ilegible %s: %s", entrada.path, err)
                continue
            items.append((st.st_mtime, st.st_size, entrada.path))
    items.sort(key=lambda t: t[0], reverse=True)
    return items


def estadisticas(history_dir: str = HISTORY_DIR) -> HistoryStats:
    """Calcula cantidad de snapshots y tamaño total del historial.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        HistoryStats: Métricas consolidadas.
    """
    items = _snapshots(history_dir)
    return HistoryStats(files=len(items), bytes=sum(size for _, size, _ in items))


def huella_archivo(path: str) -> str:
    """Calcula la huella MD5 truncada (12 hex) del contenido de un archivo.

    Args:
        path (str): Ruta del archivo.

    Returns:
        str: Huella hexadecimal de 12 caracteres, o cadena vacía si falla.
    """
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    except OSError as err:
        logger.warning("No se pudo calcular la huella de %s: %s", path, err)
        return ""


def huella_ultimo_snapshot(history_dir: str = HISTORY_DIR) -> str | None:
    """Devuelve la huella del snapshot más reciente.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        Optional[str]: Huella del último snapshot o None si no hay historial.
    """
    items = _snapshots(history_dir)
    if not items:
        return None
    return huella_archivo(items[0][2]) or None


def es_duplicado(src: str, history_dir: str = HISTORY_DIR) -> bool:
    """Indica si `src` tiene el mismo contenido que el último snapshot.

    Args:
        src (str): Ruta del mapa activo que se pretende copiar.
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        bool: True si el contenido coincide con el último snapshot.
    """
    ultimo = huella_ultimo_snapshot(history_dir)
    if not ultimo:
        return False
    return huella_archivo(src) == ultimo


def espacio_libre_mb(path: str = ".") -> float:
    """Espacio libre del sistema de archivos que contiene `path`.

    Args:
        path (str): Ruta dentro del sistema de archivos a consultar.

    Returns:
        float: Megabytes libres (0.0 si la consulta falla).
    """
    try:
        uso = shutil.disk_usage(path)
    except OSError as err:
        logger.warning("No se pudo consultar el espacio libre de %s: %s", path, err)
        return 0.0
    return round(uso.free / (1024 * 1024), 2)


def hay_espacio(path: str = ".", min_free_mb: int = MIN_FREE_MB_DEFAULT) -> bool:
    """Comprueba que quede espacio mínimo libre antes de escribir.

    Args:
        path (str): Ruta dentro del sistema de archivos a consultar.
        min_free_mb (int): Megabytes libres mínimos exigidos.

    Returns:
        bool: True si hay al menos `min_free_mb` MB libres.
    """
    return espacio_libre_mb(path) >= float(min_free_mb)


def podar(
    history_dir: str = HISTORY_DIR,
    keep: int = KEEP_DEFAULT,
    max_mb: int = MAX_MB_DEFAULT,
    dry_run: bool = False,
) -> PodaResult:
    """Poda el historial por cantidad y por tamaño, sin tocar el más reciente.

    Reglas:
        1. Conserva los `keep` snapshots más recientes.
        2. Si el tamaño resultante supera `max_mb`, elimina los más antiguos de
           los conservados hasta cumplir, dejando siempre al menos uno.
        3. `max_mb <= 0` desactiva el tope por tamaño.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.
        keep (int): Snapshots a conservar (mínimo 1).
        max_mb (int): Tope de tamaño en MB para el historial restante.
        dry_run (bool): Si es True solo calcula, no borra.

    Returns:
        PodaResult: Rutas borradas (o a borrar), bytes liberados y restantes.
    """
    items = _snapshots(history_dir)
    if not items:
        return PodaResult()

    keep = max(int(keep), 1)
    conservar = items[:keep]
    descartar = items[keep:]

    if max_mb and max_mb > 0:
        tope = int(max_mb) * 1024 * 1024
        total = sum(size for _, size, _ in conservar)
        while len(conservar) > 1 and total > tope:
            _, size, ruta = conservar.pop()
            descartar.append((0.0, size, ruta))
            total -= size

    resultado = PodaResult(restantes=len(conservar))
    for _, size, ruta in descartar:
        if not dry_run:
            try:
                os.remove(ruta)
            except OSError as err:
                logger.warning("No se pudo eliminar el snapshot %s: %s", ruta, err)
                continue
        resultado.borrados.append(ruta)
        resultado.liberado_bytes += size
    return resultado

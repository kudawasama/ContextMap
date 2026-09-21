"""Carga de eventos desde fuentes externas (JSONL y chats).

Lee y normaliza entradas heterogéneas provenientes de archivos JSONL
agnósticos o carpetas de conversaciones de chat.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any

from context_map.core.models import Event
from context_map.core.parsing.clasificacion import JSONL_TYPES, _heuristic_event
from context_map.infrastructure.analyzers.exclusions import es_archivo_excluido

logger = logging.getLogger(__name__)

EXTENSIONES_CONVERSACION: frozenset[str] = frozenset({".md", ".txt", ".json", ".jsonl"})
"""Extensiones que pueden contener una conversación exportada."""

_BYTES_BINARIOS: bytes = b"\x00"
"""Marca de archivo binario/UTF-16 (``desktop.ini`` de Google Drive, por ejemplo)."""


def _safe_jsonl(path: str) -> list[dict[str, Any]]:
    """Lee objetos JSON desde un archivo JSONL tolerando errores de formato.

    Args:
        path (str): Ruta al archivo JSONL.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios parseados correctamente.
    """
    out: list[dict[str, Any]] = []
    if not path or not isinstance(path, str) or not os.path.exists(path):
        return out
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    out.append(json.loads(line_str))
                except Exception as err:
                    logger.debug("Línea no JSON ignorada en %s: %s", path, err)
                    continue
    except Exception as err:
        logger.warning("No se pudo parsear JSONL %s: %s", path, err)
    return out


def load_events_from_jsonl(path: str) -> list[Event]:
    """Convierte líneas JSON tipadas en objetos Event.

    Args:
        path (str): Ruta del archivo JSONL.

    Returns:
        List[Event]: Lista de eventos normalizados.
    """
    events: list[Event] = []
    for obj in _safe_jsonl(path):
        t = obj.get("type", "")
        if not isinstance(t, str):
            continue
        t = t.upper().strip()
        text = str(obj.get("text", "")).strip()
        if t in JSONL_TYPES and text:
            events.append(
                Event(
                    type=t,
                    text=text,
                    timestamp=str(obj.get("timestamp", "")),
                    source=str(obj.get("source", "")),
                    tags=list(obj.get("tags") or []),
                    meta=obj.get("meta") or {},
                )
            )
    return events


def _es_archivo_de_conversacion(ruta: str) -> bool:
    """Indica si un archivo de la carpeta de chats puede contener una conversación.

    Descarta los archivos de sistema que los clientes de Drive siembran en cada
    carpeta (``desktop.ini``) y cualquier extensión que no sea de texto.

    Args:
        ruta (str): Ruta del archivo.

    Returns:
        bool: True si el archivo debe leerse como conversación.
    """
    nombre = os.path.basename(ruta)
    if es_archivo_excluido(nombre):
        return False
    return os.path.splitext(nombre)[1].lower() in EXTENSIONES_CONVERSACION


def _parece_binario(ruta: str) -> bool:
    """Detecta archivos binarios o UTF-16 por la presencia de bytes nulos.

    Args:
        ruta (str): Ruta del archivo.

    Returns:
        bool: True si el archivo no es texto UTF-8 legible.
    """
    try:
        with open(ruta, "rb") as fb:
            return _BYTES_BINARIOS in fb.read(4096)
    except OSError as err:
        logger.debug("No se pudo leer %s: %s", ruta, err)
        return True


_FECHA_EN_NOMBRE = re.compile(r"(\d{4})-?(\d{2})-?(\d{2})")


def _fecha_de_conversacion(ruta: str) -> str:
    """Deduce la fecha de una conversación a partir del nombre o de su mtime.

    Los exports de chat suelen nombrarse ``2026-09-14_...`` o
    ``20260813_104604_...``; si el nombre no trae fecha se usa la de
    modificación del archivo. Sin fecha, los eventos que genera esta carpeta son
    invisibles en el historial por día.

    Args:
        ruta (str): Ruta del archivo de conversación.

    Returns:
        str: Fecha ISO-8601, o cadena vacía si no se pudo deducir.
    """
    coincidencia = _FECHA_EN_NOMBRE.search(os.path.basename(ruta))
    if coincidencia:
        anio, mes, dia = coincidencia.groups()
        try:
            return datetime(int(anio), int(mes), int(dia)).isoformat(timespec="seconds")
        except ValueError:
            logger.debug("Fecha inválida en el nombre de %s: %s", ruta, coincidencia.group(0))
    try:
        return datetime.fromtimestamp(os.path.getmtime(ruta)).isoformat(timespec="seconds")
    except OSError as err:
        logger.debug("No se pudo leer la fecha de %s: %s", ruta, err)
        return ""


def load_events_from_chat_folder(folder: str) -> list[Event]:
    """Lee archivos de conversaciones de chat y genera eventos clasificados.

    Args:
        folder (str): Ruta del directorio de chats.

    Returns:
        List[Event]: Eventos extraídos y clasificados.
    """
    events: list[Event] = []
    if not folder or not os.path.isdir(folder):
        return events
    try:
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            if not _es_archivo_de_conversacion(path):
                logger.debug("Se omite '%s': no es un archivo de conversación", name)
                continue
            if _parece_binario(path):
                logger.debug("Se omite '%s': parece binario (bytes nulos)", name)
                continue
            source = f"chat:{name}"
            fecha = _fecha_de_conversacion(path)
            try:
                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line_str = line.strip()
                        if not line_str or len(line_str) < 8:
                            continue
                        events.append(_heuristic_event(line_str, source, fecha))
            except Exception as err:
                logger.debug("No se pudo leer archivo de chat %s: %s", path, err)
                continue
    except Exception as err:
        logger.warning("No se pudo leer carpeta de chats %s: %s", folder, err)
    return events

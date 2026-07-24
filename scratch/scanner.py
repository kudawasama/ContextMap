"""Escáner de proyecto para Context Map Generator.

Combina análisis de estructura y contenido para generar
eventos automáticamente desde el código fuente.
"""

from __future__ import annotations

import os
import json
from typing import List
from datetime import datetime

from context_map.analyzers.structure import escanear_proyecto, EstructuraProyecto
from context_map.analyzers.content import analizar_directorio, InfoContenido
from context_map.models import Event


def _ahora() -> str:
    """Timestamp actual."""
    return datetime.now().isoformat(timespec="seconds")


def _events_desde_estructura(est: EstructuraProyecto) -> List[Event]:
    """Genera eventos desde la estructura del proyecto."""
    eventos = []

    # Evento BASE: identidad del proyecto
    eventos.append(Event(
        type="BASE",
        text=f"Proyecto '{est.nombre}' con {len(est.archivos)} archivos, {est.total_lineas} líneas totales",
        timestamp=_ahora(),
        source="scanner",
        tags=["estructura", "metricas"],
    ))

    # Evento por tipo de archivo
    for tipo, cantidad in est.por_tipo.items():
        if cantidad > 0:
            eventos.append(Event(
                type="IDEA",
                text=f"El proyecto contiene {cantidad} archivos de tipo '{tipo}'",
                timestamp=_ahora(),
                source="scanner",
                tags=["estructura", tipo],
            ))

    # Eventos por entrypoints
    for ep in est.entrypoints[:3]:
        eventos.append(Event(
            type="BASE",
            text=f"Entrypoint detectado: {ep}",
            timestamp=_ahora(),
            source="scanner",
            tags=["entrypoint"],
        ))

    # Eventos por docs
    for doc in est.docs[:3]:
        eventos.append(Event(
            type="BASE",
            text=f"Documentación encontrada: {doc}",
            timestamp=_ahora(),
            source="scanner",
            tags=["docs"],
        ))

    # Eventos por configs
    for config in est.configs[:3]:
        eventos.append(Event(
            type="CAMBIO",
            text=f"Archivo de configuración: {config}",
            timestamp=_ahora(),
            source="scanner",
            tags=["config"],
        ))

    # Eventos por tests
    if est.tests:
        eventos.append(Event(
            type="PRUEBA",
            text=f"Se detectaron {len(est.tests)} archivos de test",
            timestamp=_ahora(),
            source="scanner",
            tags=["tests"],
        ))
    else:
        eventos.append(Event(
            type="RIESGO",
            text="No se detectaron archivos de test en el proyecto",
            timestamp=_ahora(),
            source="scanner",
            tags=["tests", "riesgo"],
        ))

    return eventos


def _events_desde_contenido(contenidos: List[InfoContenido]) -> List[Event]:
    """Genera eventos desde el análisis de contenido."""
    eventos = []

    for info in contenidos:
        # Docstrings principales
        if info.docstring_principal:
            ruta = os.path.basename(info.ruta)
            eventos.append(Event(
                type="IDEA",
                text=f"{ruta}: {info.docstring_principal[:150]}",
                timestamp=_ahora(),
                source="scanner",
                tags=["docstring", ruta],
            ))

        # Clases importantes
        if len(info.clases) > 0:
            eventos.append(Event(
                type="IDEA",
                text=f"{os.path.basename(info.ruta)} define {len(info.clases)} clase(s): {', '.join(info.clases[:5])}",
                timestamp=_ahora(),
                source="scanner",
                tags=["clases", os.path.basename(info.ruta)],
            ))

        # Complejidad alta
        if info.complejidad == "alta":
            eventos.append(Event(
                type="RIESGO",
                text=f"Archivo de alta complejidad: {info.ruta} ({info.lineas_codigo} líneas)",
                timestamp=_ahora(),
                source="scanner",
                tags=["complejidad", "riesgo"],
            ))

        # TODOs/FIXMEs
        for todo in info.todos[:3]:
            eventos.append(Event(
                type="FUTURO",
                text=f"Pendiente en {info.ruta}: {todo}",
                timestamp=_ahora(),
                source="scanner",
                tags=["todo", "pendiente"],
            ))

    return eventos


def escanear_y_generar_eventos(
    ruta_raiz: str,
    ignorar: List[str] = None,
) -> List[Event]:
    """Escanea un proyecto y genera eventos para el mapa.

    Args:
        ruta_raiz: Ruta raíz del proyecto a escanear
        ignorar: Carpetas a ignorar

    Returns:
        Lista de eventos generados desde el código
    """
    # Análisis de estructura
    estructura = escanear_proyecto(ruta_raiz, ignorar)

    # Análisis de contenido (solo Python por ahora)
    contenidos = analizar_directorio(ruta_raiz)

    # Generar eventos
    eventos = []
    eventos.extend(_events_desde_estructura(estructura))
    eventos.extend(_events_desde_contenido(contenidos))

    return eventos


def guardar_eventos_escaneados(eventos: List[Event], output_path: str) -> int:
    """Guarda eventos escaneados en un JSONL.

    Returns:
        Número de eventos guardados
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Leer existentes para evitar duplicados
    existentes = set()
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        obj = json.loads(linea)
                        existentes.add(obj.get("text", "")[:80])
                    except Exception:
                        pass

    # Filtrar nuevos
    nuevos = []
    for e in eventos:
        if e.text[:80] not in existentes:
            nuevos.append(e)

    # Guardar
    with open(output_path, "a", encoding="utf-8") as f:
        for e in nuevos:
            f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

    return len(nuevos)

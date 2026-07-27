"""Escáner de proyecto para Context Map Generator.

Combina análisis de estructura y contenido para generar
eventos automáticamente desde el código fuente.
"""

from __future__ import annotations

import os
import json
from typing import List
from datetime import datetime

from context_map.infrastructure.analyzers.structure import escanear_proyecto, EstructuraProyecto
from context_map.infrastructure.analyzers.content import analizar_directorio, InfoContenido
from context_map.core.models import Event


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
    max_tipos = 3
    vistos = 0
    for tipo, cantidad in est.por_tipo.items():
        if cantidad > 0:
            eventos.append(Event(
                type="IDEA",
                text=f"El proyecto contiene {cantidad} archivos de tipo '{tipo}'",
                timestamp=_ahora(),
                source="scanner",
                tags=["estructura", tipo],
            ))
            vistos += 1
            if vistos >= max_tipos:
                break

    # Entrypoints
    for ep in est.entrypoints[:1]:
        eventos.append(Event(
            type="BASE",
            text=f"Entrypoint detectado: {ep}",
            timestamp=_ahora(),
            source="scanner",
            tags=["entrypoint"],
        ))

    # Docs relevantes
    for doc in est.docs[:1]:
        eventos.append(Event(
            type="BASE",
            text=f"Documentación encontrada: {doc}",
            timestamp=_ahora(),
            source="scanner",
            tags=["docs"],
        ))

    # Configs relevantes
    for config in est.configs[:2]:
        eventos.append(Event(
            type="CAMBIO",
            text=f"Archivo de configuración: {config}",
            timestamp=_ahora(),
            source="scanner",
            tags=["config"],
        ))

    # Carpetas principales como nodos estructurales
    carpetas_principales = sorted({os.path.dirname(a.ruta) for a in est.archivos})
    for carpeta in carpetas_principales[:8]:
        eventos.append(Event(
            type="BASE",
            text=f"Carpeta: {carpeta}",
            timestamp=_ahora(),
            source="folder-map",
            tags=["carpeta", carpeta],
        ))

    # Archivos relevantes por categoría, limitados para no saturar
    for archivo in est.entrypoints[:3]:
        eventos.append(Event(
            type="BASE",
            text=f"Entrypoint: {archivo}",
            timestamp=_ahora(),
            source="structure",
            tags=["entrypoint", os.path.dirname(archivo), os.path.basename(archivo)],
        ))
    for archivo in est.configs[:5]:
        eventos.append(Event(
            type="CAMBIO",
            text=f"Config: {archivo}",
            timestamp=_ahora(),
            source="structure",
            tags=["config", os.path.dirname(archivo), os.path.basename(archivo)],
        ))
    for archivo in est.docs[:5]:
        eventos.append(Event(
            type="IDEA",
            text=f"Doc: {archivo}",
            timestamp=_ahora(),
            source="structure",
            tags=["doc", os.path.dirname(archivo), os.path.basename(archivo)],
        ))
    for archivo in est.tests[:5]:
        eventos.append(Event(
            type="PRUEBA",
            text=f"Test: {archivo}",
            timestamp=_ahora(),
            source="structure",
            tags=["test", os.path.dirname(archivo), os.path.basename(archivo)],
        ))

    # Archivo más grande por tipo relevante como muestra
    candidatos_tipo = {}
    for archivo in est.archivos:
        if archivo.tamano <= 0:
            continue
        if archivo.tipo not in candidatos_tipo or archivo.tamano > candidatos_tipo[archivo.tipo].tamano:
            candidatos_tipo[archivo.tipo] = archivo
    for tipo, archivo in sorted(candidatos_tipo.items())[:6]:
        eventos.append(Event(
            type="IDEA",
            text=f"{tipo}: {archivo.ruta} ({archivo.tamano} bytes)",
            timestamp=_ahora(),
            source="structure",
            tags=[tipo, os.path.dirname(archivo.ruta), os.path.basename(archivo.ruta)],
        ))

    return eventos


def _events_desde_contenido(contenidos: List[InfoContenido], max_eventos: int = 60) -> List[Event]:
    """Genera eventos desde el análisis de contenido, limitados para no saturar el grafo."""
    eventos: List[Event] = []

    # Priorizar: alta complejidad → TODOs → docstrings → clases
    relevantes = []
    resto = []
    for info in contenidos:
        score = 0
        if info.complejidad == "alta":
            score += 4
        if info.todos:
            score += 3
        if info.docstring_principal and len(info.docstring_principal) > 40:
            score += 2
        if len(info.clases) >= 3:
            score += 1
        if score >= 3:
            relevantes.append((score, info))
        else:
            resto.append((score, info))

    # Tomar los más relevantes primero
    candidatos = sorted(relevantes, key=lambda x: x[0], reverse=True)[:max_eventos // 2]
    if len(candidatos) < max_eventos:
        candidatos += sorted(resto, key=lambda x: x[0], reverse=True)[: max_eventos - len(candidatos)]

    for _, info in candidatos:
        ruta = os.path.basename(info.ruta)

        # Alta complejidad
        if info.complejidad == "alta":
            eventos.append(Event(
                type="RIESGO",
                text=f"Archivo complejo ({info.lineas_codigo} líneas): {ruta}",
                timestamp=_ahora(),
                source="scanner",
                tags=["complejidad", "riesgo", ruta],
            ))

        # TODOs/FIXMEs
        if info.todos:
            eventos.append(Event(
                type="FUTURO",
                text=f"Pendientes en {ruta}: {info.todos[0]}",
                timestamp=_ahora(),
                source="scanner",
                tags=["todo", ruta],
            ))

        # Docstring principal
        if info.docstring_principal and len(info.docstring_principal) > 40:
            eventos.append(Event(
                type="IDEA",
                text=f"{ruta}: {info.docstring_principal[:120]}",
                timestamp=_ahora(),
                source="scanner",
                tags=["docstring", ruta],
            ))

        # Clases importantes
        if len(info.clases) >= 3:
            eventos.append(Event(
                type="IDEA",
                text=f"{ruta}: {len(info.clases)} clases ({', '.join(info.clases[:5])})",
                timestamp=_ahora(),
                source="scanner",
                tags=["clases", ruta],
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
    print("   ⏳ Fase 1/2: Escaneando estructura del proyecto...")
    # Análisis de estructura
    estructura = escanear_proyecto(ruta_raiz, ignorar)
    print(f"   → {len(estructura.archivos)} archivos encontrados, {estructura.total_lineas} líneas totales")

    print()
    print("   ⏳ Fase 2/2: Analizando contenido de archivos Python...")
    # Análisis de contenido (solo Python por ahora)
    contenidos = analizar_directorio(ruta_raiz)

    # Generar eventos
    eventos = []
    eventos.extend(_events_desde_estructura(estructura))
    eventos.extend(_events_desde_contenido(contenidos))

    print(f"   → {len(eventos)} eventos generados")
    print()

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

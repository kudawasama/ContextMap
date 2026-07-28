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



# Carpetas y patrones que deben excluirse del escaneo para evitar ruido
_CARPETAS_EXCLUIDAS: set = {
    ".context-map", ".venv", ".git", "__pycache__", "node_modules",
    ".mypy_cache", ".pytest_cache", ".tox", ".eggs", "dist", "build",
    ".idea", ".vscode", ".vs", "egg-info",
}

def _es_ruta_excluida(ruta: str) -> bool:
    """Verifica si una ruta contiene carpetas que deben excluirse del escaneo.

    Args:
        ruta: Ruta relativa del archivo o carpeta

    Returns:
        True si la ruta debe excluirse
    """
    partes = ruta.replace("\\", "/").split("/")
    return any(parte in _CARPETAS_EXCLUIDAS for parte in partes)


def _events_desde_estructura(est: EstructuraProyecto) -> List[Event]:
    """Genera eventos semánticos desde la estructura del proyecto.

    NO produce eventos de métricas de archivos, carpetas, tipos,
    ni configuraciones menores. Solo captura la identidad del
    proyecto y sus entrypoints principales.

    Args:
        est: Estructura del proyecto escaneada

    Returns:
        Lista reducida de eventos de alto valor semántico
    """
    eventos: List[Event] = []

    # 1. BASE: identidad del proyecto (1 evento único)
    entrypoints_ratio = f"entrypoints: {len(est.entrypoints)}" if est.entrypoints else "sin entrypoints"
    eventos.append(Event(
        type="BASE",
        text=f"Proyecto '{est.nombre}' — {len(est.archivos)} archivos, {est.total_lineas} líneas, {entrypoints_ratio}",
        timestamp=_ahora(),
        source="scanner",
        tags=["estructura", "proyecto"],
        meta={"descripcion": (
            f"Proyecto detectado en {est.ruta_raiz}. "
            f"Compuesto por {len(est.archivos)} archivos ({est.total_lineas} líneas totales). "
            f"{entrypoints_ratio.replace('entrypoints: ', 'Puntos de entrada: ').replace('sin entrypoints', 'Sin entrypoints detectados')}."
        )},
    ))

    # 2. Doc principal (README o similar) como IDEA del dominio
    if est.docs:
        doc_principal = est.docs[0]
        doc_path = os.path.relpath(doc_principal, est.ruta_raiz) if os.path.isabs(doc_principal) else doc_principal
        eventos.append(Event(
            type="BASE",
            text=f"Documentación principal: {doc_path}",
            timestamp=_ahora(),
            source="scanner",
            tags=["documentacion", "proyecto"],
        ))

    # 3. Entrypoints principales (hasta 2) como BASE
    for ep in est.entrypoints[:2]:
        if _es_ruta_excluida(ep):
            continue
        eventos.append(Event(
            type="BASE",
            text=f"Entrypoint: {ep}",
            timestamp=_ahora(),
            source="scanner",
            tags=["entrypoint", os.path.dirname(ep) if os.path.dirname(ep) != "." else "raiz"],
        ))

    return eventos


def _events_desde_contenido(contenidos: List[InfoContenido], max_eventos: int = 30) -> List[Event]:
    """Genera eventos semánticos desde el análisis de contenido.

    NO produce eventos por docstring, clases, ni archivos individuales.
    Solo genera:

    - 1 evento RIESGO consolidado con los 3 archivos más complejos
    - 1-2 eventos FUTURO con TODOs/FIXMEs detectados (max 5 total)

    Args:
        contenidos: Lista de información de contenido analizado
        max_eventos: Límite máximo de eventos a generar

    Returns:
        Lista reducida de eventos de alto valor
    """
    eventos: List[Event] = []

    if not contenidos:
        return eventos

    # === RIESGO: archivos más complejos (consolidado) ===
    complejos = [info for info in contenidos if info.complejidad == "alta"]
    if len(complejos) >= 2:
        # Top 3 archivos complejos en un solo evento
        top3 = sorted(complejos, key=lambda x: x.lineas_codigo, reverse=True)[:3]
        resumen = "; ".join(
            f"{os.path.basename(c.ruta)} ({c.lineas_codigo} líneas)"
            for c in top3
        )
        eventos.append(Event(
            type="RIESGO",
            text=f"Archivos de alta complejidad ({len(complejos)} total): {resumen}",
            timestamp=_ahora(),
            source="scanner",
            tags=["complejidad", "riesgo"],
            meta={"descripcion": (
                f"Se detectaron {len(complejos)} archivos con complejidad alta. "
                f"Los más extensos son: {resumen}. "
                "Estas áreas son propensas a bugs y difíciles de mantener."
            )},
        ))
    elif len(complejos) == 1:
        c = complejos[0]
        eventos.append(Event(
            type="RIESGO",
            text=f"Archivo complejo: {os.path.basename(c.ruta)} ({c.lineas_codigo} líneas)",
            timestamp=_ahora(),
            source="scanner",
            tags=["complejidad", "riesgo"],
        ))

    # === FUTURO: TODOs/FIXMEs consolidados (máximo 5 total) ===
    todos_global: List[str] = []
    for info in contenidos:
        if info.todos:
            for todo in info.todos:
                # Limpiar marcadores comunes
                texto = todo.replace("TODO:", "").replace("FIXME:", "").replace("HACK:", "").strip()
                if texto and texto not in todos_global:
                    todos_global.append(texto)

    if todos_global:
        # Hasta 5 TODOs distintos
        for todo_texto in todos_global[:5]:
            eventos.append(Event(
                type="FUTURO",
                text=f"TODO: {todo_texto}",
                timestamp=_ahora(),
                source="scanner",
                tags=["todo"],
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

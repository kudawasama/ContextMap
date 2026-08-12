"""Escáner de proyecto para el mapa conceptual.


Combina análisis de estructura y contenido de código fuente para generar
eventos del grafo conceptual automáticamente sin saturar de ruido.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from context_map.core.models import Event
from context_map.core.storage import append_jsonl, load_jsonl
from context_map.infrastructure.analyzers.content import InfoContenido, analizar_directorio
from context_map.infrastructure.analyzers.structure import EstructuraProyecto, escanear_proyecto


def _ahora() -> str:
    """Retorna timestamp actual en ISO-8601.

    Returns:
        str: Timestamp actual.
    """
    return datetime.now().isoformat(timespec="seconds")


_CARPETAS_EXCLUIDAS: set[str] = {
    ".context-map",
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".eggs",
    "dist",
    "build",
    ".idea",
    ".vscode",
    ".vs",
    "egg-info",
    "desktop.ini",
    ".ds_store",
    "thumbs.db",
}


def _es_ruta_excluida(ruta: str) -> bool:
    """Verifica si una ruta contiene carpetas u archivos ignorados.

    Args:
        ruta (str): Ruta a evaluar.

    Returns:
        bool: True si debe ser ignorada.
    """
    nombre = os.path.basename(ruta).lower()
    if nombre in ("desktop.ini", ".ds_store", "thumbs.db") or nombre.endswith((".gdoc", ".gsheet", ".gslides")):
        return True

    partes = ruta.replace("\\", "/").split("/")
    return any(parte.lower() in _CARPETAS_EXCLUIDAS for parte in partes)


def _events_desde_estructura(est: EstructuraProyecto) -> list[Event]:
    """Genera eventos de alto nivel semántico a partir de la estructura.

    Args:
        est (EstructuraProyecto): Datos de la estructura.

    Returns:
        List[Event]: Eventos semánticos.
    """
    eventos: list[Event] = []

    entrypoints_ratio = f"entrypoints: {len(est.entrypoints)}" if est.entrypoints else "sin entrypoints"
    eventos.append(
        Event(
            type="BASE",
            text=f"Proyecto '{est.nombre}' — {len(est.archivos)} archivos, {est.total_lineas} líneas, {entrypoints_ratio}",
            timestamp=_ahora(),
            source="scanner",
            tags=["estructura", "proyecto"],
            meta={
                "descripcion": (
                    f"Proyecto detectado en {est.ruta_raiz}. "
                    f"Compuesto por {len(est.archivos)} archivos ({est.total_lineas} líneas totales)."
                )
            },
        )
    )

    if est.docs:
        doc_principal = est.docs[0]
        doc_path = (
            os.path.relpath(doc_principal, est.ruta_raiz)
            if os.path.isabs(doc_principal)
            else doc_principal
        )
        eventos.append(
            Event(
                type="BASE",
                text=f"Documentación principal: {doc_path}",
                timestamp=_ahora(),
                source="scanner",
                tags=["documentacion", "proyecto"],
            )
        )

    for ep in est.entrypoints[:2]:
        if _es_ruta_excluida(ep):
            continue
        eventos.append(
            Event(
                type="BASE",
                text=f"Entrypoint: {ep}",
                timestamp=_ahora(),
                source="scanner",
                tags=["entrypoint", os.path.dirname(ep) if os.path.dirname(ep) != "." else "raiz"],
            )
        )

    return eventos


def _events_desde_contenido(
    contenidos: list[InfoContenido],
    max_eventos: int = 30,
    ruta_raiz: str = ".",
) -> list[Event]:
    """Genera eventos semánticos consolidando complejidad y TODOs con ubicaciones estables.

    Args:
        contenidos (List[InfoContenido]): Información del contenido.
        max_eventos (int): Límite de eventos.
        ruta_raiz (str): Ruta raíz del proyecto.

    Returns:
        List[Event]: Eventos semánticos generados.
    """
    eventos: list[Event] = []
    if not contenidos:
        return eventos

    complejos = [info for info in contenidos if info.complejidad == "alta"]
    if len(complejos) >= 2:
        top3 = sorted(complejos, key=lambda x: x.lineas_codigo, reverse=True)[:3]
        rutas_top3 = [
            os.path.relpath(c.ruta, ruta_raiz).replace("\\", "/") for c in top3
        ]
        resumen = "; ".join(rutas_top3)
        eventos.append(
            Event(
                type="RIESGO",
                text=f"Archivos de alta complejidad ({len(complejos)} total): {resumen}",
                timestamp=_ahora(),
                source="scanner",
                tags=["complejidad", "riesgo"],
                meta={
                    "total_complejos": len(complejos),
                    "archivos": [
                        os.path.relpath(c.ruta, ruta_raiz).replace("\\", "/")
                        for c in complejos
                    ],
                },
            )
        )
    elif len(complejos) == 1:
        c = complejos[0]
        rel_path = os.path.relpath(c.ruta, ruta_raiz).replace("\\", "/")
        eventos.append(
            Event(
                type="RIESGO",
                text=f"Archivo complejo: {rel_path}",
                timestamp=_ahora(),
                source="scanner",
                tags=["complejidad", "riesgo"],
                meta={"lineas_codigo": c.lineas_codigo, "ruta": rel_path},
            )
        )

    todos_global: list[tuple[str, str]] = []
    for info in contenidos:
        if info.todos:
            rel_path = os.path.relpath(info.ruta, ruta_raiz).replace("\\", "/")
            if rel_path.startswith(".."):
                continue
            for todo in info.todos:
                match = re.match(r"L(\d+):\s*(.*)", todo)
                if match:
                    line_no, line_text = match.group(1), match.group(2)
                    clean_text = line_text.replace("TODO:", "").replace("FIXME:", "").replace("HACK:", "").strip()
                    if clean_text:
                        ubicacion = f"{rel_path}:L{line_no}"
                        if (ubicacion, clean_text) not in todos_global:
                            todos_global.append((ubicacion, clean_text))
                else:
                    clean_text = todo.replace("TODO:", "").replace("FIXME:", "").replace("HACK:", "").strip()
                    if clean_text:
                        ubicacion = rel_path
                        if (ubicacion, clean_text) not in todos_global:
                            todos_global.append((ubicacion, clean_text))

    if todos_global:
        for ubicacion, todo_texto in todos_global[:max_eventos]:
            eventos.append(
                Event(
                    type="FUTURO",
                    text=f"TODO ({ubicacion}): {todo_texto}",
                    timestamp=_ahora(),
                    source="scanner",
                    tags=["todo"],
                    meta={"ubicacion": ubicacion, "texto": todo_texto},
                )
            )

    return eventos


def escanear_y_generar_eventos(
    ruta_raiz: str,
    ignorar: list[str] | None = None,
) -> list[Event]:
    """Escanea el proyecto en la ruta dada y produce eventos normalizados.

    Args:
        ruta_raiz (str): Ruta raíz del proyecto.
        ignorar (Optional[List[str]]): Carpetas opcionales a ignorar.

    Returns:
        List[Event]: Eventos generados desde el código.
    """
    estructura = escanear_proyecto(ruta_raiz, ignorar)
    contenidos = analizar_directorio(ruta_raiz)

    ev_est = _events_desde_estructura(estructura)
    ev_cont = _events_desde_contenido(contenidos, ruta_raiz=ruta_raiz)

    return ev_est + ev_cont


def guardar_eventos_escaneados(eventos: list[Event], output_path: str) -> int:
    """Guarda eventos escaneados en un archivo JSONL evitando duplicados.

    Args:
        eventos (List[Event]): Lista de eventos a persistir.
        output_path (str): Ruta destino del archivo JSONL.

    Returns:
        int: Número de eventos nuevos insertados.
    """
    existentes = load_jsonl(output_path)
    textos_existentes = {e.get("text", "") for e in existentes}

    nuevos = [e for e in eventos if e.text not in textos_existentes]

    if nuevos:
        append_jsonl(output_path, [e.to_dict() for e in nuevos])

    return len(nuevos)

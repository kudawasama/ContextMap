"""Daemon / Watcher en segundo plano para sincronización automática continua.

Monitorea cambios en archivos del proyecto (.py, .md, .json, .toml, .yaml)
y ejecuta refrescos incrementales desbouncheados en tiempo real.

Guardas añadidas tras el incidente 2026-10-13 (el daemon, sumado al historial
sin tope, llenó la raíz del servidor con 148 GB): ignora las salidas que genera
el propio tool (AGENTS.md, CLAUDE.md, CONTEXT.md…), impone un intervalo mínimo
entre refrescos, suprime los eventos que ocurren durante el refresco y refresca
con ``no_snapshot=True`` — el historial es un acto deliberado, no un efecto
secundario del daemon.
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

EXTENSIONES_MONITOREADAS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt"}
DIRECTORIOS_EXCLUIDOS = {".context-map", ".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}
#: Salidas que generan ContextMap u otros agentes: no deben re-disparar el daemon.
#: `version.json` lo reescriben algunos despliegues (p. ej. kudawa-page-deploy).
ARCHIVOS_GENERADOS = {
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "CONTEXT.md",
    ".cursorrules",
    ".windsurfrules",
    "version.json",
}


def _es_archivo_relevante(path: str) -> bool:
    """Comprueba si el archivo modificado debe disparar la sincronización.

    Args:
        path (str): Ruta del archivo modificado.

    Returns:
        bool: True si el archivo debe provocar un refresco.
    """
    norm_path = path.replace("\\", "/")
    parts = norm_path.split("/")
    if any(p in DIRECTORIOS_EXCLUIDOS for p in parts):
        return False
    if os.path.basename(norm_path) in ARCHIVOS_GENERADOS:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in EXTENSIONES_MONITOREADAS


def _ejecutar_refresco_default(project_dir: str) -> None:
    """Ejecuta el comando refresh por defecto de ContextMap.

    Construye un ``argparse.Namespace`` real porque ``cmd_refresh`` y sus
    delegados (``cmd_scan``, ``project_name``) acceden a atributos como
    ``.target`` / ``.project``; pasar un ``dict`` provocaba
    ``'dict' object has no attribute 'target'`` y el refresco automático
    nunca se ejecutaba. Se usa ``quiet=True`` para no imprimir el banner de
    refresh en cada cambio de archivo detectado por el daemon y
    ``no_snapshot=True`` para que el daemon no escriba en ``maps/HISTORY``.

    Args:
        project_dir (str): Directorio raíz del proyecto a refrescar.
    """
    try:
        from context_map.application.commands.refresh import cmd_refresh
        args = argparse.Namespace(
            target=project_dir, project=None, quiet=True, no_snapshot=True
        )
        cmd_refresh(args)
    except Exception as e:
        logger.warning("Error durante refresco automático en watcher: %s", e)


def iniciar_watcher(
    project_dir: str = ".",
    debounce_ms: int = 500,
    callback: Callable[[str], None] | None = None,
    max_iterations: int = 0,
    min_interval_s: int = 60,
) -> None:
    """Inicia el escuchador de eventos en el sistema de archivos con debouncing.

    Args:
        project_dir (str): Directorio raíz del proyecto a monitorear.
        debounce_ms (int): Tiempo en ms a esperar tras la última modificación.
        callback (Callable): Función personalizada a invocar tras el debounce.
        max_iterations (int): Máximo de iteraciones de polling (0 = infinito, para tests).
        min_interval_s (int): Segundos mínimos entre dos refrescos consecutivos.
    """
    project_dir = os.path.abspath(project_dir)
    cb = callback or _ejecutar_refresco_default
    intervalo = max(float(min_interval_s), 0.0)

    # Intentar usar watchdog si está disponible
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):
            def __init__(self) -> None:
                self.last_change = 0.0
                #: Ventana durante la cual se ignoran los eventos que genera el
                #: propio refresco (rompe cualquier realimentación).
                self.suprimir_hasta = 0.0

            def on_any_event(self, event) -> None:
                if event.is_directory:
                    return
                if time.time() < self.suprimir_hasta:
                    return
                if _es_archivo_relevante(event.src_path):
                    self.last_change = time.time()

        event_handler = Handler()
        observer = Observer()
        observer.schedule(event_handler, project_dir, recursive=True)
        observer.start()

        last_processed = 0.0
        ultimo_refresco = 0.0
        iterations = 0
        try:
            while True:
                time.sleep(0.1)
                now = time.time()
                if (
                    event_handler.last_change > 0
                    and (now - event_handler.last_change) >= (debounce_ms / 1000.0)
                    and event_handler.last_change > last_processed
                    and (now - ultimo_refresco) >= intervalo
                ):
                    last_processed = now
                    ultimo_refresco = now
                    event_handler.suprimir_hasta = now + intervalo
                    cb(project_dir)

                iterations += 1
                if max_iterations > 0 and iterations >= max_iterations:
                    break
        finally:
            observer.stop()
            observer.join()
        return
    except ImportError:
        logger.info("Watchdog no instalado — usando daemon por polling inteligente.")

    # Fallback por polling inteligente de mtime (cero dependencias externas)
    mtimes: dict[str, float] = {}

    def _escanear_mtimes() -> float:
        max_mtime = 0.0
        for root, dirs, files in os.walk(project_dir):
            dirs[:] = [d for d in dirs if d not in DIRECTORIOS_EXCLUIDOS]
            for f in files:
                fpath = os.path.join(root, f)
                if _es_archivo_relevante(fpath):
                    try:
                        mt = os.path.getmtime(fpath)
                        if mt > mtimes.get(fpath, 0.0):
                            mtimes[fpath] = mt
                        if mt > max_mtime:
                            max_mtime = mt
                    except Exception:
                        continue
        return max_mtime

    # Primera pasada de inicialización
    last_known_mtime = _escanear_mtimes()
    last_trigger = 0.0
    ultimo_refresco = 0.0
    suprimir_hasta = 0.0
    iterations = 0

    while True:
        time.sleep(0.2)
        now = time.time()
        if now >= suprimir_hasta:
            current_max = _escanear_mtimes()
            if current_max > last_known_mtime:
                last_known_mtime = current_max
                last_trigger = time.time()

        now = time.time()
        if (
            last_trigger > 0
            and (now - last_trigger) >= (debounce_ms / 1000.0)
            and (now - ultimo_refresco) >= intervalo
        ):
            last_trigger = 0.0
            ultimo_refresco = now
            suprimir_hasta = now + intervalo
            cb(project_dir)

        iterations += 1
        if max_iterations > 0 and iterations >= max_iterations:
            break

"""Daemon / Watcher en segundo plano para sincronización automática continua.

Monitorea cambios en archivos del proyecto (.py, .md, .json, .toml, .yaml)
y ejecuta refrescos incrementales desbouncheados en tiempo real.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

EXTENSIONES_MONITOREADAS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt"}
DIRECTORIOS_EXCLUIDOS = {".context-map", ".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}


def _es_archivo_relevante(path: str) -> bool:
    """Comprueba si el archivo modificado debe disparar la sincronización."""
    norm_path = path.replace("\\", "/")
    parts = norm_path.split("/")
    if any(p in DIRECTORIOS_EXCLUIDOS for p in parts):
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in EXTENSIONES_MONITOREADAS


def _ejecutar_refresco_default(project_dir: str) -> None:
    """Ejecuta el comando refresh por defecto de ContextMap."""
    try:
        from context_map.application.commands.refresh import cmd_refresh
        cmd_refresh({"target_dir": project_dir, "clean": False})
    except Exception as e:
        logger.warning("Error durante refresco automático en watcher: %s", e)


def iniciar_watcher(
    project_dir: str = ".",
    debounce_ms: int = 500,
    callback: Callable[[str], None] | None = None,
    max_iterations: int = 0,
) -> None:
    """Inicia el escuchador de eventos en el sistema de archivos con debouncing.

    Args:
        project_dir (str): Directorio raíz del proyecto a monitorear.
        debounce_ms (int): Tiempo en ms a esperar tras la última modificación.
        callback (Callable): Función personalizada a invocar tras el debounce.
        max_iterations (int): Máximo de iteraciones de polling (0 = infinito, para tests).
    """
    project_dir = os.path.abspath(project_dir)
    cb = callback or _ejecutar_refresco_default

    # Intentar usar watchdog si está disponible
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer

        class Handler(FileSystemEventHandler):
            def __init__(self) -> None:
                self.last_change = 0.0

            def on_any_event(self, event) -> None:
                if event.is_directory:
                    return
                if _es_archivo_relevante(event.src_path):
                    self.last_change = time.time()

        event_handler = Handler()
        observer = Observer()
        observer.schedule(event_handler, project_dir, recursive=True)
        observer.start()

        last_processed = 0.0
        iterations = 0
        try:
            while True:
                time.sleep(0.1)
                now = time.time()
                if (
                    event_handler.last_change > 0
                    and (now - event_handler.last_change) >= (debounce_ms / 1000.0)
                    and event_handler.last_change > last_processed
                ):
                    last_processed = now
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
    iterations = 0

    while True:
        time.sleep(0.2)
        current_max = _escanear_mtimes()
        if current_max > last_known_mtime:
            last_known_mtime = current_max
            last_trigger = time.time()

        now = time.time()
        if (
            last_trigger > 0
            and (now - last_trigger) >= (debounce_ms / 1000.0)
        ):
            last_trigger = 0.0
            cb(project_dir)

        iterations += 1
        if max_iterations > 0 and iterations >= max_iterations:
            break

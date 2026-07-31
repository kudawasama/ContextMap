"""Configuración centralizada de logging para ContextMap.

Provee la inicialización del sistema de registros (nivel, formato y destino)
usado por todos los módulos del proyecto, así como un *helper* para construir
loggers por módulo.

La salida de logs se envía a ``sys.stderr`` para no contaminar la salida
estándar (stdout), que los comandos reservan para datos útiles al usuario.
"""

from __future__ import annotations

import logging
import sys

FORMATO_DEFAULT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
FECHA_DEFAULT = "%H:%M:%S"


def _resolver_nivel(level: str, quiet: bool, verbose: bool) -> int:
    """Resuelve el nivel efectivo según las banderas de la CLI.

    Args:
        level (str): Nivel base solicitado.
        quiet (bool): Silencia información (sube a WARNING).
        verbose (bool): Activa depuración (baja a DEBUG).

    Returns:
        int: Constante de nivel de logging.
    """
    if verbose:
        return logging.DEBUG
    if quiet:
        return logging.WARNING
    return getattr(logging, level.upper(), logging.INFO)


def setup_logging(level: str = "INFO", quiet: bool = False, verbose: bool = False) -> None:
    """Configura el sistema de logging global una única vez.

    Args:
        level (str): Nivel base ('DEBUG', 'INFO', 'WARNING', 'ERROR').
        quiet (bool): Si es True, silencia los mensajes informativos (nivel WARNING).
        verbose (bool): Si es True, activa el nivel DEBUG para diagnóstico exhaustivo.
    """
    nivel = _resolver_nivel(level, quiet, verbose)
    root = logging.getLogger()
    # Evitar handlers duplicados en llamadas consecutivas (tests, hooks).
    if any(isinstance(h.formatter, _ContextMapFormatter) for h in root.handlers):
        root.setLevel(nivel)
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_ContextMapFormatter(FORMATO_DEFAULT, FECHA_DEFAULT))
    root.addHandler(handler)
    root.setLevel(nivel)


def get_logger(nombre: str) -> logging.Logger:
    """Devuelve un logger configurado para el módulo indicado.

    Args:
        nombre (str): Nombre del módulo (convención ``__name__``).

    Returns:
        logging.Logger: Logger listo para su uso.
    """
    return logging.getLogger(nombre)


class _ContextMapFormatter(logging.Formatter):
    """Formatter marcador que identifica la configuración del proyecto."""

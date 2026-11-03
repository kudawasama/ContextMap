"""Núcleo compartido del servidor MCP: instancia FastMCP y utilidades.

Aquí vive lo que todas las tools necesitan: el registro condicional (``_tool``),
los envoltorios de ejecución con captura de stdout, la lectura del brief y las
comprobaciones de seguridad (target válido y confirmación explícita).

La instancia ``_fastmcp`` se crea una sola vez en este módulo; si cada grupo de
tools creara la suya, el servidor expondría varias apps MCP incompletas.
"""

from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from types import SimpleNamespace as NS

_fastmcp: FastMCP | None = None
try:
    from mcp.server.fastmcp import FastMCP

    _fastmcp = FastMCP("context-map")
except ImportError:  # mcp no instalado: el módulo se importa pero sin servidor
    _fastmcp = None

#: Frase maestra del baúl, tomada del entorno al arrancar. Vive solo en memoria:
#: si siguiera en ``os.environ``, cualquier proceso hijo la heredaría.
_FRASE_MAESTRA: str | None = None


def _frase_maestra() -> str | None:
    """Devuelve la frase maestra y la borra del entorno en la primera lectura.

    El servidor MCP necesita la frase para descifrar, pero no debe dejarla en
    ``os.environ``: los comandos que ejecuta ``secret_exec`` heredan el entorno
    y podrían exfiltrarla. Se conserva en memoria durante la sesión.

    Returns:
        str | None: Frase maestra, o ``None`` si el servidor no la tiene.
    """
    global _FRASE_MAESTRA
    if _FRASE_MAESTRA:
        return _FRASE_MAESTRA
    valor = os.environ.pop("CTXMAP_MASTER_PHRASE", None)
    if valor:
        _FRASE_MAESTRA = valor
    return _FRASE_MAESTRA


def _tool(fn):
    """Decorador condicional: registra en FastMCP solo si el SDK está disponible."""
    if _fastmcp is not None:
        return _fastmcp.tool()(fn)
    return fn


def _ejecutar(fn, args) -> str:
    """Ejecuta un comando de ctxmap capturando su stdout para devolverlo."""
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            fn(args)
        return buf.getvalue().strip() or "OK"
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR: {err}"


def _ejecutar_con_target(cmd_func, tool: str, target: str, **kwargs) -> str:
    """Resuelve el target y ejecuta un comando de ctxmap con manejo de errores.

    Args:
        cmd_func: Función comando a invocar.
        tool: Nombre de la tool (para los mensajes de error).
        target: Ruta del proyecto (posiblemente relativa).
        **kwargs: Argumentos adicionales del comando.

    Returns:
        str: Salida del comando o mensaje de error amigable.
    """
    try:
        return _ejecutar(cmd_func, NS(target=_target_abs(target), **kwargs))
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en {tool}: {err}"


def _leer_brief(target: str, project: str) -> str:
    """Lee el CONTEXT.md del proyecto (o el de la raíz)."""
    import glob

    candidatos = [
        os.path.join(target, ".context-map", "CONTEXT.md"),
        os.path.join(target, ".context-map", f"CONTEXT-{project}.md") if project else "",
    ]
    candidatos += glob.glob(os.path.join(target, ".context-map", "CONTEXT*.md"))
    for c in candidatos:
        if c and os.path.isfile(c):
            with open(c, encoding="utf-8") as f:
                return f.read()
    return "No se encontró CONTEXT.md — ejecuta `ctxmap build --brief` primero."


def _leer_brief_min(target: str, project: str) -> str:
    """Lee la capa mínima del brief (``CONTEXT.min.md``), con respaldo al completo."""
    import glob

    candidatos = [
        os.path.join(target, ".context-map", "CONTEXT.min.md"),
        os.path.join(target, ".context-map", f"CONTEXT-{project}.min.md") if project else "",
    ]
    candidatos += glob.glob(os.path.join(target, ".context-map", "CONTEXT*.min.md"))
    for c in candidatos:
        if c and os.path.isfile(c):
            with open(c, encoding="utf-8") as f:
                return f.read()
    # Sin capa mínima todavía: devolver el completo (mejor eso que nada).
    return _leer_brief(target, project)


def _seccion_brief(target: str, project: str, seccion: str) -> str:
    """Devuelve solo la sección del brief cuyo título contiene ``seccion``.

    Normaliza acentos y mayúsculas; si no encuentra la sección, lista las
    disponibles para que el agente elija.

    Args:
        target: Directorio del proyecto.
        project: Nombre del proyecto (opcional).
        seccion: Texto a buscar en el título (p. ej. "riesgos", "estado").

    Returns:
        str: La sección encontrada o la lista de secciones disponibles.
    """
    import re
    import unicodedata

    def _norm(texto: str) -> str:
        descompuesto = unicodedata.normalize("NFD", texto.lower())
        return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")

    objetivo = _norm(seccion)
    disponibles: list[str] = []
    for parte in re.split(r"(?m)^##\s+", _leer_brief(target, project))[1:]:
        titulo, _, cuerpo = parte.partition("\n")
        titulo = titulo.strip()
        disponibles.append(titulo)
        if objetivo in _norm(titulo):
            return f"## {titulo}\n{cuerpo}".strip()
    return "Sección no encontrada. Disponibles: " + " · ".join(disponibles)


def _target_abs(target: str) -> str:
    """Resuelve y valida el directorio de proyecto apuntado por la tool.

    Args:
        target: Ruta (posiblemente relativa o con ``~``).

    Returns:
        str: Ruta absoluta normalizada del proyecto.

    Raises:
        ValueError: Si la ruta no existe o no es un directorio.
    """
    resolved = os.path.abspath(os.path.expanduser(target or "."))
    if not os.path.isdir(resolved):
        raise ValueError(f"El target no es un directorio válido: {target!r}")
    return resolved


def _requiere_confirmacion(accion: str, confirm: bool) -> None:
    """Exige confirmación explícita para operaciones destructivas del MCP.

    Args:
        accion: Descripción de la operación destructiva.
        confirm: Flag de confirmación que debe pasar el agente.

    Raises:
        ValueError: Si la operación no está confirmada.
    """
    if not confirm:
        raise ValueError(
            f"Operación destructiva '{accion}' rechazada por seguridad: "
            "pasa confirm=True si estás seguro de ejecutarla."
        )

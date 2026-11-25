"""Instalación del hook de lecturas en el harness (``REG-INI-006``).

El receptor es ``ctxmap hook lectura``: lee el JSON de ``PreToolUse`` por stdin y
anota la ruta. Lo que falta es que el harness lo llame, y cada harness lo declara
en su propio archivo de configuración. Aquí se instala el de Claude Code
(``.claude/settings.json``), que es el formato con más usuarios.

La instalación **fusiona**: se añade nuestra entrada y se respeta lo que el dueño
tenga escrito. Sobrescribir la configuración de otro sería exactamente el atajo
que ``REG-EJE-004`` prohíbe.
"""

from __future__ import annotations

import json
import os
from typing import Any

#: Comando canónico cuando el proyecto no trae intérprete propio.
COMANDO = "ctxmap hook lectura --quiet"

#: Intérpretes del proyecto que se prefieren al binario global, en orden.
INTERPRETES = (os.path.join(".venv", "Scripts", "python.exe"), os.path.join(".venv", "bin", "python"))

#: Matcher de herramientas cuya entrada trae una ruta de archivo.
MATCHER = "Read|Edit|Write|MultiEdit|NotebookEdit"

#: Fragmento con el que se reconoce nuestra entrada dentro de la lista de hooks.
#: Se busca en el comando y no en una clave propia: los harnesses validan su
#: esquema y una clave desconocida es una configuración inválida, no una marca.
MARCA = "hook lectura"

#: Ruta de la configuración de Claude Code dentro del proyecto.
CONFIG = os.path.join(".claude", "settings.json")


def comando(project_dir: str = ".") -> str:
    """Comando que el harness ejecutará en cada lectura.

    Se prefiere el intérprete del proyecto (``.venv``) porque el binario global
    ``ctxmap`` puede estar desactualizado: un ``hook lectura`` que no existe en
    esa versión sale con código 2, y en un ``PreToolUse`` **el 2 bloquea la
    herramienta**. Una regla que impide leer el código para poder cumplirla sería
    una trampa.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        str: Comando listo para el harness.
    """
    for candidato in INTERPRETES:
        ruta = os.path.join(project_dir, candidato)
        if os.path.exists(ruta):
            return f'"{os.path.abspath(ruta)}" -m context_map.cli hook lectura --quiet'
    return COMANDO


def _entrada(project_dir: str = ".") -> dict[str, Any]:
    """Entrada de ``PreToolUse`` que se añade a la configuración."""
    return {
        "matcher": MATCHER,
        "hooks": [
            {
                "type": "command",
                "command": comando(project_dir),
                "timeout": 10,
            }
        ],
    }


def _config_leida(project_dir: str) -> dict[str, Any]:
    """Configuración existente del proyecto (vacía si no hay o está rota)."""
    ruta = os.path.join(project_dir, CONFIG)
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def ya_instalado(project_dir: str = ".") -> bool:
    """Indica si el hook de lecturas ya está en la configuración.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        bool: ``True`` si nuestra entrada está presente.
    """
    pre = _config_leida(project_dir).get("hooks", {})
    if not isinstance(pre, dict):
        return False
    for entrada in pre.get("PreToolUse", []) or []:
        if not isinstance(entrada, dict):
            continue
        for hook in entrada.get("hooks", []) or []:
            if isinstance(hook, dict) and MARCA in str(hook.get("command", "")):
                return True
    return False


def instalar_hook_lectura(project_dir: str = ".") -> dict[str, Any]:
    """Añade el hook de lecturas a ``.claude/settings.json`` sin pisar nada.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        dict: ``status`` (``OK``, ``WARN`` o ``FAIL``) y ``message``.
    """
    if ya_instalado(project_dir):
        return {"status": "OK", "message": "El hook de lecturas ya estaba instalado."}

    config = _config_leida(project_dir)
    hooks = config.get("hooks")
    if not isinstance(hooks, dict):
        hooks = {}
    pre = hooks.get("PreToolUse")
    if not isinstance(pre, list):
        pre = []
    pre.append(_entrada(project_dir))
    hooks["PreToolUse"] = pre
    config["hooks"] = hooks

    ruta = os.path.join(project_dir, CONFIG)
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8", newline="\n") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as err:
        return {"status": "FAIL", "message": f"No se pudo escribir {CONFIG}: {err}"}

    return {
        "status": "OK",
        "message": (
            f"Hook de lecturas instalado en {CONFIG}. Solo cubre harnesses con "
            "hooks (Claude Code, pi): en un chat manual no hay evidencia que juzgar."
        ),
    }

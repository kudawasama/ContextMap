"""Instalador y gestor transparente de Git Hooks de ContextMap.

Inyecta scripts pre-commit y post-commit en repositorios Git para garantizar
que el mapa de contexto y el brief CONTEXT.md se sincronicen en cada commit.
"""

from __future__ import annotations

import os
import stat

PRE_COMMIT_SCRIPT = """#!/bin/sh
# ContextMap Auto-Sync Pre-Commit Hook
# Prioriza el código local del repo (python -m context_map.cli) antes que
# el binario global 'ctxmap', que puede estar desactualizado.
# Se usa build --brief (SIN --clean) para NO destruir las notas manuales
# del vault (zona protegida .manual/ y notas con preserve: true).
# --import-sessions: cada commit registra la memoria viva (sesiones de Hermes).
if python -m context_map.cli build --brief --quiet --import-sessions 2>/dev/null; then
    git add .context-map CONTEXT.md AGENTS.md ACTIVE.md 2>/dev/null || true
    exit 0
fi
if command -v ctxmap >/dev/null 2>&1; then
    ctxmap build --brief --quiet --import-sessions
    git add .context-map CONTEXT.md AGENTS.md ACTIVE.md 2>/dev/null || true
fi
"""

POST_COMMIT_SCRIPT = """#!/bin/sh
# ContextMap Auto-Maintenance Post-commit Hook
# Registra la actividad del commit en la memoria viva.
if command -v ctxmap >/dev/null 2>&1; then
    ctxmap refresh .
else
    python -m context_map.cli refresh .
fi
"""


def _hacer_ejecutable(ruta: str) -> None:
    """Otorga permisos de ejecución al archivo del hook en sistemas POSIX/Linux/macOS."""
    try:
        st = os.stat(ruta)
        os.chmod(ruta, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    except Exception:
        pass


def instalar_git_hooks(project_dir: str = ".", force: bool = False) -> dict[str, str]:
    """Instala los hooks `pre-commit` y `post-commit` en la carpeta `.git/hooks/`.

    Args:
        project_dir (str): Directorio raíz del proyecto Git.
        force (bool): Si es True, sobrescribe hooks existentes.

    Returns:
        dict[str, str]: Resultado del proceso de instalación por hook.
    """
    project_dir = os.path.abspath(project_dir)
    git_dir = os.path.join(project_dir, ".git")

    if not os.path.isdir(git_dir):
        return {"status": "FAIL", "message": f"'{project_dir}' no es un repositorio Git válido (.git no existe)."}

    hooks_dir = os.path.join(git_dir, "hooks")
    os.makedirs(hooks_dir, exist_ok=True)

    resultados: dict[str, str] = {"status": "OK"}

    hooks = {
        "pre-commit": PRE_COMMIT_SCRIPT,
        "post-commit": POST_COMMIT_SCRIPT,
    }

    for name, content in hooks.items():
        hpath = os.path.join(hooks_dir, name)
        if os.path.exists(hpath) and not force:
            with open(hpath, encoding="utf-8", errors="ignore") as f:
                existing = f.read()
            if "ContextMap" in existing:
                resultados[name] = "ya instalado"
                continue

            resultados[name] = "omitido (archivo existe, usa --force para sobrescribir)"
            continue

        try:
            with open(hpath, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            _hacer_ejecutable(hpath)
            resultados[name] = "instalado con éxito"
        except Exception as e:
            resultados[name] = f"error al escribir: {e}"

    return resultados


def desinstalar_git_hooks(project_dir: str = ".") -> dict[str, str]:
    """Remueve los hooks de ContextMap instalados en `.git/hooks/`.

    Args:
        project_dir (str): Directorio raíz del proyecto Git.

    Returns:
        dict[str, str]: Resultado del proceso por hook.
    """
    project_dir = os.path.abspath(project_dir)
    hooks_dir = os.path.join(project_dir, ".git", "hooks")

    if not os.path.isdir(hooks_dir):
        return {"status": "FAIL", "message": "No existe directorio .git/hooks/."}

    resultados: dict[str, str] = {"status": "OK"}
    for name in ("pre-commit", "post-commit"):
        hpath = os.path.join(hooks_dir, name)
        if not os.path.exists(hpath):
            resultados[name] = "no existía"
            continue

        try:
            with open(hpath, encoding="utf-8", errors="ignore") as f:
                existing = f.read()
            if "ContextMap" in existing:
                os.remove(hpath)
                resultados[name] = "desinstalado"
            else:
                resultados[name] = "omitido (pertenece a otra herramienta)"
        except Exception as e:
            resultados[name] = f"error al borrar: {e}"

    return resultados

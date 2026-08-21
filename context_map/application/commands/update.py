"""Comando update: actualización automática de ContextMap desde GitHub.

Gestiona la descarga, clonación/pull del repositorio y la
reinstalación de la herramienta global vía uv/pipx.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

from context_map.application.commands._helpers import safe_rmtree


def cmd_update(args) -> None:
    """Actualiza ContextMap a la última versión desde GitHub.

    Flujo:
        1. Verificar que git está disponible
        2. Clonar o actualizar el repositorio temporal
        3. Instalar con uv/pipx --force --reinstall
        4. Mostrar versión instalada

    Args:
        args: Namespace de argparse (sin argumentos adicionales)
    """
    print("Actualizando ContextMap...")
    print()

    # Verificar si hay git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Git no encontrado. Instala git primero.")
        print("   https://git-scm.com/downloads")
        return

    repo_url = "https://github.com/kudawasama/ContextMap.git"
    print(f"Buscando última versión desde: {repo_url}")

    # Método 1: uv tool install directo (Rápido, Atómico y seguro en Windows)
    if shutil.which("uv"):
        print("   Actualizando paquete global con 'uv tool'...")
        cmd = ["uv", "tool", "install", "--force", f"git+{repo_url}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ Actualización completada exitosamente con uv.")
            _mostrar_version_final()
            return

    # Método 2: pipx install --force
    if shutil.which("pipx"):
        print("   Actualizando paquete global con 'pipx'...")
        cmd = ["pipx", "install", "--force", f"git+{repo_url}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            print("✅ Actualización completada exitosamente con pipx.")
            _mostrar_version_final()
            return

    # Método 3: Repositorio temporal git pull + fallback
    update_dir = os.path.join(os.path.expanduser("~"), ".context-map-update")

    print(f"Descargando desde: {repo_url}")

    def _es_repo_valido(path: str) -> bool:
        """Verifica si un directorio es un repo git válido."""
        r = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"

    # Si existe pero no es repo válido, lo borra y empieza de cero
    result = None
    if os.path.exists(update_dir):
        if _es_repo_valido(update_dir):
            print("   Actualizando repositorio existente...")
            result = subprocess.run(
                ["git", "-C", update_dir, "pull"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print(f"   Error al actualizar: {result.stderr}")
                safe_rmtree(update_dir)
                result = None
        else:
            print("   Directorio corrupto, clonando de nuevo...")
            safe_rmtree(update_dir)
            result = None

    if result is None or result.returncode != 0:
        # Asegurar que no queden restos del directorio corrupto
        if os.path.exists(update_dir):
            safe_rmtree(update_dir)
        print("   Clonando repositorio...")
        result = subprocess.run(
            ["git", "clone", repo_url, update_dir],
            capture_output=True, text=True, timeout=120,
        )

    if result.returncode != 0:
        print(f"Error al descargar: {result.stderr}")
        return

    print("Repositorio actualizado")
    print()

    # Instalar como herramienta global (uv tool o pipx)
    print("Instalando nueva version...")
    if shutil.which("uv"):
        installer = ["uv", "tool", "install", "--force", "--reinstall", update_dir]
    elif shutil.which("pipx"):
        installer = ["pipx", "install", "--force", update_dir]
    else:
        print("Se requiere 'uv' o 'pipx' para instalar globalmente.")
        print("   Instala uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return

    result = subprocess.run(installer, capture_output=True, text=True)
    stderr_lower = result.stderr.lower()

    if result.returncode == 0:
        print("Instalacion completada")
    elif "os error 32" in stderr_lower or ("archivo" in stderr_lower and "utilizado" in stderr_lower):
        # Windows: entrypoint bloqueado porque el .exe está en uso
        print("Codigo actualizado, pero el entrypoint esta bloqueado en Windows.")
        print("   Para completar la actualizacion, ejecuta en una shell NUEVA:")
        print()
        if shutil.which("uv"):
            print(f"     uv tool install --force --reinstall {update_dir}")
        elif shutil.which("pipx"):
            print(f"     pipx install --force {update_dir}")
        print()
        print("   El paquete ya se actualizo; los comandos nuevos deberian funcionar.")
    else:
        print(f"Error al instalar: {result.stderr}")
        return

    # Limpiar directorio temporal
    shutil.rmtree(update_dir, ignore_errors=True)
    print()

def _mostrar_version_final() -> None:
    """Muestra la versión instalada de ContextMap de forma segura."""
    print("Versión instalada:")
    try:
        from context_map.infrastructure.version_check import version_local

        print(f"   {version_local()}")
    except Exception:
        result = subprocess.run(
            [sys.executable, "-m", "context_map.cli", "--version"],
            capture_output=True, text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            print(f"   {result.stdout.strip()}")
        else:
            result = subprocess.run(
                ["ctxmap", "--version"],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                print(f"   {result.stdout.strip()}")
            else:
                print("   ContextMap (versión desconocida)")

    print()
    print("💡 Tus datos guardados (.context-map/, personal.db, notas manuales) se mantienen 100% intactos.")
    print("   Para sincronizar la estructura en tus proyectos existentes: ctxmap refresh .")

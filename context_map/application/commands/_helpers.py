"""Helpers compartidos para los comandos del CLI.

Centraliza constantes de directorios, funciones de utilidad y
operaciones comunes que varios comandos necesitan reutilizar.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import List

from context_map.core.models import Event, Node, Edge
from context_map.core.parsing import (
    _dedup_events,
    load_events_from_chat_folder,
    load_events_from_jsonl,
    events_to_model,
)
from context_map.core.storage import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)

# ============================================================
# Constantes de directorios
# ============================================================

CONTEXT_DIR: str = ".context-map"
STATE_DIR: str = os.path.join(CONTEXT_DIR, "state")
MAPS_DIR: str = os.path.join(CONTEXT_DIR, "maps")
HISTORY_DIR: str = os.path.join(CONTEXT_DIR, "maps", "HISTORY")
CHATS_DIR: str = os.path.join(CONTEXT_DIR, "chats")
RAW_DIR: str = os.path.join(CONTEXT_DIR, "raw")


def vault_dir(project_name: str | None = None) -> str:
    """Retorna el directorio del vault, incluyendo el nombre del proyecto si existe.

    Ej: vault_dir()         -> ".context-map/vault"
        vault_dir("MiApp")  -> ".context-map/vault-MiApp"
    """
    if project_name:
        safe = project_name.strip().replace(" ", "-").replace("/", "-").replace("\\", "-")
        return os.path.join(CONTEXT_DIR, f"vault-{safe}")
    return os.path.join(CONTEXT_DIR, "vault")


# ============================================================
# Funciones de utilidad
# ============================================================

def ahora() -> str:
    """Timestamp actual en formato ISO 8601 sin microsegundos."""
    return datetime.now().isoformat(timespec="seconds")


def _git_repo_name(target_dir: str = ".") -> str | None:
    """Extrae el nombre del repositorio de GitHub desde .git/config de forma agnóstica al SO.

    Args:
        target_dir (str): Ruta base del proyecto.

    Returns:
        str | None: Nombre del repo remoto (ej. 'ContextMap') o None si no existe.
    """
    try:
        git_config = os.path.join(target_dir, ".git", "config")
        if os.path.exists(git_config):
            with open(git_config, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str.startswith("url =") or line_str.startswith("url="):
                        raw_url = line_str.split("=", 1)[1].strip()
                        repo_name = raw_url.split("/")[-1].split(":")[-1]
                        if repo_name.endswith(".git"):
                            repo_name = repo_name[:-4]
                        if repo_name:
                            return repo_name
    except Exception:
        pass
    return None


def project_name(args) -> str:
    """Obtiene el nombre del proyecto con la siguiente jerarquía de prioridad:
    1. Argumento CLI explícito (--project).
    2. Configuración declarativa (.contextmap.toml / pyproject.toml en target_dir).
    3. Nombre del Repositorio de GitHub de primera instancia (vía .git/config en target_dir).
    4. Nombre de la Carpeta del Proyecto de segunda instancia (target_dir).

    Args:
        args: Namespace de argparse con atributo opcional ``project`` o ``target``.

    Returns:
        str: Nombre descriptivo del proyecto (ej. 'vault-ContextMap').
    """
    name = getattr(args, "project", None)
    if name and name != "Repo":
        return name

    target_dir = getattr(args, "target", ".") or "."

    from context_map.core.storage.config_loader import load_project_config
    cfg = load_project_config(target_dir)
    if cfg.project_name:
        return cfg.project_name

    # 1ª Instancia: Nombre del Repositorio GitHub
    repo_name = _git_repo_name(target_dir)
    if repo_name:
        return repo_name

    # 2ª Instancia: Nombre de la Carpeta del Proyecto
    folder = os.path.basename(os.path.abspath(target_dir))
    return folder or "Repo"


def ensure_dirs(_proj: str | None = None) -> None:
    """Crea el árbol de directorios de .context-map/.

    NOTA: el vault se crea bajo demanda en build/sync, no acá.
    """
    for path in [STATE_DIR, MAPS_DIR, HISTORY_DIR, CHATS_DIR, RAW_DIR]:
        os.makedirs(path, exist_ok=True)


def resolve_vault_mode(args) -> str:
    """Resuelve el modo de generación del vault desde los argumentos del CLI.

    El flag ``--raw`` tiene prioridad sobre ``--mode`` para mayor comodidad.

    Args:
        args: Namespace de argparse

    Returns:
        ``'consolidated'`` o ``'raw'``
    """
    if getattr(args, "raw", False):
        return "raw"
    return getattr(args, "mode", "hierarchical")


def clean_vault_dir(project_name: str | None = None) -> None:
    """Elimina el contenido del vault para una reconstrucción limpia.

    Si se pasa project_name, limpia .context-map/vault-{Nombre}/.
    """
    vdir = vault_dir(project_name)
    if os.path.isdir(vdir):
        shutil.rmtree(vdir, ignore_errors=True)
    os.makedirs(vdir, exist_ok=True)
    print(f"[clean] Vault limpiado: {vdir}")


def safe_rmtree(path: str) -> None:
    """Elimina directorios de forma segura, con reintentos para Windows.

    En Windows, archivos bloqueados por antivirus o handles abiertos
    pueden impedir la eliminación. Se realizan hasta 3 reintentos
    con fallback a ``cmd /c rd /s /q``.

    Args:
        path: Ruta absoluta del directorio a eliminar
    """
    import subprocess

    if not os.path.isdir(path):
        return
    shutil.rmtree(path, ignore_errors=True)
    if os.path.isdir(path):
        for _attempt in range(3):
            shutil.rmtree(path, ignore_errors=True)
            if not os.path.isdir(path):
                break
            try:
                subprocess.run(
                    ["cmd", "/c", "rd", "/s", "/q", path],
                    capture_output=True, timeout=10,
                )
            except Exception:
                pass


def append_nodes_edges(nodes: List[Node], edges: List[Edge]) -> None:
    """Persiste nodos y aristas en archivos JSONL incrementales.

    Args:
        nodes: Lista de nodos a persistir
        edges: Lista de aristas a persistir
    """
    append_jsonl(os.path.join(STATE_DIR, "graph.jsonl"), [n.to_dict() for n in nodes])
    append_jsonl(os.path.join(STATE_DIR, "edges.jsonl"), [e.to_dict() for e in edges])


def collect_events() -> List[Event]:
    """Reúne y deduplica eventos desde las carpetas de chats y raw.

    Returns:
        Lista de eventos deduplicados
    """
    events: List[Event] = []
    events.extend(load_events_from_chat_folder(CHATS_DIR))
    events.extend(load_events_from_jsonl(os.path.join(RAW_DIR, "events.jsonl")))
    return _dedup_events(events)

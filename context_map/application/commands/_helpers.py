"""Helpers compartidos para los comandos del CLI.

Centraliza constantes de directorios, funciones de utilidad y
operaciones comunes que varios comandos necesitan reutilizar.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime

from context_map.core.models import Edge, Event, Node
from context_map.core.parsing import (
    _dedup_events,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.storage import (
    append_jsonl,
)

logger = logging.getLogger(__name__)

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
            with open(git_config, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str.startswith("url =") or line_str.startswith("url="):
                        raw_url = line_str.split("=", 1)[1].strip()
                        repo_name = raw_url.split("/")[-1].split(":")[-1]
                        if repo_name.endswith(".git"):
                            repo_name = repo_name[:-4]
                        if repo_name:
                            return repo_name
    except Exception as err:
        logger.debug("No se pudo leer configuración remota de git: %s", err)
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
        return str(name)

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


def _leer_frontmatter_preserve(fpath: str) -> bool:
    """Detecta si una nota del vault pide ser preservada (frontmatter preserve: true).

    Args:
        fpath (str): Ruta del archivo Markdown.

    Returns:
        bool: True si el frontmatter contiene ``preserve: true``.
    """
    try:
        with open(fpath, encoding="utf-8") as f:
            primeras = [next(f, "") for _ in range(10)]
    except Exception:
        return False
    if not primeras or primeras[0].strip() != "---":
        return False
    for linea in primeras[1:]:
        if linea.strip().startswith("---"):
            break
        clave = linea.strip().lower().replace(" ", "")
        if clave.startswith("preserve:") and "true" in clave:
            return True
    return False


def _copiar_dir(origen: str, destino: str) -> None:
    """Copia recursiva de un directorio (sin sobrescribir destino existente)."""
    if not os.path.isdir(origen):
        return
    for raiz, _dirs, archivos in os.walk(origen):
        for archivo in archivos:
            src = os.path.join(raiz, archivo)
            rel = os.path.relpath(src, origen)
            dst = os.path.join(destino, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)


def clean_vault_dir(project_name: str | None = None) -> int:
    """Elimina el contenido del vault para una reconstrucción limpia.

    **NUNCA borra el trabajo manual.** Preserva:
    - La carpeta reservada ``.manual/`` completa (zona protegida del usuario).
    - Cualquier nota con frontmatter ``preserve: true`` (esté donde esté).
    - Las notas de planes manuales en ``5.0-BACKLOG`` (comportamiento previo).

    Args:
        project_name (str | None): Nombre del proyecto (para el vault nombrado).

    Returns:
        int: Cantidad de archivos manuales preservados.
    """
    vdir = vault_dir(project_name)
    temp_preservados = os.path.join(CONTEXT_DIR, "_preservar_manual")

    # 1. Respaldo de la zona protegida .manual/ + notas preserve:true
    manual_dir = os.path.join(vdir, ".manual")
    preservados: dict[str, str] = {}
    if os.path.isdir(manual_dir):
        # Preservar la carpeta .manual/ completa (incluido el nombre de la carpeta)
        destino_manual = os.path.join(temp_preservados, ".manual")
        os.makedirs(destino_manual, exist_ok=True)
        _copiar_dir(manual_dir, destino_manual)

    # Notas preserve:true en cualquier parte del vault (excepto .manual/, ya respaldado)
    if os.path.isdir(vdir):
        for raiz, _dirs, archivos in os.walk(vdir):
            if ".manual" in raiz.split(os.sep):
                continue
            for fname in archivos:
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(raiz, fname)
                if _leer_frontmatter_preserve(fpath):
                    rel = os.path.relpath(fpath, vdir)
                    dst = os.path.join(temp_preservados, rel)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    try:
                        shutil.copy2(fpath, dst)
                    except Exception as err:
                        logger.debug("No se pudo respaldar nota preserve %s: %s", rel, err)

    # 2. Respaldo histórico: notas manuales en 5.0-BACKLOG
    backlog_dir = os.path.join(vdir, "5.0-BACKLOG")
    if os.path.isdir(backlog_dir):
        for fname in os.listdir(backlog_dir):
            if fname.endswith(".md") and fname not in ("5.0-BACKLOG.md", "5.1-Tareas.md"):
                fpath = os.path.join(backlog_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        preservados[fname] = f.read()
                except Exception as err:
                    logger.debug("No se pudo respaldar nota %s: %s", fname, err)

    # 3. Borrar el vault y recrearlo
    if os.path.isdir(vdir):
        shutil.rmtree(vdir, ignore_errors=True)
    os.makedirs(vdir, exist_ok=True)

    # 4. Restaurar .manual/ y preserve:true
    n_restaurados = 0
    if os.path.isdir(temp_preservados):
        _copiar_dir(temp_preservados, vdir)
        n_restaurados = sum(
            len(archivos)
            for _raiz, _dirs, archivos in os.walk(temp_preservados)
        )
        shutil.rmtree(temp_preservados, ignore_errors=True)

    # 5. Restaurar backlog manual
    if preservados:
        target_backlog = os.path.join(vdir, "5.0-BACKLOG")
        os.makedirs(target_backlog, exist_ok=True)
        for fname, content in preservados.items():
            with open(os.path.join(target_backlog, fname), "w", encoding="utf-8") as f:
                f.write(content)
        n_restaurados += len(preservados)

    print(f"[clean] Vault limpiado: {vdir} (preservadas {n_restaurados} notas manuales)")
    return n_restaurados


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
            except Exception as err:
                logger.debug("No se pudo forzar borrado de %s: %s", path, err)


def registrar_build_info(
    project_name: str | None,
    clean: bool,
    manuales_preservadas: int = 0,
) -> None:
    """Registra metadatos del último build en ``state/last_build.json``.

    Permite que ``ctxmap check`` alerte si el último build usó ``--clean``
    (destructivo) y cuántas notas manuales se preservaron.

    Args:
        project_name (str | None): Nombre del proyecto.
        clean (bool): Si el último build usó --clean.
        manuales_preservadas (int): Cantidad de notas manuales preservadas.
    """
    os.makedirs(STATE_DIR, exist_ok=True)
    info = {
        "clean": bool(clean),
        "manuales_preservadas": int(manuales_preservadas),
        "timestamp": ahora(),
    }
    try:
        with open(os.path.join(STATE_DIR, "last_build.json"), "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
    except Exception as err:
        logger.debug("No se pudo registrar last_build.json: %s", err)


def append_nodes_edges(nodes: list[Node], edges: list[Edge]) -> None:
    """Persiste nodos y aristas en archivos JSONL incrementales.

    Args:
        nodes: Lista de nodos a persistir
        edges: Lista de aristas a persistir
    """
    append_jsonl(os.path.join(STATE_DIR, "graph.jsonl"), [n.to_dict() for n in nodes])
    append_jsonl(os.path.join(STATE_DIR, "edges.jsonl"), [e.to_dict() for e in edges])


def collect_events() -> list[Event]:
    """Reúne y deduplica eventos desde las carpetas de chats y raw.

    Returns:
        Lista de eventos deduplicados
    """
    events: list[Event] = []
    events.extend(load_events_from_chat_folder(CHATS_DIR))
    events.extend(load_events_from_jsonl(os.path.join(RAW_DIR, "events.jsonl")))
    return _dedup_events(events)

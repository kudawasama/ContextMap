"""Commands: Comandos del CLI unificados.

Todos los comandos están registrados aquí para evitar fragmentación.
Cada comando es una función que recibe argparse.Namespace.
"""

from __future__ import annotations

import os
import sys
import shutil
from typing import List

from context_map.core.models import Event, Node, Edge
from context_map.core.parser import (
    _dedup_events,
    events_to_model,
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.store import (
    append_jsonl,
    load_jsonl,
    snapshot_map,
    write_map,
)
from context_map.presentation.writer import render_active_map, render_obsidian_vault
from context_map.presentation.brief import generar_brief
from context_map.domain.sync import sync_incremental
from context_map.domain.scanner import escanear_y_generar_eventos, guardar_eventos_escaneados
from context_map.domain.checker import analizar_readiness, formatear_readiness
from context_map.domain.reporter import generar_semanal, guardar_reporte
from context_map.domain.doctor import run as doctor_run, DoctorReport
from context_map.infrastructure.integrations.git import leer_historial_git
from context_map.infrastructure.integrations.hermes import importar_sesiones
from context_map.infrastructure.integrations.chat_export import importar_chat
from context_map.infrastructure.integrations.antigravity import importar_antigravity

# Constantes de directorios
CONTEXT_DIR = ".context-map"
STATE_DIR = os.path.join(CONTEXT_DIR, "state")
MAPS_DIR = os.path.join(CONTEXT_DIR, "maps")
HISTORY_DIR = os.path.join(CONTEXT_DIR, "maps", "HISTORY")
CHATS_DIR = os.path.join(CONTEXT_DIR, "chats")
RAW_DIR = os.path.join(CONTEXT_DIR, "raw")
VAULT_DIR = os.path.join(CONTEXT_DIR, "vault")


def _ahora() -> str:
    """Timestamp actual."""
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _project_name(args) -> str:
    """Obtiene nombre del proyecto: argumento o directorio actual."""
    name = getattr(args, "project", None)
    if name and name != "Repo":
        return name
    return os.path.basename(os.getcwd()) or "Repo"

def _ensure_dirs() -> None:
    """Prepara el árbol de directorios."""
    for p in [STATE_DIR, MAPS_DIR, HISTORY_DIR, CHATS_DIR, RAW_DIR, VAULT_DIR]:
        os.makedirs(p, exist_ok=True)


def _append_nodes_edges(nodes: List[Node], edges: List[Edge]) -> None:
    """Persiste nodos y aristas como JSONL."""
    append_jsonl(os.path.join(STATE_DIR, "graph.jsonl"), [n.to_dict() for n in nodes])
    append_jsonl(os.path.join(STATE_DIR, "edges.jsonl"), [e.to_dict() for e in edges])


def _collect_events():
    """Reune eventos desde carpetas."""
    events = []
    events.extend(load_events_from_chat_folder(CHATS_DIR))
    events.extend(load_events_from_jsonl(os.path.join(RAW_DIR, "events.jsonl")))
    return _dedup_events(events)


def _do_sync(args, project_name=None):
    """Ejecuta sync y regenera vault."""
    stats = sync_incremental(
        chats_dir=CHATS_DIR,
        raw_dir=RAW_DIR,
        state_dir=STATE_DIR,
    )

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(project_name or "Repo", nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(project_name or "Repo", nodes, edges, vault_dir)

    print(f"sync: nodos {stats['nodos_existentes']} → {stats['nodos_existentes'] + stats['nodos_agregados']}")
    print(f"vault: {vault_dir}")
    return nodes, edges


# === COMANDOS ===

def cmd_init(_args):
    """Crea el directorio .context-map."""
    _ensure_dirs()
    print("init:ok ->", os.path.abspath(CONTEXT_DIR))


def cmd_build(args):
    """Genera el mapa contextual y snapshot."""
    _ensure_dirs()
    extra_events = _collect_events()
    if extra_events:
        nodes, edges = events_to_model(extra_events)
        # Estandarizar nodos nuevos antes de persistir
        from context_map.core.standardize import estandarizar_nodos
        nodes = estandarizar_nodos(nodes)
        _append_nodes_edges(nodes, edges)

    # Cargar nodos y re-estandarizar todo (por si quedaron viejos)
    from context_map.core.standardize import estandarizar_nodo
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [estandarizar_nodo(Node.from_dict(r)) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    md = render_active_map(_project_name(args), nodes, edges)
    write_map(md)

    vault_dir = os.path.join(CONTEXT_DIR, "vault")
    render_obsidian_vault(_project_name(args), nodes, edges, vault_dir)

    # Snapshot
    snapshot_name = getattr(args, "snapshot_name", "") or None
    snap = snapshot_map(nodes=nodes, edges=edges, name=snapshot_name)
    if snap:
        print(f"snapshot: {snap}")

    # Brief si se pide
    if getattr(args, "brief", False):
        brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
        readiness = analizar_readiness(".")
        generar_brief(_project_name(args), nodes, edges, readiness.score, brief_path)
        print(f"brief: {brief_path}")

    print("build:ok -> ACTIVE.md")
    print(f"vault:ok -> {vault_dir}")


def cmd_scan(args):
    """Escanea el proyecto y genera eventos."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Escaneando: {os.path.abspath(ruta)}")

    eventos = escanear_y_generar_eventos(ruta)

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        _do_sync(args, _project_name(args))


def cmd_sync(args):
    """Sync incremental."""
    _ensure_dirs()
    _do_sync(args, _project_name(args))


def cmd_check(args):
    """Verifica readiness del proyecto."""
    ruta = args.target or os.getcwd()
    resultado = analizar_readiness(ruta)
    print(formatear_readiness(resultado))


def cmd_import_git(args):
    """Importa historial de git."""
    _ensure_dirs()

    ruta = args.target or os.getcwd()
    print(f"Leyendo historial git de: {os.path.abspath(ruta)}")

    history = leer_historial_git(ruta, limite=args.limit or 50)

    if not history.commits:
        print("No se encontraron commits o no es un repositorio git")
        return

    print(f"Commits encontrados: {len(history.commits)}")
    print(f"Tags: {len(history.tags)}")

    eventos = [
        Event(
            type="BASE",
            text=f"Repositorio git con {history.total_commits} commits totales, branch: {history.branch_actual}",
            timestamp=_ahora(),
            source="git",
            tags=["git", "repo"],
        )
    ]

    for commit in history.commits[:20]:
        msg_lower = commit.mensaje.lower()
        if any(kw in msg_lower for kw in ["fix", "bug", "correc", "patch"]):
            tipo = "CORRECCION"
        elif any(kw in msg_lower for kw in ["feat", "add", "nuevo", "new"]):
            tipo = "IDEA"
        elif any(kw in msg_lower for kw in ["test", "qa"]):
            tipo = "PRUEBA"
        elif any(kw in msg_lower for kw in ["doc", "readme", "changelog"]):
            tipo = "CAMBIO"
        else:
            tipo = "CAMBIO"

        eventos.append(Event(
            type=tipo,
            text=f"[{commit.sha[:7]}] {commit.mensaje}",
            timestamp=commit.fecha or _ahora(),
            source="git",
            tags=["commit", tipo.lower()],
        ))

    for tag in history.tags[:10]:
        eventos.append(Event(
            type="HITO",
            text=f"Release tag: {tag}",
            timestamp=_ahora(),
            source="git",
            tags=["tag", "release"],
        ))

    output = os.path.join(RAW_DIR, "events.jsonl")
    guardados = guardar_eventos_escaneados(eventos, output)
    print(f"Eventos nuevos guardados: {guardados}")

    if guardados > 0:
        _do_sync(args, _project_name(args))


def cmd_import_sessions(args):
    """Importa sesiones de Hermes."""
    _ensure_dirs()

    print("Buscando base de datos de sesiones...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_sesiones(
        db_path=args.db,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Sesiones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, _project_name(args))


def cmd_import_chat(args):
    """Importa un archivo de chat."""
    _ensure_dirs()

    if not args.file:
        print("Error: especifica un archivo con --file")
        return

    print(f"Importando chat: {args.file}")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_chat(args.file, output)

    print(f"Eventos importados: {importados}")

    if importados > 0:
        _do_sync(args, _project_name(args))


def cmd_weekly(args):
    """Genera reporte semanal."""
    _ensure_dirs()

    dias = args.days or 7
    output = os.path.join(MAPS_DIR, f"semanal-{dias}d.md")

    print(f"Generando reporte de los últimos {dias} días...")

    reporte = guardar_reporte(STATE_DIR, output, dias)

    print(f"Reporte generado: {reporte}")
    print("")
    with open(reporte, "r", encoding="utf-8") as f:
        lineas = f.readlines()[:30]
        print("".join(lineas))


def cmd_watch(args):
    """Observa cambios y regenera."""
    print(f"Observando cambios cada {args.interval} segundos... (Ctrl+C para salir)")

    import time
    last_mtime = 0

    while True:
        graph_path = os.path.join(STATE_DIR, "graph.jsonl")
        if os.path.exists(graph_path):
            current_mtime = os.path.getmtime(graph_path)
            if current_mtime > last_mtime:
                last_mtime = current_mtime
                print("Detectado cambio, regenerando...")
                try:
                    _do_sync(args, "Repo")
                except Exception as e:
                    print(f"Error: {e}")
        time.sleep(args.interval)


def cmd_brief(args):
    """Genera brief para agentes de IA."""
    _ensure_dirs()

    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    e_records = load_jsonl(os.path.join(STATE_DIR, "edges.jsonl"))
    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in e_records]

    if not nodes:
        print("No hay nodos. Ejecuta 'ctxmap build' primero.")
        return

    readiness = analizar_readiness(".")
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")

    generar_brief(_project_name(args), nodes, edges, readiness.score, brief_path)
    print(f"brief:ok -> {brief_path}")


def cmd_import_antigravity(args):
    """Importa chats de Antigravity IDE."""
    _ensure_dirs()

    print("Importando conversaciones de Antigravity IDE...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_antigravity(
        ide=True,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Conversaciones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, _project_name(args))


def cmd_import_antigravity2(args):
    """Importa chats de Antigravity 2.0."""
    _ensure_dirs()

    print("Importando conversaciones de Antigravity 2.0...")

    output = os.path.join(RAW_DIR, "events.jsonl")
    importados = importar_antigravity(
        ide=False,
        limite=args.limit or 5,
        output_path=output,
    )

    print(f"Conversaciones importadas: {importados} eventos nuevos")

    if importados > 0:
        _do_sync(args, _project_name(args))


def cmd_update(args):
    """Actualiza ContextMap a la última versión desde GitHub."""
    import subprocess
    import sys

    print("🔄 Actualizando ContextMap...")
    print()

    # Verificar si hay git
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("❌ Git no encontrado. Instala git primero.")
        print("   https://git-scm.com/downloads")
        return

    # Clonar/actualizar repo
    repo_url = "https://github.com/kudawasama/ContextMap.git"
    update_dir = os.path.join(os.path.expanduser("~"), ".context-map-update")

    print(f"📥 Descargando desde: {repo_url}")

    def _es_repo_valido(path: str) -> bool:
        """Verifica si un directorio es un repo git válido."""
        r = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip() == "true"

    # Si existe pero no es repo válido, lo borra y empieza de cero
    if os.path.exists(update_dir):
        if _es_repo_valido(update_dir):
            print("   Actualizando repositorio existente...")
            result = subprocess.run(
                ["git", "-C", update_dir, "pull"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                print(f"   Error al actualizar: {result.stderr}")
                # Caerá al clone de abajo
                _safe_rmtree(update_dir)
                result = None
            else:
                result = result  # pull ok
        else:
            print("   Directorio corrupto, clonando de nuevo...")
            _safe_rmtree(update_dir)
            result = None
    else:
        result = None

    if result is None or result.returncode != 0:
        print("   Clonando repositorio...")
        result = subprocess.run(
            ["git", "clone", repo_url, update_dir],
            capture_output=True, text=True, timeout=120,
        )

    if result.returncode != 0:
        print(f"❌ Error al descargar: {result.stderr}")
        return

    print("✅ Repositorio actualizado")
    print()

    # Instalar como herramienta global (uv tool o pipx)
    print("📦 Instalando nueva versión...")
    if shutil.which("uv"):
        # uv tool install crea entorno aislado global
        installer = ["uv", "tool", "install", "--force", update_dir]
    elif shutil.which("pipx"):
        installer = ["pipx", "install", "--force", update_dir]
    else:
        print("❌ Se requiere 'uv' o 'pipx' para instalar globalmente.")
        print("   Instala uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return

    result = subprocess.run(installer, capture_output=True, text=True)
    stderr_lower = result.stderr.lower()

    if result.returncode == 0:
        print("✅ Instalación completada")
    elif "os error 32" in stderr_lower or "archivo" in stderr_lower and "utilizado" in stderr_lower:
        # Windows: entrypoint bloqueado porque el .exe está en uso
        print("⚠️  Código actualizado, pero el entrypoint está bloqueado en Windows.")
        print("   Para completar la actualización, ejecutá en una shell NUEVA:")
        print()
        if shutil.which("uv"):
            print(f"     uv tool install --force {update_dir}")
        elif shutil.which("pipx"):
            print(f"     pipx install --force {update_dir}")
        print()
        print("   El paquete ya se actualizó; los comandos nuevos deberían funcionar.")
    else:
        print(f"❌ Error al instalar: {result.stderr}")
        return
    # Limpiar directorio temporal
    shutil.rmtree(update_dir, ignore_errors=True)
    print()

    # Mostrar versión
    print("📋 Versión instalada:")
    result = subprocess.run(
        [sys.executable, "-m", "context_map.cli", "--version"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"   {result.stdout.strip()}")
    else:
        # Intentar con ctxmap
        result = subprocess.run(
            ["ctxmap", "--version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"   {result.stdout.strip()}")
        else:
            print("   (versión desconocida)")

    print()
    print("💡 Para aplicar cambios a un proyecto existente:")
    print("   ctxmap sync --migrate")
    print()
    print("🧹 Para limpiar archivos temporales:")


def cmd_sync_migrate(args):
    """Sincroniza un proyecto existente con la nueva versión de ContextMap."""
    import json

    _ensure_dirs()

    print("🔄 Sincronizando proyecto con nueva versión...")
    print()

    # 1. Cargar estado actual
    graph_file = os.path.join(STATE_DIR, "graph.jsonl")
    edges_file = os.path.join(STATE_DIR, "edges.jsonl")

    if not os.path.exists(graph_file):
        print("⚠️  No se encontró estado del proyecto.")
        print("   Ejecuta: ctxmap scan . && ctxmap build --project 'Nombre'")
        return

    # 2. Cargar nodos
    records = load_jsonl(graph_file)
    edges_records = load_jsonl(edges_file)

    if not records:
        print("⚠️  No hay nodos en el estado.")
        return

    nodes = [Node.from_dict(r) for r in records]
    edges = [Edge.from_dict(r) for r in edges_records]

    print(f"📊 Estado actual: {len(nodes)} nodos, {len(edges)} aristas")
    print()

    # 3. Aplicar estandarización
    from context_map.core.standardize import estandarizar_nodos
    nodes_estandarizados = estandarizar_nodos(nodes)

    # 4. Guardar cambios
    with open(graph_file, "w", encoding="utf-8") as f:
        for n in nodes_estandarizados:
            f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")

    print("✅ Nodos estandarizados")
    print()

    # 5. Regenerar vault
    project_name = getattr(args, "project", None) or "Repo"
    vault_dir = os.path.join(CONTEXT_DIR, "vault")

    render_obsidian_vault(project_name, nodes_estandarizados, edges, vault_dir)
    print(f"✅ Vault regenerado: {vault_dir}")

    # 6. Regenerar brief
    brief_path = os.path.join(CONTEXT_DIR, "CONTEXT.md")
    from context_map.domain.checker import analizar_readiness
    readiness = analizar_readiness(".")
    from context_map.presentation.brief import generar_brief
    generar_brief(project_name, nodes_estandarizados, edges, readiness.score, brief_path)
    print(f"✅ Brief regenerado: {brief_path}")

    # 7. Resumen de cambios
    print()
    print("📋 Resumen de cambios:")
    print(f"   - Nodos estandarizados: {len(nodes_estandarizados)}")
    print(f"   - Vault regenerado: {vault_dir}")
    print(f"   - Brief regenerado: {brief_path}")
    print()
    print("💡 Para verificar:")
    print("   ctxmap check .")
    print()
    print("💡 Para reconstruir completo:")
    print("   ctxmap build --project 'Nombre'")


def cmd_doctor(args):
    """Diagnostica el entorno y repara problemas conocidos."""
    report = doctor_run()

    for check in report.checks:
        icon = "✅" if check.status == "OK" else "⚠️" if check.status == "WARN" else "❌"
        print(f"{icon} {check.name}: {check.message}")

        if check.fix_applied:
            print(f"   🔧 Reparacion: {check.fix_message}")

        print()

    if report.ok:
        print("👌 Doctor: sin fallos detectados.")
    else:
        print("🧰 Doctor: se detectaron fallos.")
        if any(c.fix_applied for c in report.checks):
            print("   Algunos se intentaron reparar automaticamente.")
        print("   Revisa los mensajes anteriores y reejecuta 'ctxmap doctor' si es necesario.")

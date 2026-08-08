"""Parser principal de argumentos de la CLI.

Define y configura todos los subcomandos disponibles para la interfaz
de línea de comandos de Context Map.
"""

from __future__ import annotations

import argparse


def create_parser() -> argparse.ArgumentParser:
    """Construye y configura el parser principal con sus subcomandos.

    Returns:
        argparse.ArgumentParser: Parser configurado.
    """
    p = argparse.ArgumentParser(
        prog="ctxmap",
        description="Mapa mental narrativo de proyectos para agentes de IA",
    )
    p.add_argument("-v", "--verbose", action="store_true", help="Logs detallados (nivel DEBUG)")
    sub = p.add_subparsers(dest="cmd", help="Comandos disponibles")

    s_auto = sub.add_parser("auto", help="Automatización completa en 1 paso (scan + git + build)")
    s_auto.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_auto.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_auto.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    sub.add_parser("init", help="Crea estructura .context-map/")

    s_build = sub.add_parser("build", help="Genera vault completo")
    s_build.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_build.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_build.add_argument("--snapshot-name", default="", help="Nombre del snapshot")
    s_build.add_argument("--brief", action="store_true", help="Generar brief para agentes")
    s_build.add_argument(
        "--mode",
        choices=["consolidated", "raw", "hierarchical"],
        default="hierarchical",
        help="Modo de generación del vault: 'hierarchical' (por defecto), 'consolidated' o 'raw'",
    )
    s_build.add_argument("--raw", action="store_true", help="Alias para --mode raw")
    s_build.add_argument("--clean", action="store_true", help="Eliminar contenido previo antes de reconstruir")
    s_build.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    s_scan = sub.add_parser("scan", help="Escanea proyecto y genera eventos")
    s_scan.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_scan.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_scan.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    s_hook = sub.add_parser("hook", help="Gestión e instalación de Git pre-commit hooks")
    s_hook.add_argument("action", nargs="?", default="install", help="Acción a realizar ('install')")
    s_hook.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")

    s_sync = sub.add_parser("sync", help="Sync incremental (use --migrate para migración)")
    s_sync.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_sync.add_argument("--migrate", action="store_true", help="Migrar a nueva versión")
    s_sync.add_argument(
        "--mode",
        choices=["consolidated", "raw", "hierarchical"],
        default="hierarchical",
        help="Modo de generación del vault",
    )
    s_sync.add_argument("--raw", action="store_true", help="Alias para --mode raw")
    s_sync.add_argument("--clean", action="store_true", help="Eliminar contenido previo de vault/")

    s_check = sub.add_parser("check", help="Verifica readiness (0-100)")
    s_check.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_check.add_argument("--json", action="store_true", help="Salida JSON")

    s_git = sub.add_parser("import-git", help="Importa historial de commits")
    s_git.add_argument("target", nargs="?", default=".", help="Ruta del repositorio")
    s_git.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_git.add_argument("--limit", type=int, default=50, help="Máximo de commits")

    s_ingest = sub.add_parser("ingest", help="Ingiere documentos externos (MD/TXT/PDF) al mapa de contexto")
    s_ingest.add_argument("target", help="Archivo o directorio de documentos a ingerir")
    s_ingest.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_ingest.add_argument(
        "--mode",
        choices=["consolidated", "raw", "hierarchical"],
        default="hierarchical",
        help="Modo de generación del vault",
    )
    s_ingest.add_argument("--raw", action="store_true", help="Alias para --mode raw")
    s_ingest.add_argument("--brief", action="store_true", help="Regenerar brief tras ingerir")
    s_ingest.add_argument("--quiet", action="store_true", help="Modo silencioso")

    s_sessions = sub.add_parser("import-sessions", help="Importa sesiones de Hermes")
    s_sessions.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_sessions.add_argument("--db", default=None, help="Ruta a sessions.db")
    s_sessions.add_argument("--limit", type=int, default=5, help="Máximo de sesiones")

    s_chat = sub.add_parser("import-chat", help="Importa chats externos")
    s_chat.add_argument("file", help="Ruta al archivo de chat")
    s_chat.add_argument("--project", default="Repo", help="Nombre del proyecto")

    s_weekly = sub.add_parser("weekly", help="Genera reporte semanal")
    s_weekly.add_argument("--days", type=int, default=7, help="Días a reportar")

    s_brief = sub.add_parser("brief", help="Genera brief para agentes de IA")
    s_brief.add_argument("--project", default="Repo", help="Nombre del proyecto")

    s_antigravity = sub.add_parser("import-antigravity", help="Importa chats de Antigravity IDE")
    s_antigravity.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_antigravity.add_argument("--limit", type=int, default=5, help="Máximo de conversaciones")

    sub.add_parser("update", help="Actualiza ContextMap a la última versión")
    sub.add_parser("doctor", help="Diagnostica el entorno y repara problemas conocidos")

    s_adapt = sub.add_parser("adapt", help="Detecta stack/IDE y genera reglas agénticas adaptadas")
    s_adapt.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a analizar")
    s_adapt.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_adapt.add_argument("--overwrite", action="store_true", help="Sobrescribir reglas existentes")
    s_adapt.add_argument("--merge", action="store_true", help="Fusionar: anexa/actualiza bloque ContextMap preservando reglas del usuario")

    return p

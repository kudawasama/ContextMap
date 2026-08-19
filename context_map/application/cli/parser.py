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

    s_refresh = sub.add_parser(
        "refresh",
        help="Actualiza el contexto en 1 paso: scan + build (preservando manuales) + check",
    )
    s_refresh.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_refresh.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_refresh.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    s_wrap = sub.add_parser(
        "wrap",
        help="Cierre de sesión: refresh + resumen de memoria viva registrada vs pendiente",
    )
    s_wrap.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_wrap.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_wrap.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    sub.add_parser(
        "mcp",
        help="Arranca el servidor MCP (stdio) que expone las herramientas de ctxmap como tools",
    )

    s_enrich = sub.add_parser("enrich", help="Enriquece el código con docstrings función por función usando Ollama local o AST")
    s_enrich.add_argument("path", nargs="?", default=".", help="Ruta del archivo o directorio a enriquecer")
    s_enrich.add_argument("--model", default=None, help="Modelo de Ollama preferido (ej. qwen2.5-coder:1.5b)")
    s_enrich.add_argument("--dry-run", action="store_true", help="Solo muestra la vista previa sin modificar archivos")

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
    s_build.add_argument("--import-sessions", action="store_true", dest="import_sessions",
                         help="Importar sesiones recientes de Hermes antes del build (memoria viva)")
    s_build.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    s_scan = sub.add_parser("scan", help="Escanea proyecto y genera eventos")
    s_scan.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_scan.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_scan.add_argument("--quiet", action="store_true", help="Modo silencioso sin mensajes de salida")

    s_hook = sub.add_parser("hook", help="Gestión e instalación de Git pre-commit hooks")
    s_hook.add_argument("action", nargs="?", choices=["install", "uninstall"], default="install", help="Acción: install o uninstall")
    s_hook.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_hook.add_argument("--force", action="store_true", help="Sobrescribir hooks existentes")

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
    
    s_doctor = sub.add_parser("doctor", help="Diagnóstico y auto-reparación (Self-Healing) del proyecto")
    s_doctor.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a diagnosticar")
    s_doctor.add_argument("--fix", action="store_true", help="Auto-reparar anomalías e inconsistencias encontradas")
    s_doctor.add_argument("--json", action="store_true", help="Salida JSON estructurada")

    s_watch = sub.add_parser("watch", help="Daemon escuchador en segundo plano para sincronización continua")
    s_watch.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a monitorear")
    s_watch.add_argument("--debounce-ms", type=int, default=500, help="Tiempo en ms a esperar tras modificaciones (default: 500)")

    s_export = sub.add_parser(
        "export",
        help="Exporta el contexto en formato portable (XML/JSON/Markdown) para chats web de LLMs",
    )
    s_export.add_argument("target", nargs="?", default=".", help="Ruta del proyecto")
    s_export.add_argument(
        "--format",
        choices=["xml", "json", "markdown"],
        default="xml",
        help="Formato de salida ('xml', 'json', 'markdown')",
    )
    s_export.add_argument("--output", default=None, help="Ruta del archivo de salida (por defecto: contextmap_export.xml)")
    s_export.add_argument("--brief-only", action="store_true", help="Exportar únicamente el brief ejecutivo")
    s_export.add_argument(
        "--model",
        default="gpt-4o",
        help="Modelo de destino para estimación de tokens (gpt-4o, claude-3-5-sonnet, gemini-1.5-pro)",
    )

    s_adapt = sub.add_parser("adapt", help="Detecta stack/IDE y genera reglas agénticas adaptadas")
    s_adapt.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a analizar")
    s_adapt.add_argument("--project", default="Repo", help="Nombre del proyecto")
    s_adapt.add_argument("--overwrite", action="store_true", help="Sobrescribir reglas existentes")
    s_adapt.add_argument("--merge", action="store_true", help="Fusionar: anexa/actualiza bloque ContextMap preservando reglas del usuario")

    s_personal = sub.add_parser(
        "personal",
        help="Base de datos personal consolidada (SQLite + FTS5, transportable en F:/pendrive)",
    )
    sp = s_personal.add_subparsers(dest="personal_cmd", help="Acciones personales")

    sp_sync = sp.add_parser("sync", help="Consolida proyectos en la BD personal")
    sp_sync.add_argument("target", nargs="?", default=".", help="Ruta del proyecto a consolidar")
    sp_sync.add_argument("--todos", action="store_true", help="Consolidar todos los proyectos con .context-map en ~/Proyectos, ~/Documents y ~/Desktop")
    sp_sync.add_argument("--db", default=None, help="Ruta a la BD personal (default: F: o ~/.context-map/personal)")
    sp_sync.add_argument("--rutas", default="", help="Rutas adicionales separadas por ';' para --todos (ej. 'H:\\Mi unidad\\Desarrollo y Proyectos;D:\\proyectos')")

    sp_add = sp.add_parser("add", help="Registra una lección o decisión al vuelo")
    sp_add.add_argument("texto", help="Texto de la lección o decisión")
    sp_add.add_argument("--tipo", choices=["leccion", "decision"], default="leccion", help="Tipo de registro")
    sp_add.add_argument("--proyecto", default=None, help="Proyecto asociado")
    sp_add.add_argument("--contexto", default="", help="Contexto / cómo se resolvió")
    sp_add.add_argument("--tags", default="", help="Etiquetas separadas por coma")
    sp_add.add_argument("--db", default=None, help="Ruta a la BD personal")

    sp_query = sp.add_parser("query", help="Busca con full-text (FTS5) en la BD personal")
    sp_query.add_argument("consulta", help="Términos de búsqueda (sintaxis FTS5)")
    sp_query.add_argument("--proyecto", default=None, help="Filtrar por proyecto")
    sp_query.add_argument("--limite", type=int, default=10, help="Máximo de resultados (default: 10)")
    sp_query.add_argument("--db", default=None, help="Ruta a la BD personal")
    sp_query.add_argument("--json", action="store_true", help="Salida JSON estructurada (para uso programático/agentes)")

    sp_export = sp.add_parser("export", help="Genera un vault personal Obsidian desde la BD")
    sp_export.add_argument("--destino", default=None, help="Carpeta destino del vault personal (default: ~/.context-map/vault-Personal)")
    sp_export.add_argument("--db", default=None, help="Ruta a la BD personal")

    sp_backup = sp.add_parser("backup", help="Copia la BD personal a un pendrive/disco externo")
    sp_backup.add_argument("--destino", required=True, help="Ruta destino (ej. /run/media/usb/personal.db)")
    sp_backup.add_argument("--db", default=None, help="Ruta a la BD personal (default: la activa)")

    p_pack = sub.add_parser("pack", help="Empaqueta el contexto en un archivo comprimido .ctxpack portátil")
    p_pack.add_argument("target", nargs="?", default=".", help="Ruta del proyecto (default: .)")
    p_pack.add_argument("--output", "-o", default=None, help="Ruta del archivo de salida .ctxpack")

    p_unpack = sub.add_parser("unpack", help="Desempaqueta un archivo .ctxpack y restaura el contexto")
    p_unpack.add_argument("archive", help="Ruta del archivo .ctxpack")
    p_unpack.add_argument("target", nargs="?", default=".", help="Directorio destino para la restauración (default: .)")

    return p

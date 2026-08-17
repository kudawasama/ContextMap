"""Mapeos de estandarización y constantes de clasificación semántica.

Organiza las constantes y diccionarios utilizados por el motor de normalización
y clasificación de nodos.
"""

from __future__ import annotations

# Tags a eliminar (redundantes o no informativos)
TAGS_ELIMINAR: set[str] = {
    "todo",
    "otro",
    "docstring",
    "__init__.py",
}

CLASSIFICATION_PATTERNS: list[tuple[list[str], str, str]] = [
    (["feat", "feature", "nueva", "agregar", "añadir", "implementar", "crear", "soporte para"], "feature", "Feature"),
    (["fix", "corregir", "arreglar", "solucionar", "resolver", "patch", "bug", "error", "fallo"], "fix", "Fix"),
    (["update", "actualizar", "mejorar", "optimizar", "refactor", "refactorizar", "reestructurar", "limpiar"], "update", "Update"),
    (["chore", "mantenimiento", "config", "configurar", "dependenc", "build", "ci", "cd", "docker", "script"], "chore", "Chore"),
    (["refactor", "refactorizar", "reorganizar", "extraer", "modular", "separar", "mover archivo"], "refactor", "Refactor"),
    (["doc", "documentar", "readme", "changelog", "comentario", "docstring", "guia", "tutorial"], "docs", "Documentación"),
    (["test", "testing", "prueba", "cobertura", "mock", "spec", "e2e", "integracion"], "test", "Test"),
    (["style", "formato", "lint", "prettier", "espacios", "indent", "naming", "convencion"], "style", "Style"),
    (["perf", "performance", "rendimiento", "velocidad", "memoria", "cache", "latencia"], "perf", "Performance"),
    (["security", "seguridad", "auth", "autenticacion", "autorizacion", "vulnerabilidad", "cifrado"], "security", "Security"),
]

DEFAULT_CLASSIFICATION: tuple[str, str] = ("other", "Otro")

# Mapeo de conceptos / dominio técnico
CONCEPT_PATTERNS: list[tuple[list[str], str]] = [
    (["base de datos", "database", " db", "sql", "query", "consulta", "tabla", "schema",
      "migracion", "migración", "modelo", "modelos", "repositorio", "repository",
      "maestroclasificacion", "facturascontrol", "ordenescompra", "guias"],
     "BASEDEDATOS"),
    (["tui", "textual", "interfaz terminal", "pantalla", "panel", "widget", "lazyapp",
      "gobernanzalazy", "menú", "menu.py", "console"],
     "TUI"),
    (["cli", "comando", "argumento", "flag", "terminal", "consola", "shell", "argparse",
      "click", "typer", "entrypoint", "main.py", "cli.py"],
     "CLI"),
    (["ui", "frontend", "interfaz", "vista", "componente", "pagina", "página", "estilo",
      "css", "html", "dashboard", "tablero"],
     "UI"),
    (["api", "endpoint", "rest", "graphql", "webhook", "integracion", "integración",
      "servicio", "service", "wrapper", "conector", "connector"],
     "API"),
    (["bot", "telegram", "whatsapp", "discord", "playwright", "descarga", "pdf",
      "icstruye", "iconstruye", "automatizacion", "automatización"],
     "AUTOMATIZACION"),
    (["etl", "ingesta", "ingest", "parser", "parse", "normalizar", "limpieza", "clean",
      "transformacion", "transformación", "extractor", "detector"],
     "ETL"),
    (["reporte", "report", "monthly", "mensual", "consolidado", "excel", "xlsx", "xls",
      "openpyxl", "hoja", "sheet"],
     "REPORTES"),
    (["test", "prueba", "testing", "cobertura", "mock", "fixture", "assert", "unittest",
      "pytest", "smoke"],
     "TESTING"),
    (["config", "settings", "environment", "env", "variable", ".env", "yaml", "toml",
      "pyproject", "requirements"],
     "CONFIGURACION"),
    (["docker", "kubernetes", "deploy", "ci", "cd", "github actions", "workflow",
      "pipeline", "infraestructura", "servidor"],
     "DEVOPS"),
    (["documentacion", "documentación", "readme", "changelog", "docstring", "guia",
      "tutorial", "wiki", "docs"],
     "DOCUMENTACION"),
    (["seguridad", "security", "auth", "autenticacion", "autorizacion", "permiso",
      "token", "jwt", "oauth"],
     "SEGURIDAD"),
    (["performance", "rendimiento", "velocidad", "latencia", "memoria", "cpu", "cache",
      "optimizacion", "optimización"],
     "PERFORMANCE"),
]

DEFAULT_CONCEPT: str = "GENERAL"

TAG_FILE_MAP: dict[str, str] = {
    "antigravity.py": "integracion",
    "chat_export.py": "integracion",
    "checker.py": "analisis",
    "cli.py": "cli",
    "content.py": "analisis",
    "git.py": "integracion",
    "hermes.py": "integracion",
    "models.py": "modelos",
    "structure.py": "analisis",
    "brief.py": "presentacion",
    "generadores.py": "generadores",
    "parser.py": "parser",
    "reporter.py": "reportes",
    "scanner.py": "scanner",
    "smoke.py": "testing",
    "store.py": "persistencia",
    "sync.py": "sincronizacion",
    "writer.py": "presentacion",
}

TAG_MERGE: dict[str, str] = {
    "doc": "documentacion",
    "docs": "documentacion",
    "commit": "git",
    "repo": "git",
    "riesgo": "riesgo",
    "complejidad": "riesgo",
    "clases": "modelos",
    "estructura": "arquitectura",
    "config": "configuracion",
    "entrypoint": "cli",
    "tests": "testing",
    "metricas": "analisis",
    "python": "lenguaje",
}

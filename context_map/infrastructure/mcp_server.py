"""Servidor MCP de ContextMap.

Expone las herramientas de ctxmap como tools MCP (transporte stdio) para que
cualquier agente compatible con MCP (Hermes Agent, Claude Desktop, Cursor,
Windsurf...) las llame directamente como herramientas, sin shell:

- ``refresh``   — el flujo completo (scan + build preservando manuales + check)
- ``scan``      — escanear cambios del código
- ``build``     — regenerar vault + brief
- ``check``     — readiness + salud del vault
- ``import_git`` / ``import_chat`` / ``import_sessions`` — historia
- ``adapt``     — reglas por agente (AGENTS.md, CLAUDE.md, .cursorrules...)
- ``context``   — leer el CONTEXT.md (brief) del proyecto

Uso (desde la raíz de un proyecto): ``ctxmap mcp`` — el servidor queda a la
escucha en stdio; conéctalo como servidor MCP en tu agente (ej. en Hermes:

.. code-block:: yaml

    mcp_servers:
      ctxmap:
        command: "ctxmap"
        args: ["mcp"]
)
"""

from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from types import SimpleNamespace as NS

try:
    from mcp.server.fastmcp import FastMCP

    _fastmcp = FastMCP("context-map")
except ImportError:  # mcp no instalado: el módulo se importa pero sin servidor
    _fastmcp = None


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


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@_tool
def refresh(target: str = ".", project: str = "") -> str:
    """Actualiza el contexto del proyecto: scan + build (preservando manuales) + check. USAR como flujo normal al terminar de trabajar.

    Args:
        target: Directorio del proyecto (default ".").
        project: Nombre del proyecto (opcional).
    """
    from context_map.application.commands.refresh import cmd_refresh

    return _ejecutar(cmd_refresh, NS(target=target, project=project or None, quiet=True))


@_tool
def scan(target: str = ".", project: str = "") -> str:
    """Escanea el código del proyecto y registra eventos (nodos IDEA/CAMBIO/CORRECCION)."""
    from context_map.application.commands.scan import cmd_scan

    return _ejecutar(cmd_scan, NS(target=target, project=project or None))


@_tool
def build(target: str = ".", project: str = "", clean: bool = False, brief: bool = True) -> str:
    """Regenera el vault de Obsidian y el brief. NO usar clean=True si hay notas manuales (las borra).

    Args:
        target: Directorio del proyecto (default ".").
        project: Nombre del proyecto.
        clean: Reconstrucción total (DESTRUCTIVO para notas manuales).
        brief: Regenerar también CONTEXT.md.
    """
    from context_map.application.commands.build import cmd_build

    return _ejecutar(cmd_build, NS(target=target, project=project or None, clean=clean, brief=brief))


@_tool
def check(target: str = ".", project: str = "") -> str:
    """Audita el proyecto: readiness + salud del vault (notas manuales, alerta si el último build fue --clean)."""
    from context_map.application.commands.tools import cmd_check

    return _ejecutar(cmd_check, NS(target=target, project=project or None))


@_tool
def import_git(target: str = ".", project: str = "", limit: int = 50) -> str:
    """Importa el historial de commits del proyecto como eventos (la historia también es contexto)."""
    from context_map.application.commands.importers import cmd_import_git

    return _ejecutar(cmd_import_git, NS(target=target, project=project or None, limit=limit))


@_tool
def import_chat(file: str, project: str = "") -> str:
    """Importa un chat exportado (Telegram/Discord/Slack) como eventos.

    Args:
        file: Ruta al archivo de chat.
        project: Nombre del proyecto.
    """
    from context_map.application.commands.importers import cmd_import_chat

    return _ejecutar(cmd_import_chat, NS(file=file, project=project or None))


@_tool
def import_sessions(project: str = "", limit: int = 5) -> str:
    """Importa sesiones de Hermes Agent como eventos (decisiones y porqués de conversaciones)."""
    from context_map.application.commands.importers import cmd_import_sessions

    return _ejecutar(cmd_import_sessions, NS(project=project or None, db=None, limit=limit))


@_tool
def adapt(target: str = ".", project: str = "") -> str:
    """Genera/actualiza las reglas por agente del proyecto (AGENTS.md, CLAUDE.md, .cursorrules, .windsurfrules, ecosistema .hermes/)."""
    from context_map.application.commands.adapt import cmd_adapt

    return _ejecutar(cmd_adapt, NS(target=target, project=project or None))


@_tool
def context(target: str = ".", project: str = "") -> str:
    """Lee el CONTEXT.md (brief) del proyecto: qué es, por qué existe, estado y cómo trabajar. LEER ANTES de trabajar en el proyecto."""
    return _leer_brief(target, project)


@_tool
def personal_query(consulta: str, proyecto: str = "", limite: int = 5) -> str:
    """Busca en la BD PERSONAL de ContextMap (FTS5): eventos, lecciones y decisiones de TODOS los proyectos del usuario. USAR para recuperar contexto histórico global con pocos tokens (ej. '¿qué hicimos con fair share?', 'lecciones sobre Vercel'). Complementa el vault local.

    Args:
        consulta: Términos a buscar (full-text).
        proyecto: Filtrar por proyecto (opcional).
        limite: Máximo de resultados (default 5).
    """
    from context_map.core.personal import PersonalDB

    try:
        db = PersonalDB()
        try:
            resultados = db.buscar(
                consulta,
                proyecto=proyecto or None,
                limite=limite,
            )
            if not resultados:
                return f"personal: sin resultados para '{consulta}'"
            lineas = [f"personal: {len(resultados)} resultado(s) para '{consulta}':"]
            for i, r in enumerate(resultados, 1):
                proy = f" [{r.proyecto}]" if r.proyecto else " [personal]"
                lineas.append(f"{i:2d}. ({r.tabla}){proy}")
                lineas.append(f"    {r.texto}")
            return "\n".join(lineas)
        finally:
            db.cerrar()
    except Exception as err:  # noqa: BLE001
        return f"ERROR: {err} — ejecuta `ctxmap personal sync --todos` para crear la BD personal"


@_tool
def export(
    target: str = ".",
    format: str = "xml",
    output: str = "",
    brief_only: bool = False,
    model: str = "gpt-4o",
) -> str:
    """Exporta todo el contexto del proyecto en formato XML, JSON o Markdown portable (estilo Repomix) para chats web.

    Args:
        target: Ruta del proyecto.
        format: Formato de salida ('xml', 'json', 'markdown').
        output: Ruta opcional del archivo de salida.
        brief_only: Exportar únicamente el brief ejecutivo.
        model: Modelo de destino para estimación de tokens (gpt-4o, claude-3-5-sonnet, gemini-1.5-pro).
    """
    from pathlib import Path
    from context_map.application.commands.export import exportar_contexto

    try:
        p = Path(target).resolve()
        out = Path(output).resolve() if output else None
        res_path = exportar_contexto(
            project_path=p,
            format_type=format,
            output_file=out,
            brief_only=brief_only,
            model_name=model,
        )
        return f"export: [OK] Contexto exportado exitosamente a {res_path}"
    except Exception as err:
        return f"ERROR en export: {err}"


@_tool
def doctor(target: str = ".", fix: bool = False) -> str:
    """Diagnostica y auto-repara (Self-Healing) la salud del proyecto y la topología de la bóveda.

    Args:
        target: Ruta del proyecto.
        fix: Si es True, aplica reparaciones automáticas en el vault, notas y metadatos.
    """
    from context_map.domain.health.doctor import diagnosticar_salud, reparar_salud

    try:
        report = reparar_salud(target) if fix else diagnosticar_salud(target)
        status = "OK" if report.ok else "WARN/FAIL"
        resumen = f"doctor: [{status}] {len(report.checks)} chequeos ejecutados."
        detalles = [f" - {c.name}: {c.status} ({c.message})" for c in report.checks]
        return "\n".join([resumen] + detalles)
    except Exception as err:
        return f"ERROR en doctor: {err}"


@_tool
def install_hooks(target: str = ".", force: bool = False) -> str:
    """Instala Git Hooks transparentes (pre-commit y post-commit) para auto-sincronización.

    Args:
        target: Ruta del proyecto Git.
        force: Sobrescribir hooks existentes.
    """
    from context_map.domain.ecosystem.hooks import instalar_git_hooks

    try:
        res = instalar_git_hooks(target, force=force)
        if res.get("status") == "FAIL":
            return f"install_hooks: ERROR — {res.get('message')}"
        return f"install_hooks: [OK] pre-commit={res.get('pre-commit')}, post-commit={res.get('post-commit')}"
    except Exception as err:
        return f"ERROR en install_hooks: {err}"


def run() -> None:
    """Arranca el servidor MCP en stdio (bloqueante)."""
    if _fastmcp is None:
        raise SystemExit("mcp no instalado. Ejecuta: pip install mcp  (o: uv pip install mcp)")
    _fastmcp.run()


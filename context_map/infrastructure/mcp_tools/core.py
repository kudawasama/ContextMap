"""Herramientas MCP del ciclo de vida del proyecto (escanear, construir, revisar).

Extraído de ``mcp_server.py`` (1091 líneas) sin cambiar nombres ni firmas.
El servidor sigue exponiendo las mismas 33 tools; el orden en que las publica
ahora lo fija el nombre del módulo (importación alfabética).
"""

from __future__ import annotations

import os
from types import SimpleNamespace as NS

from context_map.infrastructure.mcp_tools.base import (
    _ejecutar,
    _ejecutar_con_target,
    _leer_brief,
    _leer_brief_min,
    _requiere_confirmacion,
    _seccion_brief,
    _target_abs,
    _tool,
)


@_tool
def refresh(target: str = ".", project: str = "") -> str:
    """Actualiza el contexto del proyecto: scan + build (preservando manuales) + check. USAR como flujo normal al terminar de trabajar.

    Args:
        target: Directorio del proyecto (default ".").
        project: Nombre del proyecto (opcional).
    """
    from context_map.application.commands.refresh import cmd_refresh

    return _ejecutar_con_target(cmd_refresh, "refresh", target, project=project or None, quiet=True)

@_tool
def scan(target: str = ".", project: str = "") -> str:
    """Escanea el código del proyecto y registra eventos (nodos IDEA/CAMBIO/CORRECCION)."""
    from context_map.application.commands.scan import cmd_scan

    return _ejecutar_con_target(cmd_scan, "scan", target, project=project or None)

@_tool
def build(target: str = ".", project: str = "", clean: bool = False, brief: bool = True, confirm: bool = False) -> str:
    """Regenera el vault de Obsidian y el brief.

    Args:
        target: Directorio del proyecto (default ".").
        project: Nombre del proyecto.
        clean: Reconstrucción total (DESTRUCTIVO para notas manuales); requiere confirm=True.
        brief: Regenerar también CONTEXT.md.
        confirm: Confirmación explícita obligatoria para clean=True.
    """
    try:
        if clean:
            _requiere_confirmacion("build --clean", confirm)
        from context_map.application.commands.build import cmd_build

        return _ejecutar(cmd_build, NS(target=_target_abs(target), project=project or None, clean=clean, brief=brief))
    except Exception as err:
        return f"ERROR en build: {err}"

@_tool
def check(target: str = ".", project: str = "") -> str:
    """Audita el proyecto: readiness + salud del vault (notas manuales, alerta si el último build fue --clean)."""
    from context_map.application.commands.tools import cmd_check

    return _ejecutar_con_target(cmd_check, "check", target, project=project or None)

@_tool
def import_git(target: str = ".", project: str = "", limit: int = 50) -> str:
    """Importa el historial de commits del proyecto como eventos (la historia también es contexto)."""
    from context_map.application.commands.importers import cmd_import_git

    return _ejecutar_con_target(cmd_import_git, "import_git", target, project=project or None, limit=limit)

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

    return _ejecutar_con_target(cmd_adapt, "adapt", target, project=project or None)

@_tool
def context(target: str = ".", project: str = "", minimo: bool = True, seccion: str = "") -> str:
    """Lee el CONTEXT.md (brief) del proyecto: qué es, por qué existe, estado y cómo trabajar. LEER ANTES de trabajar en el proyecto.

    Args:
        target: Ruta del proyecto.
        project: Nombre del proyecto (opcional).
        minimo: Por defecto devuelve la capa MÍNIMA (~600 tk): identidad, estado,
            títulos de riesgos y pendientes, Second Brain y cómo ampliar. Usa
            ``minimo=False`` SOLO si necesitas el brief completo (~1.600 tk).
        seccion: Si se indica (p. ej. "riesgos", "estado", "propósito"), devuelve
            **solo esa sección** del brief (todavía menos tokens). Vacío = brief.
    """
    try:
        raiz = _target_abs(target)
        if seccion:
            return _seccion_brief(raiz, project, seccion)
        if minimo:
            return _leer_brief_min(raiz, project)
        return _leer_brief(raiz, project)
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en context: {err}"

@_tool
def context_diff(since: str = "", target: str = ".", project: str = "") -> str:
    """Devuelve SOLO lo que cambió en la memoria del proyecto desde un digest, sin releer todo el brief.

    Flujo recomendado: llama sin `since` al empezar (obtienes el digest actual) y
    con `since=<digest>` al volver. Si nada cambió, devuelve una línea.

    Args:
        since: Digest devuelto en una llamada anterior (vacío = solo devuelve el actual).
        target: Ruta del proyecto.
        project: Nombre del proyecto (opcional).
    """
    try:
        from context_map.core.models import Node
        from context_map.core.storage import load_jsonl
        from context_map.domain.analysis.diff_contexto import (
            cargar_indice,
            comparar,
            digest_de,
            formatear_diff,
            guardar_indice,
            snapshot_de_nodos,
        )

        state_dir = os.path.join(_target_abs(target), ".context-map", "state")
        nodos = [Node.from_dict(r) for r in load_jsonl(os.path.join(state_dir, "graph.jsonl"))]
        digest = digest_de(nodos)
        snap = snapshot_de_nodos(nodos)

        idx_path = os.path.join(state_dir, "digest_index.json")
        indice = cargar_indice(idx_path)
        indice[digest] = snap
        guardar_indice(idx_path, indice)

        if not since:
            return (
                f"digest: {digest}\n"
                "Guarda este digest y pasalo como `since` la proxima vez para recibir SOLO los cambios."
            )
        if since == digest:
            return f"Sin cambios desde {since} (digest {digest})."
        antes = indice.get(since)
        if not antes:
            return f"Digest {since} desconocido (indice vacio o antiguo). Digest actual: {digest}."
        return formatear_diff(since, digest, comparar(antes, snap))
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en context_diff: {err}"

@_tool
def context_search(consulta: str, limite: int = 5, target: str = ".", semantico: bool = True) -> str:
    """Busca pasajes relevantes de la memoria del proyecto (nodos del grafo y notas del vault) CON CITAS.

    USAR cuando necesites contexto del proyecto sin cargar ficheros completos: devuelve
    solo los fragmentos más afines con su cita para profundizar. Fusiona BM25 con
    similitud semantica opcional (si sentence-transformers esta instalado).

    Args:
        consulta: Terminos a buscar (ej. "topologia del vault", "riesgos de ingesta").
        limite: Maximo de pasajes (default 5).
        target: Ruta del proyecto.
        semantico: Usar embeddings si estan disponibles (default True); False = solo BM25.
    """
    from context_map.domain.retrieval import buscar_contexto, formatear_resultados

    try:
        resultados = buscar_contexto(
            _target_abs(target), consulta, limite=limite, semantico=bool(semantico)
        )
        if not resultados:
            return f"context_search: sin resultados para: {consulta}"
        return "\n".join(
            [f"context_search: {len(resultados)} pasaje(s)"] + formatear_resultados(resultados)
        )
    except Exception as err:  # noqa: BLE001
        return f"ERROR en context_search: {err}"

@_tool
def context_search_vault(
    consulta: str,
    limite: int = 10,
    target: str = ".",
    seccion: str = "",
    tipo: str = "",
) -> str:
    """Busca texto libre en el vault Obsidian del proyecto con FTS5 (rapido, sin cargar ficheros).

    USAR para recuperar notas del vault por contenido (ideas, riesgos, lecciones,
    diario) con snippet y ruta. Requiere haber ejecutado ``ctxmap build``/``refresh``
    para que exista el indice ``.context-map/state/vault_index.db``.

    Args:
        consulta: Terminos a buscar (sintaxis FTS5: AND/OR/"frase").
        limite: Maximo de notas (default 10).
        target: Ruta del proyecto.
        seccion: Filtra por seccion del vault (ej. "2.0", "4.0"). Vacio = todas.
        tipo: Filtra por tipo de nota (IDEA, RIESGO, CAMBIO, BASE, ...). Vacio = todos.
    """
    from context_map.core.storage.vault_index import abrir_indice, buscar as buscar_vault
    import os

    target_abs = _target_abs(target)
    db_path = os.path.join(target_abs, ".context-map", "state", "vault_index.db")
    if not os.path.isfile(db_path):
        return (
            "context_search_vault: sin indice FTS5. "
            "Ejecuta `ctxmap refresh .` (o `ctxmap build`) para generarlo."
        )
    try:
        conn = abrir_indice(db_path)
        try:
            resultados = buscar_vault(
                conn,
                consulta,
                seccion=seccion or None,
                tipo=tipo or None,
                limite=limite,
            )
        finally:
            conn.close()
        if not resultados:
            return f"context_search_vault: sin resultados para: {consulta}"
        lineas = [f"context_search_vault: {len(resultados)} nota(s)"]
        for r in resultados:
            lineas.append(
                f"- {r['ruta']}  ({r['seccion']} · {r['tipo'] or 'sin tipo'})"
            )
            lineas.append(f"  {r['snippet']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en context_search_vault: {err}"


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
def doctor(target: str = ".", fix: bool = False, confirm: bool = False) -> str:
    """Diagnostica y auto-repara (Self-Healing) la salud del proyecto y la topología de la bóveda.

    Args:
        target: Ruta del proyecto.
        fix: Si es True, aplica reparaciones automáticas (DESTRUCTIVO); requiere confirm=True.
        confirm: Confirmación explícita obligatoria para fix=True.
    """
    from context_map.domain.health.doctor import diagnosticar_salud, reparar_salud

    try:
        if fix:
            _requiere_confirmacion("doctor --fix", confirm)
        target_abs = _target_abs(target)
        report = reparar_salud(target_abs) if fix else diagnosticar_salud(target_abs)
        status = "OK" if report.ok else "WARN/FAIL"
        resumen = f"doctor: [{status}] {len(report.checks)} chequeos ejecutados."
        detalles = [f" - {c.name}: {c.status} ({c.message})" for c in report.checks]
        return "\n".join([resumen] + detalles)
    except Exception as err:
        return f"ERROR en doctor: {err}"

@_tool
def install_hooks(target: str = ".", force: bool = False, confirm: bool = False) -> str:
    """Instala Git Hooks transparentes (pre-commit y post-commit) para auto-sincronización.

    Args:
        target: Ruta del proyecto Git.
        force: Sobrescribir hooks existentes.
        confirm: Confirmación explícita obligatoria (inyecta scripts en .git/hooks).
    """
    from context_map.domain.ecosystem.hooks import instalar_git_hooks

    try:
        _requiere_confirmacion("install_hooks", confirm)
        res = instalar_git_hooks(_target_abs(target), force=force)
        if res.get("status") == "FAIL":
            return f"install_hooks: ERROR — {res.get('message')}"
        return f"install_hooks: [OK] pre-commit={res.get('pre-commit')}, post-commit={res.get('post-commit')}"
    except Exception as err:
        return f"ERROR en install_hooks: {err}"

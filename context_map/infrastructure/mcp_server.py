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

_fastmcp: FastMCP | None = None
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


def _ejecutar_con_target(cmd_func, tool: str, target: str, **kwargs) -> str:
    """Resuelve el target y ejecuta un comando de ctxmap con manejo de errores.

    Args:
        cmd_func: Función comando a invocar.
        tool: Nombre de la tool (para los mensajes de error).
        target: Ruta del proyecto (posiblemente relativa).
        **kwargs: Argumentos adicionales del comando.

    Returns:
        str: Salida del comando o mensaje de error amigable.
    """
    try:
        return _ejecutar(cmd_func, NS(target=_target_abs(target), **kwargs))
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en {tool}: {err}"


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


def _target_abs(target: str) -> str:
    """Resuelve y valida el directorio de proyecto apuntado por la tool.

    Args:
        target: Ruta (posiblemente relativa o con ``~``).

    Returns:
        str: Ruta absoluta normalizada del proyecto.

    Raises:
        ValueError: Si la ruta no existe o no es un directorio.
    """
    resolved = os.path.abspath(os.path.expanduser(target or "."))
    if not os.path.isdir(resolved):
        raise ValueError(f"El target no es un directorio válido: {target!r}")
    return resolved


def _requiere_confirmacion(accion: str, confirm: bool) -> None:
    """Exige confirmación explícita para operaciones destructivas del MCP.

    Args:
        accion: Descripción de la operación destructiva.
        confirm: Flag de confirmación que debe pasar el agente.

    Raises:
        ValueError: Si la operación no está confirmada.
    """
    if not confirm:
        raise ValueError(
            f"Operación destructiva '{accion}' rechazada por seguridad: "
            "pasa confirm=True si estás seguro de ejecutarla."
        )


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
def context(target: str = ".", project: str = "") -> str:
    """Lee el CONTEXT.md (brief) del proyecto: qué es, por qué existe, estado y cómo trabajar. LEER ANTES de trabajar en el proyecto."""
    try:
        return _leer_brief(_target_abs(target), project)
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en context: {err}"


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
def personal_panorama(
    dias: int = 14,
    proyecto: str = "",
    solo_sesiones: bool = False,
    json_output: bool = False,
) -> str:
    """Muestra el panorama consolidado de actividad multi-proyecto (semáforos, sesiones reales y foco).

    Args:
        dias: Días hacia atrás para análisis (default: 14).
        proyecto: Filtrar por nombre de proyecto (opcional).
        solo_sesiones: Solo listar sesiones interactivas de trabajo.
        json_output: Devolver reporte como JSON estructurado.
    """
    import json

    from context_map.core.personal import PersonalDB
    from context_map.core.personal.panorama import (
        construir_panorama,
        formatear_panorama_texto,
    )

    try:
        db = PersonalDB()
        try:
            rep = construir_panorama(
                db=db,
                dias=dias,
                proyecto=proyecto or None,
                solo_sesiones=solo_sesiones,
            )
            if json_output:
                return json.dumps(rep.to_dict(), indent=2, ensure_ascii=False)
            return formatear_panorama_texto(rep)
        finally:
            db.cerrar()
    except Exception as err:  # noqa: BLE001
        return f"ERROR en personal_panorama: {err}"


@_tool
def personal_timeline(
    dias: int = 30,
    proyecto: str = "",
    json_output: bool = False,
) -> str:
    """Muestra la línea temporal unificada de sesiones y eventos con fecha en todos los proyectos.

    Args:
        dias: Días hacia atrás a incluir (default: 30).
        proyecto: Filtrar por nombre de proyecto (opcional).
        json_output: Devolver salida como lista JSON.
    """
    import json
    from dataclasses import asdict

    from context_map.core.personal import PersonalDB
    from context_map.core.personal.panorama import (
        construir_timeline,
        formatear_timeline_texto,
    )

    try:
        db = PersonalDB()
        try:
            items = construir_timeline(
                db=db,
                dias=dias,
                proyecto=proyecto or None,
            )
            if json_output:
                return json.dumps([asdict(it) for it in items], indent=2, ensure_ascii=False)
            return formatear_timeline_texto(items)
        finally:
            db.cerrar()
    except Exception as err:  # noqa: BLE001
        return f"ERROR en personal_timeline: {err}"


@_tool
def personal_repair(
    dry_run: bool = False,
    confirm: bool = False,
    json_output: bool = False,
) -> str:
    """Ejecuta el saneamiento integral de la BD personal (fusiona duplicados, purga ruido, elimina vacíos y compacta).

    Args:
        dry_run: Si es True, ejecuta en modo simulación sin modificar datos.
        confirm: Confirmación requerida si se aplican cambios reales (dry_run=False).
        json_output: Devolver salida estructurada en JSON.
    """
    import json

    from context_map.core.personal import PersonalDB
    from context_map.core.personal.repair import (
        formatear_repair_texto,
        reparar_bd_personal,
    )

    if not dry_run and not confirm:
        return "ERROR: Para aplicar reparaciones reales pasa confirm=True o utiliza dry_run=True para simular."

    try:
        db = PersonalDB()
        try:
            report = reparar_bd_personal(
                db=db,
                dry_run=dry_run,
                merge_duplicados=True,
                fill_ruta=True,
                drop_vacios=True,
                purge_ruido=True,
                vacuum=True,
            )
            if json_output:
                return json.dumps(report.to_dict(), indent=2, ensure_ascii=False)
            return formatear_repair_texto(report)
        finally:
            db.cerrar()
    except Exception as err:  # noqa: BLE001
        return f"ERROR en personal_repair: {err}"


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


def _vault_de(target: str, project: str = "") -> str:
    """Resuelve la ruta ABSOLUTA del vault del proyecto objetivo."""
    from context_map.application.commands._helpers import project_name, vault_dir

    t = _target_abs(target)
    ns = NS(target=t, project=project or "Repo")
    return os.path.join(t, vault_dir(project_name(ns)))


@_tool
def knowledge_inbox_add(texto: str, titulo: str = "", tags: str = "", fuente: str = "", target: str = ".") -> str:
    """Captura una nota en el inbox del mundo CONOCIMIENTO (PKM / Second Brain).

    USAR cuando el usuario pide guardar una idea, dato, link o apunte sin decir
    dónde va: entra crudo al inbox y luego se clasifica a PARA.

    Args:
        texto: Contenido de la nota.
        titulo: Título opcional (si falta, se deriva del texto).
        tags: Etiquetas separadas por coma.
        fuente: Origen (URL, archivo, conversación).
        target: Ruta del proyecto (default '.').
    """
    from context_map.domain.knowledge import inbox as kb

    try:
        ruta = kb.crear_nota(
            _vault_de(target), texto, titulo=titulo or None, tags=tags, fuente=fuente,
        )
        return f"knowledge_inbox_add: [OK] nota creada en {ruta}"
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_inbox_add: {err}"


@_tool
def knowledge_inbox_list(target: str = ".") -> str:
    """Lista las notas pendientes en el inbox del mundo CONOCIMIENTO (PKM).

    Args:
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import inbox as kb

    try:
        notas = kb.listar_notas(_vault_de(target), "inbox")
        if not notas:
            return "knowledge_inbox_list: inbox vacío."
        lineas = [f"knowledge_inbox_list: {len(notas)} nota(s):"]
        for n in notas:
            lineas.append(f" - {n['titulo']} ({os.path.basename(n['ruta'])})")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_inbox_list: {err}"


@_tool
def knowledge_inbox_move(nota: str, destino: str, target: str = ".") -> str:
    """Mueve una nota del inbox a una categoría PARA tras clasificarla.

    Args:
        nota: Nombre o ruta de la nota a mover.
        destino: Categoría destino (projects, areas, resources o archive).
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import inbox as kb

    try:
        ruta = kb.mover_nota(_vault_de(target), nota, destino)
        return f"knowledge_inbox_move: [OK] {nota} → {destino}: {ruta}"
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_inbox_move: {err}"


@_tool
def knowledge_purge(target: str = ".", dry_run: bool = False) -> str:
    """Clasifica y vacía el inbox del mundo CONOCIMIENTO (PKM) usando el método PARA.

    Args:
        target: Ruta del proyecto.
        dry_run: Si es True, solo simula las decisiones (no mueve archivos).
    """
    from context_map.domain.knowledge import inbox as kb

    try:
        decisiones = kb.purgar(_vault_de(target), dry_run=dry_run)
        if not decisiones:
            return "knowledge_purge: inbox vacío."
        etiqueta = " (dry-run, sin cambios)" if dry_run else ""
        lineas = [f"knowledge_purge: {len(decisiones)} nota(s){etiqueta}:"]
        for d in decisiones:
            lineas.append(f" - {d['nota']} → {d['destino']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_purge: {err}"


@_tool
def knowledge_wiki_ingest(contenido: str, titulo: str = "", fuente: str = "", entidades: str = "", target: str = ".") -> str:
    """Ingesta una fuente a la LLM Wiki (resúmenes + entidades + entry log).

    Crea la página de resumen, actualiza el índice de resúmenes, el entry log y
    las páginas de entidades/conceptos indicadas. USAR cuando hay que guardar un
    aprendizaje, artículo o lección en la base de conocimiento.

    Args:
        contenido: Texto del resumen (redactado por el agente).
        titulo: Título de la página (default: primera línea).
        fuente: Origen (URL, video, PDF, conversación).
        entidades: Conceptos separados por coma.
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        res = kb_w.ingresar(_vault_de(target), titulo, contenido, fuente=fuente, entidades=entidades)
        lineas = [f"knowledge_wiki_ingest: [OK] resumen creado en {res['ruta']}"]
        if res["entidades"]:
            lineas.append(f"entidades: {res['entidades']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_ingest: {err}"


@_tool
def knowledge_wiki_query(pregunta: str, limite: int = 5, target: str = ".") -> str:
    """Busca páginas relevantes de la LLM Wiki CON CITAS para responder preguntas.

    Devuelve las páginas más relacionadas con su wikilink (cita) y un fragmento;
    el agente sintetiza la respuesta citando cada página.

    Args:
        pregunta: Texto de la consulta.
        limite: Máximo de resultados (default 5).
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        resultados = kb_w.consultar(_vault_de(target), pregunta, limite=limite)
        if not resultados:
            return f"knowledge_wiki_query: sin páginas relevantes para: {pregunta}"
        lineas = [f"knowledge_wiki_query: {len(resultados)} resultado(s):"]
        for r in resultados:
            lineas.append(f" - {r['titulo']} — cita {r['cita']}")
            lineas.append(f"     {r['excerpt']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_query: {err}"


@_tool
def knowledge_wiki_ask(pregunta: str, limite: int = 5, target: str = ".") -> str:
    """Responde una pregunta del mundo CONOCIMIENTO de forma extractiva y LOCAL, con citas.

    No usa red ni LLM: encadena las frases mas afines de la wiki y cita cada
    fuente como [n]. USAR cuando el usuario pregunta sobre su Second Brain.

    Args:
        pregunta: Pregunta a responder.
        limite: Maximo de fuentes (default 5).
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        res = kb_w.sintetizar(_vault_de(target), pregunta, limite=limite)
        if not res["respuesta"]:
            return f"knowledge_wiki_ask: sin paginas relevantes para: {pregunta}"
        lineas = ["knowledge_wiki_ask:", str(res["respuesta"]), "", "Fuentes:"]
        for i, f in enumerate(res["fuentes"], 1):
            lineas.append(f" [{i}] {f['titulo']} — {f['cita']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_ask: {err}"


@_tool
def knowledge_wiki_embeddings(target: str = ".", rebuild: bool = False) -> str:
    """Estado del indice semantico opcional de la wiki (sentence-transformers).

    La wiki no depende de esta capa: sin la libreria el ranking usa BM25. Con
    rebuild=True carga el modelo (puede usar red la primera vez) y reconstruye
    el indice cacheado en .context-map/state/embeddings.json. USAR para saber
    si la busqueda semantica esta activa o para precalcular el indice.

    Args:
        target: Ruta del proyecto.
        rebuild: Reconstruir el indice ignorando la cache.
    """
    from context_map.domain.knowledge import embeddings as emb

    try:
        vdir = _vault_de(target)
        indice = emb.construir_indice(vdir, forzar=True) if rebuild else {}
        diag = emb.estado(vdir)
        if indice.get("motivo"):
            diag["motivo"] = indice["motivo"]
        lineas = ["knowledge_wiki_embeddings:"]
        lineas.append(f" - disponible: {'si' if diag['disponible'] else 'no'}")
        lineas.append(f" - modelo: {diag['modelo'] or '(ninguno)'}")
        lineas.append(f" - paginas_wiki: {diag['paginas_wiki']}")
        lineas.append(f" - paginas_indexadas: {diag['paginas_indexadas']}")
        lineas.append(f" - cache_al_dia: {'si' if diag['cache_al_dia'] else 'no'}")
        if diag.get("motivo"):
            lineas.append(f" - motivo: {diag['motivo']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_embeddings: {err}"


@_tool
def knowledge_wiki_moc(target: str = ".") -> str:
    """Regenera el MOC (mapa de contenido) de la wiki: cada concepto con sus fuentes.

    Args:
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        ruta = kb_w.generar_moc(_vault_de(target))
        return f"knowledge_wiki_moc: [OK] MOC regenerado en {ruta}"
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_moc: {err}"


@_tool
def knowledge_wiki_lint(target: str = ".") -> str:
    """Audita la salud de la LLM Wiki: enlaces rotos, huérfanas, conceptos sin página.

    Args:
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        reporte = kb_w.lint(_vault_de(target))
        estado = "OK" if reporte.ok else "PROBLEMAS"
        lineas = [f"knowledge_wiki_lint: [{estado}]"]
        for e in reporte.errores:
            lineas.append(f" ⚠️ {e}")
        for a in reporte.avisos:
            lineas.append(f" 💬 {a}")
        if not reporte.errores and not reporte.avisos:
            lineas.append(" sin errores ni avisos.")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_wiki_lint: {err}"


@_tool
def knowledge_review_due(limite: int = 20, target: str = ".") -> str:
    """Páginas de la wiki pendientes de repaso hoy (repaso espaciado SM-2).

    Args:
        limite: Máximo de páginas (default 20).
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import review as rv

    try:
        pendientes = rv.paginas_due(_vault_de(target), limite=limite)
        if not pendientes:
            return "knowledge_review_due: nada pendiente. 🎉"
        lineas = [f"knowledge_review_due: {len(pendientes)} página(s):"]
        for p in pendientes:
            lineas.append(f" - {p['titulo']} ({p['due'] or 'nueva'}) · {p['cita']}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_review_due: {err}"


@_tool
def knowledge_review_grade(pagina: str, calidad: int, target: str = ".") -> str:
    """Califica (0-5) una página de la wiki y reprograma su repaso con SM-2.

    Args:
        pagina: Título de la página o wikilink.
        calidad: Calificación 0-5 (>=3 es acierto).
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import review as rv

    try:
        res = rv.calificar(_vault_de(target), pagina, calidad)
        return (
            f"knowledge_review_grade: {res['titulo']} → "
            f"repeticiones={res['repetitions']}, intervalo={res['interval']}d, "
            f"ease={res['ease']}, próximo={res['due']}"
        )
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_review_grade: {err}"


@_tool
def knowledge_ingest(url: str, video: bool = False, destino: str = "inbox", titulo: str = "", target: str = ".") -> str:
    """Captura una fuente externa al mundo CONOCIMIENTO (Web Clipper + YouTube).

    USAR cuando el usuario comparte un link y hay que guardarlo: con video=False
    descarga la web y la convierte a Markdown; con video=True baja la transcripcion
    de YouTube (yt-dlp). Entra al inbox por defecto o a la wiki con destino='wiki'.

    Args:
        url: Direccion web o de video de YouTube.
        video: True si es un video de YouTube (transcripcion).
        destino: 'inbox' (defecto) o 'wiki'.
        titulo: Titulo opcional.
        target: Ruta del proyecto.
    """
    from context_map.domain.knowledge import captura as cap

    try:
        vdir = _vault_de(target)
        if video:
            titulo_final, texto = cap.descargar_transcripcion_youtube(url, titulo or None)
            res = cap.capturar(vdir, texto, titulo_final, url, destino)
        else:
            res = cap.capturar_desde_url(vdir, url, titulo, destino)
        return f"knowledge_ingest: [OK] captura en {res['destino']}: {res['ruta']}"
    except Exception as err:  # noqa: BLE001
        return f"ERROR en knowledge_ingest: {err}"


def run() -> None:
    """Arranca el servidor MCP en stdio (bloqueante)."""
    if _fastmcp is None:
        raise SystemExit("mcp no instalado. Ejecuta: pip install mcp  (o: uv pip install mcp)")
    _fastmcp.run()


"""Herramientas MCP del Second Brain (inbox, wiki, repaso y captura).

Extraído de ``mcp_server.py`` (1091 líneas) sin cambiar nombres ni firmas.
El servidor sigue exponiendo las mismas 33 tools; el orden en que las publica
ahora lo fija el nombre del módulo (importación alfabética).
"""

from __future__ import annotations

import os
from types import SimpleNamespace as NS

from context_map.infrastructure.mcp_tools.base import (
    _target_abs,
    _tool,
)


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
def knowledge_wiki_ask(pregunta: str, limite: int = 5, target: str = ".", llm: bool = False) -> str:
    """Responde una pregunta del mundo CONOCIMIENTO de forma extractiva y LOCAL, con citas.

    Por defecto NO usa red ni LLM: encadena las frases mas afines de la wiki y
    cita cada fuente como [n]. USAR cuando el usuario pregunta sobre su Second
    Brain. Con llm=True intenta sintetizar con el LLM configurado por el usuario
    (CTXMAP_LLM_API_KEY); si falla, devuelve la version extractiva local.

    Args:
        pregunta: Pregunta a responder.
        limite: Maximo de fuentes (default 5).
        target: Ruta del proyecto.
        llm: Permitir el LLM opcional (envio de fragmentos al endpoint configurado).
    """
    from context_map.domain.knowledge import wiki as kb_w

    try:
        res = kb_w.sintetizar(_vault_de(target), pregunta, limite=limite, usar_llm=bool(llm))
        if not res["respuesta"]:
            return f"knowledge_wiki_ask: sin paginas relevantes para: {pregunta}"
        lineas = [
            f"knowledge_wiki_ask ({res.get('motor', 'extractivo')}):",
            str(res["respuesta"]),
            "",
            "Fuentes:",
        ]
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

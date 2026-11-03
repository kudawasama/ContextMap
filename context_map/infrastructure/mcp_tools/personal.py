"""Herramientas MCP de la memoria personal multi-proyecto.

Extraído de ``mcp_server.py`` (1091 líneas) sin cambiar nombres ni
comportamiento: el servidor sigue registrando las mismas tools en el mismo orden.
"""

from __future__ import annotations

from context_map.infrastructure.mcp_tools.base import (
    _tool,
)


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
                texto = " ".join((r.texto or "").split())
                if len(texto) > 240:
                    texto = texto[:240].rstrip() + "…"
                lineas.append(f"    {texto}")
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

"""Subpaquete modular para el comando personal y base de datos consolidada.

Permite sincronizar el contexto de todos los proyectos en una única base
de datos SQLite, registrar lecciones y decisiones al vuelo, buscar con full-text
(FTS5), exportar un vault personal de Obsidian, y gestionar panoramas y reparaciones.

Subcomandos:
    sync       Consolida proyectos en la BD personal.
    add        Agrega una lección o decisión al vuelo.
    query      Busca en eventos, lecciones y decisiones (FTS5).
    export     Genera un vault personal Obsidian desde la BD.
    backup     Copia la BD a otra ruta (pendrive, disco externo).
    panorama   Genera el tablero general de actividad multi-proyecto.
    timeline   Genera la línea de tiempo agregada de sesiones y eventos.
    repair     Ejecuta saneamiento y reparación integral de la BD.
"""

from __future__ import annotations

from context_map.application.commands.personal.common import (
    _campo_knowledge,
    _leer_decisiones_vault,
    _leer_lecciones_vault,
    _nombre_proyecto_por_ruta,
    _parsear_leccion,
    _rutas_proyecto,
    sincronizar_proyecto_automatico,
)
from context_map.application.commands.personal.export import (
    _cmd_personal_export,
    _generar_slugs_unicos,
    _sanear_texto_markdown,
    _seccion_decisiones,
    _seccion_lecciones,
    _seccion_notas_proyecto,
)
from context_map.application.commands.personal.panorama import (
    _cmd_personal_panorama,
)
from context_map.application.commands.personal.query import (
    _cmd_personal_add,
    _cmd_personal_backup,
    _cmd_personal_query,
)
from context_map.application.commands.personal.repair import (
    _cmd_personal_repair,
)
from context_map.application.commands.personal.sync import (
    _bases_gdrive_estandar,
    _bases_gdrive_letras,
    _bases_por_defecto,
    _cmd_personal_sync,
    _deduplicar_por_ruta,
    _descubrir_proyectos,
    _proyectos_para_sync,
)
from context_map.application.commands.personal.timeline import (
    _cmd_personal_timeline,
)


def cmd_personal(args) -> None:
    """Despacha el subcomando personal solicitado.

    Args:
        args: Namespace de argparse con ``personal_cmd``.
    """
    sub = str(getattr(args, "personal_cmd", "") or "")
    despacho: dict[str, object] = {
        "sync": _cmd_personal_sync,
        "add": _cmd_personal_add,
        "query": _cmd_personal_query,
        "export": _cmd_personal_export,
        "backup": _cmd_personal_backup,
        "panorama": _cmd_personal_panorama,
        "timeline": _cmd_personal_timeline,
        "repair": _cmd_personal_repair,
    }
    handler = despacho.get(sub)
    if callable(handler):
        handler(args)
    else:
        print("personal: usa uno de sync | add | query | export | backup | panorama | timeline | repair")


__all__ = [
    "_bases_gdrive_estandar",
    "_bases_gdrive_letras",
    "_bases_por_defecto",
    "_campo_knowledge",
    "_cmd_personal_add",
    "_cmd_personal_backup",
    "_cmd_personal_export",
    "_cmd_personal_panorama",
    "_cmd_personal_query",
    "_cmd_personal_repair",
    "_cmd_personal_sync",
    "_cmd_personal_timeline",
    "_deduplicar_por_ruta",
    "_descubrir_proyectos",
    "_generar_slugs_unicos",
    "_leer_decisiones_vault",
    "_leer_lecciones_vault",
    "_nombre_proyecto_por_ruta",
    "_parsear_leccion",
    "_proyectos_para_sync",
    "_rutas_proyecto",
    "_sanear_texto_markdown",
    "_seccion_decisiones",
    "_seccion_lecciones",
    "_seccion_notas_proyecto",
    "cmd_personal",
    "sincronizar_proyecto_automatico",
]

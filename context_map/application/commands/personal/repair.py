"""Handler CLI del comando repair para la base de datos personal.

Orquesta el saneamiento de eventos de ruido técnico, deduplicación de proyectos,
relleno de rutas, limpieza de carpetas vacías y optimización con SQLite VACUUM.
"""

from __future__ import annotations

import json

from context_map.core.personal import PersonalDB
from context_map.core.personal.repair import (
    formatear_repair_texto,
    reparar_bd_personal,
)


def _cmd_personal_repair(args) -> None:
    """Ejecuta el saneamiento y reparación integral de la BD personal."""
    db = PersonalDB(getattr(args, "db", None))
    try:
        dry_run = bool(getattr(args, "dry_run", False))
        is_all = bool(getattr(args, "all", False))
        merge_duplicados = is_all or bool(getattr(args, "merge_duplicados", False))
        fill_ruta = is_all or bool(getattr(args, "fill_ruta", False))
        drop_vacios = is_all or bool(getattr(args, "drop_vacios", False))
        purge_ruido = is_all or bool(getattr(args, "purge_ruido", False))
        vacuum = is_all or bool(getattr(args, "vacuum", False))
        json_output = bool(getattr(args, "json", False))

        if not (merge_duplicados or fill_ruta or drop_vacios or purge_ruido or vacuum):
            merge_duplicados = fill_ruta = drop_vacios = purge_ruido = vacuum = True

        rutas_extra = [
            r.strip()
            for r in (getattr(args, "rutas", "") or "").split(";")
            if r.strip()
        ]

        report = reparar_bd_personal(
            db=db,
            dry_run=dry_run,
            merge_duplicados=merge_duplicados,
            fill_ruta=fill_ruta,
            drop_vacios=drop_vacios,
            purge_ruido=purge_ruido,
            vacuum=vacuum,
            rutas_busqueda=rutas_extra,
        )

        if json_output:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(formatear_repair_texto(report))
    finally:
        db.cerrar()

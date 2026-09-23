"""Handler CLI del comando timeline multi-proyecto.

Genera la vista cronológica de sesiones interactivas (Hermes) y eventos con fecha,
ordenados descendentemente y formateados para terminal o exportación JSON.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from context_map.core.personal import PersonalDB
from context_map.core.personal.panorama import (
    construir_timeline,
    formatear_timeline_texto,
)


def _cmd_personal_timeline(args) -> None:
    """Genera y muestra la línea temporal agregada de sesiones y eventos."""
    db = PersonalDB(getattr(args, "db", None))
    try:
        dias = int(getattr(args, "dias", 30) or 30)
        proyecto = getattr(args, "proyecto", None)
        json_output = bool(getattr(args, "json", False))

        items = construir_timeline(
            db=db,
            dias=dias,
            proyecto=proyecto,
        )

        if json_output:
            print(json.dumps([asdict(it) for it in items], indent=2, ensure_ascii=False))
        else:
            print(formatear_timeline_texto(items))
    finally:
        db.cerrar()

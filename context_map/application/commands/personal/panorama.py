"""Handler CLI del comando panorama multi-proyecto.

Invoca la lógica pura de agregación y semáforos de actividad de
context_map.core.personal.panorama y presenta la salida en consola o JSON.
"""

from __future__ import annotations

import json

from context_map.core.personal import PersonalDB
from context_map.core.personal.panorama import (
    construir_panorama,
    formatear_panorama_texto,
)


def _cmd_personal_panorama(args) -> None:
    """Genera y muestra el tablero general de actividad multi-proyecto."""
    db = PersonalDB(getattr(args, "db", None))
    try:
        dias = int(getattr(args, "dias", 14) or 14)
        proyecto = getattr(args, "proyecto", None)
        solo_sesiones = bool(getattr(args, "solo_sesiones", False))
        json_output = bool(getattr(args, "json", False))

        report = construir_panorama(
            db=db,
            dias=dias,
            proyecto=proyecto,
            solo_sesiones=solo_sesiones,
        )

        if json_output:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(formatear_panorama_texto(report))
    finally:
        db.cerrar()

"""Pruebas de la ruta real del proyecto en la BD personal (T1.8).

Regresión de la auditoría 2026-09-21: ``cargar_eventos`` llamaba a
``registrar_proyecto(nombre)`` sin pasar la ruta, así que la columna ``ruta``
quedaba vacía en el 100% de los proyectos (14 de 14). Sin ella no se puede
localizar un proyecto, detectar duplicados por carpeta ni auditar el panel.
"""

from __future__ import annotations

import argparse
import os

from context_map.application.commands.personal import (
    _cmd_personal_sync,
    sincronizar_proyecto_automatico,
)
from context_map.core.personal import PersonalDB

EVENTO = '{"type": "BASE", "text": "Proyecto escaneado", "source": "test", "timestamp": "2026-09-21T10:00:00"}'


def _proyecto_con_eventos(base, nombre: str):
    """Crea un proyecto con un event.jsonl mínimo."""
    raiz = base / nombre
    raw = raiz / ".context-map" / "raw"
    raw.mkdir(parents=True)
    (raw / "events.jsonl").write_text(EVENTO + "\n", encoding="utf-8")
    return raiz


def _args(**kwargs) -> argparse.Namespace:
    """Namespace con los valores por defecto del comando `personal sync`."""
    base = {"todos": False, "rutas": "", "target": ".", "db": None}
    base.update(kwargs)
    return argparse.Namespace(**base)


def _ruta_registrada(nombre: str) -> str:
    """Devuelve la ruta guardada para un proyecto de la BD aislada del test."""
    db = PersonalDB()
    try:
        fila = db._conn.execute(
            "SELECT ruta FROM proyectos WHERE nombre = ?", (nombre,)
        ).fetchone()
    finally:
        db.cerrar()
    assert fila is not None, f"{nombre} no quedó registrado"
    return str(fila["ruta"])


def test_sync_guarda_la_ruta(tmp_path, monkeypatch) -> None:
    """El sync con `--todos` guarda la carpeta real del proyecto."""
    raiz = tmp_path / "Mi unidad"
    proyecto = _proyecto_con_eventos(raiz, "mi-app-utm")

    import context_map.application.commands.personal as personal_mod

    monkeypatch.setattr(personal_mod, "_bases_por_defecto", lambda: [str(raiz)])

    _cmd_personal_sync(_args(todos=True))

    ruta = _ruta_registrada("mi-app-utm")
    assert ruta, "la ruta quedó vacía"
    assert os.path.isdir(ruta)
    assert os.path.samefile(ruta, proyecto)


def test_consolidacion_automatica_guarda_la_ruta(tmp_path) -> None:
    """La consolidación silenciosa de cada `sync` también guarda la ruta."""
    proyecto = _proyecto_con_eventos(tmp_path, "CotanoPet")

    sincronizar_proyecto_automatico("CotanoPet", str(proyecto))

    ruta = _ruta_registrada("CotanoPet")
    assert ruta, "la ruta quedó vacía"
    assert os.path.samefile(ruta, proyecto)


def test_ruta_se_actualiza_si_el_proyecto_se_mueve(tmp_path, monkeypatch) -> None:
    """Re-sincronizar desde otra carpeta actualiza la ruta guardada."""
    origen = _proyecto_con_eventos(tmp_path / "viejo", "CotanoPet")
    sincronizar_proyecto_automatico("CotanoPet", str(origen))
    assert os.path.samefile(_ruta_registrada("CotanoPet"), origen)

    nuevo = _proyecto_con_eventos(tmp_path / "nuevo", "CotanoPet")
    sincronizar_proyecto_automatico("CotanoPet", str(nuevo))

    assert os.path.samefile(_ruta_registrada("CotanoPet"), nuevo)

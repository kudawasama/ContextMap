"""Pruebas del descubrimiento de proyectos para la BD personal (T1.6).

Regresión medida en la auditoría 2026-09-21: las bases de ``sync --todos`` se
solapan (``H:\\Mi unidad`` contiene a ``H:\\Mi unidad\\Desarrollo y Proyectos``),
así que cada proyecto se escaneaba 2-3 veces por corrida.
"""

from __future__ import annotations

import argparse
import os

from context_map.application.commands.personal import (
    _deduplicar_por_ruta,
    _proyectos_para_sync,
)


def _proyecto(base, nombre: str):
    """Crea un proyecto mínimo con `.context-map`."""
    raiz = base / nombre
    (raiz / ".context-map" / "raw").mkdir(parents=True)
    return raiz


def _args(**kwargs) -> argparse.Namespace:
    """Namespace con los valores por defecto del comando `personal sync`."""
    base = {"todos": False, "rutas": "", "target": ".", "db": None}
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_deduplicar_por_ruta_quita_repetidos_y_conserva_orden(tmp_path) -> None:
    """El mismo proyecto no puede aparecer dos veces en una corrida de sync."""
    padre = tmp_path / "Desarrollo"
    hijo = padre / "GitHub" / "CotanoPet"
    hijo.mkdir(parents=True)

    proyectos = [
        ("CotanoPet", str(hijo)),
        ("Otro", str(padre)),
        ("CotanoPet", str(hijo) + os.sep),  # misma ruta, forma distinta
    ]

    unicos = _deduplicar_por_ruta(proyectos)

    assert [nombre for nombre, _ in unicos] == ["CotanoPet", "Otro"]


def test_bases_solapadas_no_repite_proyectos(tmp_path, monkeypatch) -> None:
    """Con bases anidadas, cada proyecto se escanea una sola vez."""
    raiz = tmp_path / "Mi unidad"
    proyecto = _proyecto(raiz / "Desarrollo y Proyectos", "mi-app-utm")

    import context_map.application.commands.personal as personal_mod

    monkeypatch.setattr(
        personal_mod,
        "_bases_por_defecto",
        lambda: [str(raiz), str(raiz / "Desarrollo y Proyectos")],
    )

    proyectos = _proyectos_para_sync(_args(todos=True))
    rutas = [os.path.normcase(os.path.realpath(r)) for _, r in proyectos]
    esperada = os.path.normcase(os.path.realpath(str(proyecto)))

    assert len(rutas) == len(set(rutas)), rutas
    assert rutas.count(esperada) == 1, rutas

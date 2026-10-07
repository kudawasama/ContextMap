"""Repaso espaciado SM-2 (F11) del mundo conocimiento."""

from __future__ import annotations

import os
from datetime import date

from context_map.domain.knowledge import review as rv
from context_map.domain.knowledge import wiki as kb
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento

HOY = date(2026, 10, 7)


def _vault(tmp_path) -> str:
    """Crea un vault PKM con una página y devuelve su ruta."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    kb.ingresar(vdir, "Sistemas RAG", "RAG combina recuperación con generación de texto.")
    return vdir


def test_sm2_primer_acierto() -> None:
    """La primera respuesta correcta deja intervalo 1 día y sube el ease."""
    nuevo = rv.calcular_sm2(None, 5, HOY)
    assert nuevo["repetitions"] == 1
    assert nuevo["interval"] == 1
    assert nuevo["ease"] == 2.6
    assert nuevo["due"] == "2026-10-08"


def test_sm2_fallo_reinicia() -> None:
    """Una calificación <3 reinicia las repeticiones y el intervalo."""
    previo = {"repetitions": 3, "interval": 15, "ease": 2.5, "due": "2026-10-01"}
    nuevo = rv.calcular_sm2(previo, 2, HOY)
    assert nuevo["repetitions"] == 0
    assert nuevo["interval"] == 1


def test_sm2_secuencia_de_aciertos() -> None:
    """La secuencia 1-6-días y luego intervalo*ease es la esperada."""
    e1 = rv.calcular_sm2(None, 4, HOY)
    e2 = rv.calcular_sm2(e1, 4, HOY)
    e3 = rv.calcular_sm2(e2, 4, HOY)
    assert (e1["interval"], e2["interval"], e3["interval"]) == (1, 6, 15)
    assert e3["repetitions"] == 3


def test_paginas_due_incluye_nuevas(tmp_path) -> None:
    """Una página nunca repasada está vencida; tras calificarla deja de estarlo."""
    vdir = _vault(tmp_path)
    pendientes = rv.paginas_due(vdir, hoy=HOY)
    assert len(pendientes) == 1
    assert pendientes[0]["due"] == ""

    rv.calificar(vdir, pendientes[0]["titulo"], 5, hoy=HOY)

    # Reprogramada para mañana → ya no está vencida hoy.
    assert rv.paginas_due(vdir, hoy=HOY) == []
    assert rv.contar_due(vdir, hoy=date(2026, 10, 8)) == 1


def test_calificar_persiste_estado(tmp_path) -> None:
    """El estado del repaso se guarda en disco y se puede recargar."""
    vdir = _vault(tmp_path)
    rv.calificar(vdir, "Sistemas RAG", 5, hoy=HOY)

    assert os.path.exists(rv.ruta_estado(vdir))
    estado = rv.cargar_estado(vdir)
    assert len(estado["paginas"]) == 1
    assert next(iter(estado["paginas"].values()))["interval"] == 1

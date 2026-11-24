"""Contrato de las reglas fijas de estabilidad (invariantes del motor).

Estos tests son la garantía de que el catálogo de
``context_map/domain/health/invariantes.py`` no se queda huérfano: cada
invariante declarado debe seguir midiéndose con un chequeo real del doctor y el
puente `--strict-warn` debe seguir cortando el proceso.
"""

from __future__ import annotations

import subprocess
import sys

from context_map.domain.health import doctor, invariantes


def test_cada_invariante_tiene_chequeo_real(tmp_path):
    """Cada invariante apunta a un chequeo que el doctor ejecuta de verdad."""
    report = doctor.diagnosticar_salud(str(tmp_path))
    medidos = {c.name for c in report.checks}

    faltantes = [inv.chequeo for inv in invariantes.INVARIANTES if inv.chequeo not in medidos]

    assert not faltantes, f"invariantes sin chequeo en el doctor: {faltantes}"


def test_invariantes_declaran_severidad_valida():
    """La severidad solo puede ser FAIL o WARN (nada de estados inventados)."""
    for inv in invariantes.INVARIANTES:
        assert inv.severidad in {"FAIL", "WARN"}, inv.nombre
        assert inv.motivo.strip(), inv.nombre
        assert inv.reparacion.strip(), inv.nombre


def test_incumplidas_detecta_fail_y_warn(tmp_path):
    """`incumplidas` traduce estados del doctor a reglas rotas."""
    report = doctor.DoctorReport()
    for inv in invariantes.INVARIANTES:
        report.add(doctor.DoctorCheck(name=inv.chequeo, status="OK"))

    assert invariantes.incumplidas(report) == []

    primero = invariantes.INVARIANTES[0]
    report.add(doctor.DoctorCheck(name=primero.chequeo, status="FAIL"))
    rotos = invariantes.incumplidas(report)

    assert [inv.chequeo for inv in rotos] == [primero.chequeo]


def test_strict_warn_corta_el_proceso():
    """`doctor --strict-warn` sale con código 1 en un proyecto sin vault."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        proceso = subprocess.run(
            [sys.executable, "-m", "context_map.cli", "doctor", tmp, "--strict-warn"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    assert proceso.returncode == 1

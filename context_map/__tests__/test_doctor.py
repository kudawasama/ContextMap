"""Tests para el módulo doctor.py (diagnóstico y auto-reparación Self-Healing)."""

from __future__ import annotations

import os
import time

from context_map.domain.health.doctor import diagnosticar_salud, reparar_salud
from context_map.presentation.briefs.extractors import vault_nombre


def test_doctor_diagnosticar_salud(tmp_path, monkeypatch):
    """Verifica que diagnosticar_salud retorna un reporte OK."""
    # Aísla la verificación de ~/.context-map-update a un directorio limpio
    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    monkeypatch.setattr("os.path.expanduser", lambda path: str(fake_home) if "~" in path else os.path.expanduser(path))

    report = diagnosticar_salud(str(tmp_path))
    assert report.ok
    assert len(report.checks) >= 4


def test_doctor_reparar_salud_preserva_notas(tmp_path):
    """Verifica que reparar_salud inyecta preserve: true en notas manuales sin borrarlas."""
    repo_name = os.path.basename(os.path.abspath(str(tmp_path)))
    vname = vault_nombre(repo_name)
    manual_dir = tmp_path / ".context-map" / vname / "7.0-MANUAL"
    manual_dir.mkdir(parents=True)
    nota = manual_dir / "BACKLOG.md"
    nota.write_text("# Backlog\n- [ ] Tarea importante", encoding="utf-8")

    report = reparar_salud(str(tmp_path))
    assert report.ok
    content = nota.read_text(encoding="utf-8")
    assert "preserve: true" in content
    assert "Tarea importante" in content


def test_doctor_reparar_vaults_desalineados(tmp_path):
    """Verifica que vaults desalineados se mueven a _legacy sin borrar su contenido."""
    ctx_dir = tmp_path / ".context-map"
    (ctx_dir / "vault-Viejo").mkdir(parents=True)
    (ctx_dir / "vault-Viejo" / "nota.md").write_text("# Nota", encoding="utf-8")

    # El vault esperado para tmp_path será vault-<nombre del directorio>
    reparar_salud(str(tmp_path))
    assert os.path.isdir(ctx_dir / "_legacy" / "vault-Viejo")


def test_check_history_avisa_con_historial_grande(tmp_path, monkeypatch):
    """`doctor` marca WARN si el historial supera el umbral configurado."""
    from context_map.core.storage.history import HistoryStats
    from context_map.domain.health import doctor

    hist = tmp_path / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True)
    (hist / "s0.md").write_bytes(b"x" * 1024)

    monkeypatch.setattr(
        doctor,
        "estadisticas",
        lambda *a, **k: HistoryStats(files=200, bytes=2048 * 1024 * 1024),
    )
    report = doctor.DoctorReport()
    doctor.check_history(report, fix=False, project_dir=str(tmp_path))

    assert report.checks[0].status == "WARN"
    assert "history prune" in report.checks[0].message


def test_check_history_ok_sin_snapshots(tmp_path):
    """Sin historial el chequeo queda en OK."""
    from context_map.domain.health import doctor

    report = doctor.DoctorReport()
    doctor.check_history(report, fix=False, project_dir=str(tmp_path))

    assert report.checks[0].status == "OK"


def test_check_history_fix_poda(tmp_path):
    """Con fix=True el chequeo poda el historial por encima del umbral."""
    from context_map.domain.health import doctor

    hist = tmp_path / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True)
    for i in range(120):  # supera KEEP_DEFAULT * 5
        f = hist / f"s{i:03d}.md"
        f.write_bytes(b"x" * 512)
        os.utime(f, (time.time() + i, time.time() + i))

    report = doctor.DoctorReport()
    doctor.check_history(report, fix=True, project_dir=str(tmp_path))

    check = report.checks[0]
    assert check.fix_applied is True
    assert len(list(hist.glob("*.md"))) <= doctor.KEEP_DEFAULT

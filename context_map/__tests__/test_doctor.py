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


def test_check_history_ok_sin_snapshots(tmp_path):
    """Sin historial el chequeo queda en OK."""
    from context_map.domain.health import doctor

    report = doctor.DoctorReport()
    doctor.check_history(report, fix=False, project_dir=str(tmp_path))

    assert report.checks[0].status == "OK"


def test_check_history_avisa_con_historial_grande(tmp_path):
    """WARN cuando el historial supera el umbral (5× keep por defecto)."""
    from context_map.core.storage.store import SNAPSHOT_KEEP_DEFAULT
    from context_map.domain.health import doctor

    hist = tmp_path / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True)
    for i in range(SNAPSHOT_KEEP_DEFAULT * 5 + 1):
        (hist / f"s{i:03d}.md").write_text("# s\n", encoding="utf-8")

    report = doctor.DoctorReport()
    doctor.check_history(report, fix=False, project_dir=str(tmp_path))

    assert report.checks[0].status == "WARN"
    assert "history prune" in report.checks[0].message


def test_check_history_fix_archiva(tmp_path):
    """Con fix=True poda/archiva y deja el historial dentro del tope."""
    from context_map.core.storage.store import SNAPSHOT_KEEP_DEFAULT
    from context_map.domain.health import doctor

    hist = tmp_path / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True)
    for i in range(SNAPSHOT_KEEP_DEFAULT * 5 + 10):
        fichero = hist / f"s{i:03d}.md"
        fichero.write_text("# s\n", encoding="utf-8")
        momento = time.time() + i
        os.utime(fichero, (momento, momento))

    report = doctor.DoctorReport()
    doctor.check_history(report, fix=True, project_dir=str(tmp_path))

    check = report.checks[0]
    assert check.fix_applied is True
    assert "archivados" in check.fix_message
    assert len(list(hist.glob("*.md"))) <= SNAPSHOT_KEEP_DEFAULT + 1


def test_check_interpreter_ok_sin_venv(tmp_path):
    """Sin `.venv` en el proyecto el chequeo es OK (no hay intérprete exigido)."""
    from context_map.domain.health import doctor

    report = doctor.DoctorReport()
    doctor.check_interpreter(report, fix=False, project_dir=str(tmp_path))

    check = report.checks[0]
    assert check.name == "interpreter"
    assert check.status == "OK"
    assert "Sin venv" in check.message


def test_check_interpreter_avisa_si_no_es_el_del_venv(tmp_path):
    """Con `.venv` presente y otro intérprete activo, avisa (regla fija)."""
    from context_map.domain.health import doctor

    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "python.exe").write_text("", encoding="utf-8")

    report = doctor.DoctorReport()
    doctor.check_interpreter(report, fix=False, project_dir=str(tmp_path))

    check = report.checks[0]
    assert check.status == "WARN"
    assert "venv del proyecto" in check.message


def test_check_interpreter_ok_si_coincide(tmp_path, monkeypatch):
    """Si el intérprete activo es el del venv, el chequeo es OK."""
    from context_map.domain.health import doctor

    scripts = tmp_path / ".venv" / "Scripts"
    scripts.mkdir(parents=True)
    falso = scripts / "python.exe"
    falso.write_text("", encoding="utf-8")
    monkeypatch.setattr(doctor.sys, "executable", str(falso))

    report = doctor.DoctorReport()
    doctor.check_interpreter(report, fix=False, project_dir=str(tmp_path))

    assert report.checks[0].status == "OK"


def test_check_mcp_deps_no_sugiere_paquete_inexistente():
    """El consejo de reparación debe ser instalable (no `ctxmap-ai`, ausente en PyPI)."""
    from context_map.domain.health import doctor

    report = doctor.DoctorReport()
    doctor.check_mcp_deps(report, fix=False, project_dir=".")

    check = report.checks[0]
    assert check.name == "mcp_deps"
    assert "ctxmap-ai" not in check.message
    if check.status == "FAIL":
        assert "[mcp]" in check.message


def test_checks_incluye_interpreter_antes_de_mcp():
    """El orden importa: primero el intérprete, después sus dependencias."""
    from context_map.domain.health import doctor

    nombres = [fn.__name__ for fn in doctor.CHECKS]
    assert "check_interpreter" in nombres
    assert nombres.index("check_interpreter") < nombres.index("check_mcp_deps")


def test_cli_doctor_expone_strict_warn():
    """La bandera de CI (`--strict-warn`) existe y se parsea."""
    from context_map.application.cli.parser import create_parser

    args = create_parser().parse_args(["doctor", ".", "--strict-warn"])
    assert args.strict_warn is True
    assert args.strict is False


def test_skill_collisions_no_reporta_la_misma_ruta_dos_veces(tmp_path, monkeypatch):
    """El mismo SKILL.md alcanzado por dos raíces no es una colisión.

    Regresión: el chequeo recorría ``~/.pi/agent/npm/node_modules`` entero y
    además el glob ``*/*/skills``, así que cada skill se encontraba dos veces y
    siete «colisiones» fantasma tapaban la única real.
    """
    from context_map.domain.health.doctor import DoctorReport, check_skill_collisions

    home = tmp_path / "home"
    skill = home / ".agents" / "skills" / "demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("---\nname: demo\n---\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    report = DoctorReport()
    # project_dir == home: las dos raíces (.agents del proyecto y del usuario)
    # apuntan al mismo directorio.
    check_skill_collisions(report, project_dir=str(home))

    check = report.checks[0]
    assert check.status == "OK", check.message
    assert "demo:" not in check.message


def test_skill_collisions_detecta_duplicados_reales(tmp_path, monkeypatch):
    """Dos copias con el mismo nombre en orígenes distintos sí son colisión."""
    from context_map.domain.health.doctor import DoctorReport, check_skill_collisions

    home = tmp_path / "home"
    proyecto = tmp_path / "proyecto"
    for base in (home, proyecto):
        ruta = base / ".agents" / "skills" / "demo" / "SKILL.md"
        ruta.parent.mkdir(parents=True)
        ruta.write_text("---\nname: demo\n---\n", encoding="utf-8")

    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))

    report = DoctorReport()
    check_skill_collisions(report, project_dir=str(proyecto))

    check = report.checks[0]
    assert check.status == "WARN"
    assert "demo:" in check.message
    assert check.message.count("SKILL.md") == 2

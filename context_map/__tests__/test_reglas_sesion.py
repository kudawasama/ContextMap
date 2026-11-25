"""Contrato de los seis chequeos de conducta de la sesión.

Se fabrican bitácoras y repositorios reales en ``tmp_path``: lo que se prueba es
la lectura de la evidencia, no la opinión del agente. Cada chequeo se mide en su
cara verde y en su cara roja, porque un chequeo que solo sabe avisar es un
estornudo y uno que nunca avisa es un adorno.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from context_map.domain.health import reglas_sesion as sesion
from context_map.domain.health.doctor import DoctorReport

SECRETO_AWS = "AKIAQWERTYUIOPASDFGH"


def _estado(chequeo, raiz: Path) -> tuple[str, str]:
    report = DoctorReport()
    chequeo(report, project_dir=str(raiz))
    return report.checks[0].status, report.checks[0].message


def _bitacora(raiz: Path, entradas: list[dict]) -> Path:
    ruta = raiz / ".context-map" / "state" / "bitacora.jsonl"
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        "\n".join(json.dumps(e, ensure_ascii=False) for e in entradas) + "\n",
        encoding="utf-8",
    )
    return ruta


def _git(raiz: Path, *args: str) -> str | None:
    try:
        proceso = subprocess.run(
            ["git", *args], cwd=str(raiz), capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proceso.stdout if proceso.returncode == 0 else None


def _repo(
    raiz: Path,
    archivos: dict[str, str] | None = None,
    mensaje: str = "feat: algo",
    fecha: str | None = None,
) -> Path:
    if _git(raiz, "rev-parse", "--git-dir") is None:
        assert _git(raiz, "init", "-q") is not None
    for ruta, contenido in (archivos or {"README.md": "# x\n"}).items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    assert _git(raiz, "add", "-A") is not None
    entorno = dict(os.environ)
    if fecha:
        entorno["GIT_AUTHOR_DATE"] = fecha
        entorno["GIT_COMMITTER_DATE"] = fecha
    proceso = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com",
         "commit", "-q", "-m", mensaje],
        cwd=str(raiz), capture_output=True, text=True, env=entorno, timeout=30,
    )
    assert proceso.returncode == 0, proceso.stderr
    return raiz


HOY = datetime.now().strftime("%Y-%m-%d")
#: Primer instante del día: sirve de "evidencia anterior al commit de ahora".
PASADO = f"{HOY}T00:00:01"
#: Último instante del día: sirve de "evidencia posterior al commit de ahora".
FUTURO = f"{HOY}T23:59:59"


# ── bitacora_sesion: INI-001, INI-002, EJE-002, SAL-002 ───────────────────

def test_sin_actividad_no_hay_nada_que_auditar(tmp_path):
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "OK"
    assert "Sin actividad" in mensaje


def test_sesion_con_evidencia_completa(tmp_path):
    _repo(tmp_path)
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "brief", "exit": 0},
        {"ts": PASADO, "comando": "doctor", "exit": 0, "duracion_s": 11.0},
    ])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "OK", mensaje
    assert "brief leído" in mensaje


def test_sin_leer_el_brief_avisa(tmp_path):
    _repo(tmp_path)
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 0}])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "WARN"
    assert "REG-INI-002" in mensaje


def test_commit_sin_diagnostico_previo_avisa(tmp_path):
    _repo(tmp_path)
    # el registro nace de madrugada, pero el doctor llega después del commit de hoy
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "brief", "exit": 0},
        {"ts": FUTURO, "comando": "doctor", "exit": 0},
    ])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "WARN"
    assert "REG-INI-001" in mensaje


def test_los_commits_anteriores_a_la_bitacora_no_se_juzgan(tmp_path):
    """No se puede exigir evidencia de un día en el que el registro no existía."""
    _repo(tmp_path, fecha=f"{HOY}T00:00:00")
    _bitacora(tmp_path, [{"ts": f"{HOY}T00:00:30", "comando": "brief", "exit": 0}])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "OK", mensaje


def test_puerta_final_en_rojo_avisa(tmp_path):
    _repo(tmp_path)
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "brief", "exit": 0},
        {"ts": PASADO, "comando": "doctor", "exit": 0},
        {"ts": FUTURO, "comando": "doctor", "exit": 1},
    ])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "WARN"
    assert "REG-SAL-002" in mensaje


def test_trabajar_sin_diagnostico_avisa(tmp_path):
    _repo(tmp_path)
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "brief", "exit": 0}])
    estado, mensaje = _estado(sesion.check_bitacora_sesion, tmp_path)
    assert estado == "WARN"
    assert "REG-EJE-002" in mensaje


# ── permisos_explicitos: EJE-004, SAL-003, PUB-003 ────────────────────────

def test_sin_ejecuciones_sensibles_esta_verde(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 0}])
    estado, mensaje = _estado(sesion.check_permisos_explicitos, tmp_path)
    assert estado == "OK"
    assert "Ninguna ejecución sensible" in mensaje


def test_adapt_sin_permiso_avisa(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "adapt", "exit": 0, "autorizado": False},
    ])
    estado, mensaje = _estado(sesion.check_permisos_explicitos, tmp_path)
    assert estado == "WARN"
    assert "REG-EJE-004" in mensaje


def test_adapt_autorizado_esta_verde(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "adapt", "exit": 0, "autorizado": True},
    ])
    estado, _ = _estado(sesion.check_permisos_explicitos, tmp_path)
    assert estado == "OK"


def test_fix_sin_permiso_avisa(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "doctor", "exit": 0, "flags": ["fix"], "autorizado": False},
    ])
    estado, mensaje = _estado(sesion.check_permisos_explicitos, tmp_path)
    assert estado == "WARN"
    assert "REG-SAL-003" in mensaje


def test_fix_con_permiso_esta_verde(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "doctor", "exit": 0, "flags": ["fix"], "autorizado": True},
    ])
    estado, _ = _estado(sesion.check_permisos_explicitos, tmp_path)
    assert estado == "OK"


# ── tag_con_puerta_verde: PUB-002 ─────────────────────────────────────────

def test_sin_git_no_juzga_tags(tmp_path):
    estado, mensaje = _estado(sesion.check_tag_con_puerta_verde, tmp_path)
    assert estado == "OK"
    assert "Sin git" in mensaje


def test_sin_tags_esta_verde(tmp_path):
    _repo(tmp_path)
    estado, mensaje = _estado(sesion.check_tag_con_puerta_verde, tmp_path)
    assert estado == "OK"
    assert "Sin tags" in mensaje


def test_tags_anteriores_a_la_bitacora_no_se_juzgan(tmp_path):
    _repo(tmp_path)
    assert _git(tmp_path, "tag", "v1.0.0") is not None
    _bitacora(tmp_path, [{"ts": FUTURO, "comando": "doctor", "exit": 0}])
    estado, mensaje = _estado(sesion.check_tag_con_puerta_verde, tmp_path)
    assert estado == "OK"
    assert "anteriores a la bitácora" in mensaje


def test_tag_nuevo_sin_doctor_en_verde_avisa(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 1}])
    _repo(tmp_path)
    assert _git(tmp_path, "tag", "v9.9.9") is not None
    estado, mensaje = _estado(sesion.check_tag_con_puerta_verde, tmp_path)
    assert estado == "WARN"
    assert "REG-PUB-002" in mensaje


def test_tag_nuevo_con_doctor_en_verde_esta_amparado(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 0}])
    _repo(tmp_path)
    assert _git(tmp_path, "tag", "v9.9.9") is not None
    estado, mensaje = _estado(sesion.check_tag_con_puerta_verde, tmp_path)
    assert estado == "OK", mensaje
    assert "amparado" in mensaje


# ── secreto_en_el_historial: SEG-003 ──────────────────────────────────────

def test_sin_git_no_escanea_historial(tmp_path):
    estado, mensaje = _estado(sesion.check_secreto_en_el_historial, tmp_path)
    assert estado == "OK"
    assert "Sin git" in mensaje


def test_credencial_en_el_codigo_avisa_sin_copiarla(tmp_path):
    _repo(tmp_path, {"config.py": f'CLAVE = "{SECRETO_AWS}"\n'})
    estado, mensaje = _estado(sesion.check_secreto_en_el_historial, tmp_path)
    assert estado == "WARN"
    assert "REG-SEG-003" in mensaje
    assert SECRETO_AWS not in mensaje, "el reporte no puede propagar el secreto"


def test_credencial_en_un_test_es_fixture(tmp_path):
    _repo(tmp_path, {
        "context_map/__tests__/test_x.py": f'TOKEN = "{SECRETO_AWS}"\n',
    })
    estado, mensaje = _estado(sesion.check_secreto_en_el_historial, tmp_path)
    assert estado == "OK", mensaje
    assert "fixtures" in mensaje


def test_la_definicion_del_patron_no_es_un_secreto(tmp_path):
    """Buscar 'AKIA' a secas marcaba el propio detector como credencial."""
    _repo(tmp_path, {
        "security.py": 'PATRON = re.compile(r"AKIA[0-9A-Z]{16}")\n',
    })
    estado, _ = _estado(sesion.check_secreto_en_el_historial, tmp_path)
    assert estado == "OK"


def test_repo_limpio_esta_verde(tmp_path):
    _repo(tmp_path, {"main.py": "print('hola')\n"})
    estado, mensaje = _estado(sesion.check_secreto_en_el_historial, tmp_path)
    assert estado == "OK"
    assert "Sin credenciales reales" in mensaje


# ── historia_preservada: HUM-002 ──────────────────────────────────────────

def test_menos_de_dos_construcciones_no_comparan(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "build", "exit": 0, "notas": 100}])
    estado, mensaje = _estado(sesion.check_historia_preservada, tmp_path)
    assert estado == "OK"
    assert "nada que comparar" in mensaje


def test_vault_que_crece_esta_verde(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "build", "exit": 0, "notas": 100},
        {"ts": PASADO, "comando": "build", "exit": 0, "notas": 120},
    ])
    estado, mensaje = _estado(sesion.check_historia_preservada, tmp_path)
    assert estado == "OK"
    assert "creció" in mensaje


def test_vault_que_pierde_notas_avisa(tmp_path):
    _bitacora(tmp_path, [
        {"ts": PASADO, "comando": "build", "exit": 0, "notas": 135},
        {"ts": PASADO, "comando": "build", "exit": 0, "notas": 96},
    ])
    estado, mensaje = _estado(sesion.check_historia_preservada, tmp_path)
    assert estado == "WARN"
    assert "REG-HUM-002" in mensaje
    assert "96" in mensaje


# ── doctor_rapido: LIM-002 ────────────────────────────────────────────────

def test_sin_mediciones_esta_verde(tmp_path):
    estado, mensaje = _estado(sesion.check_doctor_rapido, tmp_path)
    assert estado == "OK"
    assert "empieza a contar" in mensaje


def test_doctor_rapido_esta_verde(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 0, "duracion_s": 12.3}])
    estado, mensaje = _estado(sesion.check_doctor_rapido, tmp_path)
    assert estado == "OK"
    assert "12.3 s" in mensaje


def test_doctor_lento_avisa(tmp_path):
    _bitacora(tmp_path, [{"ts": PASADO, "comando": "doctor", "exit": 0, "duracion_s": 300.0}])
    estado, mensaje = _estado(sesion.check_doctor_rapido, tmp_path)
    assert estado == "WARN"
    assert "REG-LIM-002" in mensaje


def test_el_limite_es_declarado_y_no_oculto(tmp_path):
    assert sesion.LIMITE_DOCTOR_SEGUNDOS == 120.0

"""Contrato de los chequeos de conducta (``domain/health/reglas_proyecto.py``).

Cada prueba construye un repositorio git de verdad en ``tmp_path``: simular
``subprocess`` probaría el mock, no la regla. Todas comprueban las dos caras:
que la regla **detecte** la violación y que **no** invente avisos cuando el
proyecto cumple.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from context_map.domain.health.doctor import DoctorReport
from context_map.domain.health.reglas_proyecto import (
    _es_convencional,
    _es_falso_positivo,
    _es_merge,
    _toca_codigo,
    check_changelog_commit,
    check_commits_convencionales,
    check_diario_del_dia,
    check_secretos_versionados,
)

sin_git = pytest.mark.skipif(shutil.which("git") is None, reason="git no disponible")

#: Secreto con forma realista (AWS): 4 + 16 mayúsculas.
SECRETO = "AKIAQWERTYUIOPASDFGH"


def _git(raiz, *args) -> str:
    resultado = subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        cwd=str(raiz),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert resultado.returncode == 0, resultado.stderr
    return resultado.stdout


def _repo(tmp_path, archivos: dict[str, str], mensaje: str = "feat: inicial"):
    raiz = tmp_path / "repo"
    raiz.mkdir()
    _git(raiz, "init", "-q")
    _escribir(raiz, archivos)
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", mensaje)
    return raiz


def _escribir(raiz, archivos: dict[str, str]) -> None:
    for ruta, contenido in archivos.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")


def _estado(chequeo, raiz) -> tuple[str, str]:
    report = DoctorReport()
    chequeo(report, project_dir=str(raiz))
    return report.checks[0].status, report.checks[0].message


# ── clasificadores puros ──────────────────────────────────────────────────

@pytest.mark.parametrize(
    "asunto",
    [
        "feat: catalogo de reglas",
        "fix(doctor): no caer con una nota corrupta",
        "docs: comandos sin make",
        "refactor!: partir el modulo",
    ],
)
def test_asuntos_convencionales(asunto: str) -> None:
    assert _es_convencional(asunto)


@pytest.mark.parametrize(
    "asunto",
    ["arreglos varios", "Feat: mayúscula", "fix : espacio", "fix: ", "wip"],
)
def test_asuntos_no_convencionales(asunto: str) -> None:
    assert not _es_convencional(asunto)


@pytest.mark.parametrize(
    "asunto", ["Merge branch 'main'", "Merge pull request #8 from x/y"]
)
def test_los_merges_no_cuentan(asunto: str) -> None:
    assert _es_merge(asunto)


def test_solo_codigo_de_la_aplicacion_cuenta_como_codigo() -> None:
    assert _toca_codigo(["context_map/domain/x.py"])
    assert not _toca_codigo(["context_map/__tests__/test_x.py"])
    assert not _toca_codigo(["README.md", "docs/x.md"])
    assert not _toca_codigo(["setup.py"])


@pytest.mark.parametrize(
    "ruta",
    [
        "context_map/__tests__/test_security_scanner.py",
        "tests/test_algo.py",
        "conftest.py",
    ],
)
def test_los_tests_son_falsos_positivos(ruta: str) -> None:
    assert _es_falso_positivo(ruta, f'api_key = "{SECRETO}"')


def test_un_marcador_de_ejemplo_es_falso_positivo() -> None:
    assert _es_falso_positivo("docs/x.md", 'api_key = "tu-token-de-ejemplo-aqui"')
    assert not _es_falso_positivo("context_map/x.py", f'api_key = "{SECRETO}"')


# ── commits convencionales ────────────────────────────────────────────────

@sin_git
def test_commits_convencionales_detecta_el_suelto(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "hola"}, mensaje="feat: inicial")
    _escribir(raiz, {"b.txt": "x"})
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "arreglos varios")

    estado, mensaje = _estado(check_commits_convencionales, raiz)
    assert estado == "WARN"
    assert "1 de 2" in mensaje
    assert "arreglos varios" in mensaje


@sin_git
def test_commits_convencionales_en_verde(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "hola"}, mensaje="feat: inicial")
    estado, mensaje = _estado(check_commits_convencionales, raiz)
    assert estado == "OK"
    assert "Conventional Commits" in mensaje


@sin_git
def test_sin_repositorio_git_no_inventa_avisos(tmp_path):
    estado, mensaje = _estado(check_commits_convencionales, tmp_path)
    assert estado == "OK"
    assert "Sin historial" in mensaje


# ── CHANGELOG en el commit ────────────────────────────────────────────────

@sin_git
def test_changelog_avisa_si_el_commit_cambia_codigo_sin_registrarlo(tmp_path):
    raiz = _repo(tmp_path, {"CHANGELOG.md": "# Changelog\n"})
    _escribir(raiz, {"context_map/modulo.py": "x = 1\n"})
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "feat(modulo): algo nuevo")

    estado, mensaje = _estado(check_changelog_commit, raiz)
    assert estado == "WARN"
    assert "sin tocar CHANGELOG.md" in mensaje


@sin_git
def test_changelog_en_verde_si_el_commit_lo_toca(tmp_path):
    raiz = _repo(tmp_path, {"CHANGELOG.md": "# Changelog\n"})
    _escribir(raiz, {"context_map/modulo.py": "x = 1\n", "CHANGELOG.md": "# Changelog\n\n- algo\n"})
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "feat(modulo): algo nuevo")

    estado, mensaje = _estado(check_changelog_commit, raiz)
    assert estado == "OK"
    assert "CHANGELOG al día" in mensaje


@sin_git
def test_changelog_no_exige_nada_a_un_commit_de_documentacion(tmp_path):
    raiz = _repo(tmp_path, {"README.md": "# Hola\n"})
    _escribir(raiz, {"README.md": "# Hola\n\nMás texto\n"})
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "docs: ampliar readme")

    estado, _ = _estado(check_changelog_commit, raiz)
    assert estado == "OK"


@sin_git
def test_changelog_no_cuenta_los_tests_como_codigo(tmp_path):
    raiz = _repo(tmp_path, {"CHANGELOG.md": "# Changelog\n"})
    _escribir(raiz, {"context_map/__tests__/test_x.py": "def test_x(): pass\n"})
    _git(raiz, "add", "-A")
    _git(raiz, "commit", "-q", "-m", "test: cubrir x")

    estado, _ = _estado(check_changelog_commit, raiz)
    assert estado == "OK"


# ── diario del día ────────────────────────────────────────────────────────

@sin_git
def test_diario_avisa_si_hoy_hay_commits_y_no_hay_nota(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "x"})
    (raiz / ".context-map" / "vault-Demo" / "7.0-MANUAL" / "Diario").mkdir(parents=True)

    estado, mensaje = _estado(check_diario_del_dia, raiz)
    assert estado == "WARN"
    assert "el diario no tiene la nota" in mensaje


@sin_git
def test_diario_en_verde_con_la_nota_de_hoy(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "x"})
    diario = raiz / ".context-map" / "vault-Demo" / "7.0-MANUAL" / "Diario"
    diario.mkdir(parents=True)
    from datetime import date

    (diario / f"{date.today().isoformat()}.md").write_text("# Hoy\n", encoding="utf-8")

    estado, mensaje = _estado(check_diario_del_dia, raiz)
    assert estado == "OK"
    assert "Diario del día presente" in mensaje


@sin_git
def test_diario_sin_vault_no_exige_nada(tmp_path):
    raiz = _repo(tmp_path, {"a.txt": "x"})
    estado, mensaje = _estado(check_diario_del_dia, raiz)
    assert estado == "OK"
    assert "Sin vault" in mensaje


# ── secretos versionados ──────────────────────────────────────────────────

@sin_git
def test_secretos_detecta_una_clave_real_y_no_la_imprime(tmp_path):
    raiz = _repo(tmp_path, {"config.py": f'API_KEY = "AKIAQWERTYUIOPASDFGH"\n'})

    estado, mensaje = _estado(check_secretos_versionados, raiz)
    assert estado == "WARN"
    assert "config.py:1" in mensaje
    assert "clave de AWS" in mensaje
    # El reporte nunca debe copiar el secreto al log.
    assert SECRETO not in mensaje


@sin_git
def test_secretos_ignora_los_tests_y_los_ejemplos(tmp_path):
    raiz = _repo(
        tmp_path,
        {
            "context_map/__tests__/test_scanner.py": f'TOKEN = "{SECRETO}"\n',
            "docs/ejemplo.md": 'api_key = "tu-token-de-ejemplo-aqui"\n',
            "context_map/limpio.py": "x = 1\n",
        },
    )

    estado, mensaje = _estado(check_secretos_versionados, raiz)
    assert estado == "OK"
    assert "Sin secretos" in mensaje


@sin_git
def test_secretos_no_mira_lo_que_git_no_rastrea(tmp_path):
    raiz = _repo(tmp_path, {"limpio.py": "x = 1\n"})
    _escribir(raiz, {"secreto.py": f'API_KEY = "{SECRETO}"\n'})

    estado, _ = _estado(check_secretos_versionados, raiz)
    assert estado == "OK"

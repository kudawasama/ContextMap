"""Contrato de los chequeos de calidad del repositorio.

Cada prueba construye un árbol de proyecto real en ``tmp_path``: se mide el
código que corre, no una simulación. Todas comprueban las dos caras —detectar y
no inventar avisos— porque un chequeo que siempre está en verde es decoración y
uno que siempre está en rojo deja de leerse.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from context_map.domain.health import reglas_calidad as calidad
from context_map.domain.health.doctor import DoctorReport


def _estado(chequeo, raiz: Path) -> tuple[str, str]:
    report = DoctorReport()
    chequeo(report, project_dir=str(raiz))
    return report.checks[0].status, report.checks[0].message


def _escribir(raiz: Path, archivos: dict[str, str]) -> Path:
    for ruta, contenido in archivos.items():
        destino = raiz / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
    return raiz


# ── PUB-001 versión anunciada ─────────────────────────────────────────────

def test_version_anunciada_en_verde(tmp_path):
    _escribir(tmp_path, {
        "pyproject.toml": '[project]\nversion = "1.4.2"\n',
        "CHANGELOG.md": "# Changelog\n\n## [1.4.2] - 2026-11-25\n\n- algo\n",
    })
    estado, mensaje = _estado(calidad.check_version_documentada, tmp_path)
    assert estado == "OK"
    assert "1.4.2" in mensaje


def test_version_sin_anuncio_avisa(tmp_path):
    _escribir(tmp_path, {
        "pyproject.toml": '[project]\nversion = "1.5.0"\n',
        "CHANGELOG.md": "# Changelog\n\n## [1.4.2]\n",
    })
    estado, mensaje = _estado(calidad.check_version_documentada, tmp_path)
    assert estado == "WARN"
    assert "REG-PUB-001" in mensaje


def test_version_sin_changelog_avisa(tmp_path):
    _escribir(tmp_path, {"pyproject.toml": 'version = "1.0.0"\n'})
    estado, _ = _estado(calidad.check_version_documentada, tmp_path)
    assert estado == "WARN"


def test_sin_pyproject_no_hay_version_que_anunciar(tmp_path):
    estado, mensaje = _estado(calidad.check_version_documentada, tmp_path)
    assert estado == "OK"
    assert "Sin pyproject.toml" in mensaje


# ── LIM-003 derivados fuera de git ────────────────────────────────────────

def _repo(raiz: Path, archivos: dict[str, str]) -> Path:
    _escribir(raiz, archivos)
    subprocess.run(["git", "init", "-q"], cwd=str(raiz), check=True)
    subprocess.run(["git", "add", "-A"], cwd=str(raiz), check=True)
    return raiz


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git no disponible",
)
def test_derivados_fuera_de_git_en_verde(tmp_path):
    _repo(tmp_path, {"context_map/a.py": "x = 1\n", ".gitignore": ".context-map/\n"})
    estado, mensaje = _estado(calidad.check_derivados_fuera_de_git, tmp_path)
    assert estado == "OK"
    assert "Nada derivado" in mensaje


@pytest.mark.skipif(
    subprocess.run(["git", "--version"], capture_output=True).returncode != 0,
    reason="git no disponible",
)
def test_vault_versionado_avisa(tmp_path):
    _repo(tmp_path, {
        ".context-map/vault-Demo/00-INDICE.md": "# Índice\n",
        ".context-map/state/graph.jsonl": "{}\n",
    })
    estado, mensaje = _estado(calidad.check_derivados_fuera_de_git, tmp_path)
    assert estado == "WARN"
    assert "REG-LIM-003" in mensaje


# ── ARQ-002 raíz limpia ───────────────────────────────────────────────────

def test_raiz_limpia_en_verde(tmp_path):
    _escribir(tmp_path, {
        "README.md": "# x\n", "LICENSE": "MIT\n", "pyproject.toml": "\n",
        "AGENTS.md": "# x\n", ".gitignore": "\n", "CHANGELOG.md": "# x\n",
        "Makefile": "all:\n", "mkdocs.yml": "site_name: x\n",
    })
    estado, mensaje = _estado(calidad.check_raiz_limpia, tmp_path)
    assert estado == "OK"
    assert "Raíz limpia" in mensaje


def test_archivo_suelto_en_la_raiz_avisa(tmp_path):
    _escribir(tmp_path, {"README.md": "# x\n", "arreglo_final_v2.py": "x = 1\n"})
    estado, mensaje = _estado(calidad.check_raiz_limpia, tmp_path)
    assert estado == "WARN"
    assert "arreglo_final_v2.py" in mensaje
    assert "REG-ARQ-002" in mensaje


def test_las_carpetas_de_la_raiz_no_cuentan(tmp_path):
    _escribir(tmp_path, {"README.md": "# x\n", "docs/guia.md": "# guía\n"})
    estado, _ = _estado(calidad.check_raiz_limpia, tmp_path)
    assert estado == "OK"


# ── ARQ-001/003 capas ─────────────────────────────────────────────────────

def test_capas_en_verde_sin_imports_cruzados(tmp_path):
    _escribir(tmp_path, {
        "context_map/core/base.py": "x = 1\n",
        "context_map/domain/servicio.py": "from context_map.core.base import x\n",
        "context_map/application/cli.py": "from context_map.domain.servicio import x\n",
        "context_map/infrastructure/api.py": "from context_map.core.base import x\n",
        "context_map/presentation/vista.py": "from context_map.domain.servicio import x\n",
    })
    estado, mensaje = _estado(calidad.check_capas_respetadas, tmp_path)
    assert estado == "OK"
    assert "0 import(s) cruzado(s)" in mensaje


def test_import_que_sube_de_capa_rompe_el_tope(tmp_path, monkeypatch):
    monkeypatch.setattr(calidad, "MAX_IMPORTS_CRUZADOS", 0)
    _escribir(tmp_path, {
        "context_map/core/base.py": "x = 1\n",
        "context_map/domain/servicio.py": "from context_map.core.base import x\n",
        "context_map/application/cli.py": "from context_map.domain.servicio import x\n",
        "context_map/infrastructure/api.py": "from context_map.core.base import x\n",
        "context_map/presentation/vista.py": "from context_map.core.base import x\n",
        # el dominio mirando hacia fuera: violación
        "context_map/domain/malo.py": "from context_map.presentation.vista import x\n",
    })
    estado, mensaje = _estado(calidad.check_capas_respetadas, tmp_path)
    assert estado == "WARN"
    assert "domain->presentation" in mensaje
    assert "REG-ARQ-003" in mensaje


def test_capa_ausente_avisa(tmp_path):
    _escribir(tmp_path, {"context_map/core/base.py": "x = 1\n"})
    estado, mensaje = _estado(calidad.check_capas_respetadas, tmp_path)
    assert estado == "WARN"
    assert "REG-ARQ-001" in mensaje


def test_sin_paquete_context_map_no_aplica(tmp_path):
    estado, mensaje = _estado(calidad.check_capas_respetadas, tmp_path)
    assert estado == "OK"
    assert "no hay capas" in mensaje


# ── ARQ-004 módulos con test ──────────────────────────────────────────────

def test_modulos_de_dominio_cubiertos(tmp_path):
    _escribir(tmp_path, {
        "context_map/domain/salud/doctor.py": "x = 1\n",
        "context_map/__tests__/test_salud.py": "import context_map.domain.salud.doctor\n",
    })
    estado, mensaje = _estado(calidad.check_modulos_con_test, tmp_path)
    assert estado == "OK"
    assert "1 submódulos" in mensaje


def test_submodulo_sin_test_avisa(tmp_path):
    _escribir(tmp_path, {
        "context_map/domain/salud/doctor.py": "x = 1\n",
        "context_map/domain/reportes/reporter.py": "x = 1\n",
        "context_map/__tests__/test_salud.py": "import context_map.domain.salud\n",
    })
    estado, mensaje = _estado(calidad.check_modulos_con_test, tmp_path)
    assert estado == "WARN"
    assert "reportes" in mensaje
    assert "REG-ARQ-004" in mensaje


# ── DOC-002 docstrings y tipos ────────────────────────────────────────────

def test_docstrings_y_tipos_en_verde(tmp_path):
    _escribir(tmp_path, {
        "context_map/core/base.py": (
            '"""Base."""\n\n'
            "def suma(a: int, b: int) -> int:\n"
            '    """Suma."""\n'
            "    return a + b\n"
        ),
    })
    estado, mensaje = _estado(calidad.check_docstrings_y_tipos, tmp_path)
    assert estado == "OK"
    assert "0%" in mensaje


def test_modulo_sin_docstring_avisa(tmp_path):
    _escribir(tmp_path, {
        "context_map/core/base.py": "def suma(a: int) -> int:\n    return a\n",
    })
    estado, mensaje = _estado(calidad.check_docstrings_y_tipos, tmp_path)
    assert estado == "WARN"
    assert "sin docstring" in mensaje
    assert "REG-DOC-002" in mensaje


def test_los_tests_no_necesitan_docstring_de_modulo(tmp_path):
    _escribir(tmp_path, {
        "context_map/__tests__/test_x.py": "def test_x() -> None:\n    pass\n",
    })
    estado, _ = _estado(calidad.check_docstrings_y_tipos, tmp_path)
    assert estado == "OK"


def test_suelo_de_anotaciones(tmp_path, monkeypatch):
    monkeypatch.setattr(calidad, "TOPE_SIN_TIPOS", 0.10)
    _escribir(tmp_path, {
        "context_map/core/base.py": (
            '"""Base."""\n\n'
            "def a(x: int) -> int:\n    return x\n\n"
            "def b(x):\n    return x\n"
        ),
    })
    estado, mensaje = _estado(calidad.check_docstrings_y_tipos, tmp_path)
    assert estado == "WARN"
    assert "suelo es 10%" in mensaje


# ── DOC-001 idioma ────────────────────────────────────────────────────────

def _parrafo(palabras: int, ingles: bool) -> str:
    base = "the and should which with the from the you can this is there is make sure "
    texto = (base * (palabras // 12 + 1)) if ingles else ("regla " * palabras)
    return "# Título\n\n" + texto


def test_documentacion_en_espanol_en_verde(tmp_path):
    _escribir(tmp_path, {"AGENTS.md": _parrafo(400, ingles=False)})
    estado, mensaje = _estado(calidad.check_idioma_de_la_documentacion, tmp_path)
    assert estado == "OK"
    assert "en español técnico" in mensaje


def test_documento_en_ingles_avisa(tmp_path):
    _escribir(tmp_path, {"guia.md": _parrafo(400, ingles=True)})
    estado, mensaje = _estado(calidad.check_idioma_de_la_documentacion, tmp_path)
    assert estado == "WARN"
    assert "guia.md" in mensaje
    assert "REG-DOC-001" in mensaje


def test_las_traducciones_declaradas_no_se_juzgan(tmp_path):
    _escribir(tmp_path, {"README_EN.md": _parrafo(400, ingles=True)})
    estado, _ = _estado(calidad.check_idioma_de_la_documentacion, tmp_path)
    assert estado == "OK"


def test_los_documentos_cortos_no_se_juzgan(tmp_path):
    _escribir(tmp_path, {"nota.md": "# Hola\n\nShort.\n"})
    estado, _ = _estado(calidad.check_idioma_de_la_documentacion, tmp_path)
    assert estado == "OK"


def test_un_entorno_con_nombre_raro_no_se_escanea(tmp_path):
    """`.venv_drive_slow` es un entorno: su LICENSE.md de numpy no es nuestro documento."""
    _escribir(tmp_path, {
        "AGENTS.md": _parrafo(400, ingles=False),
        ".venv_drive_slow/Lib/site-packages/numpy/LICENSE.md": _parrafo(400, ingles=True),
        "venv-local/lib/paquete/LEEME.md": _parrafo(400, ingles=True),
        "paquete.egg-info/LEEME.md": _parrafo(400, ingles=True),
    })
    estado, mensaje = _estado(calidad.check_idioma_de_la_documentacion, tmp_path)
    assert estado == "OK"
    assert "1 documento(s)" in mensaje

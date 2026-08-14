"""Métrica de memoria viva (R7) y consistencia del nombre (R8).

Auditoría 2026-08-14:
- R7: ``check`` debe reportar qué % de sesiones recientes de Hermes generaron
  eventos (memoria viva registrada), para medir cuánto contexto se pierde.
- R8: ``check`` debe avisar cuando el nombre del vault (vault-<X>) no coincide
  con el ``project`` del CONTEXT.md ni con el nombre del repo — eso duplica
  eventos en la BD personal.
"""

from __future__ import annotations

import json

from context_map.domain.analysis.checker import (
    _cobertura_memoria_viva,
    _inconsistencia_nombre,
)


def _proyecto(tmp_path, vault: str = "MiProyecto", project: str = "MiProyecto") -> str:
    """Crea un proyecto con vault y CONTEXT.md (frontmatter project).

    Args:
        tmp_path: Fixture de pytest.
        vault (str): Nombre de la carpeta vault-<X>.
        project (str): Valor de ``project`` en el frontmatter del CONTEXT.md.

    Returns:
        str: Ruta del proyecto.
    """
    ctx = tmp_path / ".context-map"
    (ctx / f"vault-{vault}" / "7.0-MANUAL" / "Diario").mkdir(parents=True)
    (ctx / "state").mkdir()
    (ctx / "raw").mkdir()
    (ctx / "CONTEXT.md").write_text(
        f"---\nproject: \"{project}\"\n---\n# Brief\n", encoding="utf-8",
    )
    return str(tmp_path)


def test_cobertura_memoria_viva_porcentaje(tmp_path, monkeypatch):
    """1 evento registrado y 4 sesiones sin importar → 20% de cobertura."""
    ruta = _proyecto(tmp_path)
    raw = tmp_path / ".context-map" / "raw"
    with open(raw / "events.jsonl", "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "IDEA", "text": "decisión A"}) + "\n")

    def _fake_sesiones(_ruta):  # noqa: ANN001
        return 4

    monkeypatch.setattr(
        "context_map.domain.analysis.checker._sesiones_posteriores", _fake_sesiones,
    )
    cov = _cobertura_memoria_viva(ruta)
    assert cov["eventos"] == 1
    assert cov["sesiones"] == 4
    assert cov["porcentaje"] == 20


def test_cobertura_sin_eventos_es_cero(tmp_path):
    """Sin events.jsonl la cobertura es 0% y no rompe."""
    ruta = _proyecto(tmp_path)
    cov = _cobertura_memoria_viva(ruta)
    assert cov["eventos"] == 0
    assert cov["porcentaje"] == 0


def test_nombre_consistente_no_avisa(tmp_path):
    """vault, project y carpeta coinciden → sin aviso."""
    repo = tmp_path / "MiProyecto"
    repo.mkdir()
    ruta = _proyecto(repo, vault="MiProyecto", project="MiProyecto")
    (repo / "README.md").write_text("# ok", encoding="utf-8")
    assert _inconsistencia_nombre(ruta, "MiProyecto") == ""


def test_nombre_inconsistente_avisa(tmp_path):
    """vault-reporte_mensuales + project 'reporte_mensuales' + repo '00_GOBERNANZA_IA' → aviso."""
    repo = tmp_path / "00_GOBERNANZA_IA"
    repo.mkdir()
    ruta = _proyecto(repo, vault="reporte_mensuales", project="reporte_mensuales")
    (repo / "README.md").write_text("# ok", encoding="utf-8")
    aviso = _inconsistencia_nombre(ruta, "00_GOBERNANZA_IA")
    assert aviso
    assert "reporte_mensuales" in aviso
    assert "00_GOBERNANZA_IA" in aviso

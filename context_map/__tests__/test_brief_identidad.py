"""Regresión P0: identidad del brief (`CONTEXT.md`) y no-contaminación entre proyectos.

Bug original: ``exportar_contexto`` invocaba ``generar_brief`` sin ``output_path``,
por lo que el default ``.context-map/CONTEXT.md`` (relativo al CWD) sobrescribía
el brief del proyecto REAL con el de un proyecto temporal. Los tests de
``test_export`` corrompían así `.context-map/CONTEXT.md` del repo al correr la
suite.

Estos tests garantizan:
1. ``exportar_contexto`` escribe el brief DENTRO del proyecto exportado y nunca
   en el CWD.
2. ``check`` (vía ``_inconsistencia_nombre``) detecta un brief "extranjero"
   comparando el H1 con el vault/repo.
"""

from __future__ import annotations

from pathlib import Path

from context_map.application.commands.export import exportar_contexto
from context_map.domain.analysis.checker import _inconsistencia_nombre


def _proyecto(tmp_path: Path, h1: str = "MiProyecto") -> Path:
    """Crea un proyecto mínimo con brief cuyo H1 es ``h1``."""
    ctx = tmp_path / ".context-map"
    (ctx / "vault-MiProyecto").mkdir(parents=True)
    (ctx / "state").mkdir(parents=True)
    (ctx / "CONTEXT.md").write_text(
        f"# {h1} — Brief para Agentes\n\nContenido.\n", encoding="utf-8",
    )
    return tmp_path


def test_export_no_sobrescribe_el_brief_del_cwd(tmp_path: Path, monkeypatch) -> None:
    """Exportar otro proyecto NO debe tocar el CONTEXT.md del directorio actual."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    brief_cwd = cwd / ".context-map" / "CONTEXT.md"
    brief_cwd.parent.mkdir(parents=True)
    sentinela = "# ProyectoReal — Brief para Agentes\n"
    brief_cwd.write_text(sentinela, encoding="utf-8")
    monkeypatch.chdir(cwd)

    origen = tmp_path / "ProyectoTemporal"
    origen.mkdir()
    salida = tmp_path / "export.xml"

    exportar_contexto(project_path=origen, format_type="xml", output_file=salida)

    # El brief del CWD quedó intacto...
    assert brief_cwd.read_text(encoding="utf-8") == sentinela
    # ...y el brief se generó dentro del proyecto exportado.
    generado = origen / ".context-map" / "CONTEXT.md"
    assert generado.exists()
    assert "# ProyectoTemporal — Brief para Agentes" in generado.read_text(encoding="utf-8")


def test_check_detecta_brief_extranjero(tmp_path: Path) -> None:
    """Un brief con H1 de otro proyecto dispara el aviso de fragmentación."""
    repo = tmp_path / "MiProyecto"
    repo.mkdir()
    ruta = _proyecto(repo, h1="test_exportar_contexto_xml_inc0")
    (repo / "README.md").write_text("# ok", encoding="utf-8")

    aviso = _inconsistencia_nombre(str(ruta), "MiProyecto")

    assert aviso
    assert "test_exportar_contexto_xml_inc0" in aviso
    assert "brief" in aviso


def test_brief_coherente_no_dispara_aviso(tmp_path: Path) -> None:
    """H1, vault y repo coincidentes → sin aviso (no falsos positivos)."""
    repo = tmp_path / "MiProyecto"
    repo.mkdir()
    ruta = _proyecto(repo, h1="MiProyecto")
    (repo / "README.md").write_text("# ok", encoding="utf-8")

    assert _inconsistencia_nombre(str(ruta), "MiProyecto") == ""

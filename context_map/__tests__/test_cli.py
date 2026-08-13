"""Pruebas unitarias para el parser principal del CLI y despacho de comandos."""

from __future__ import annotations

import argparse

from context_map.application.cli.parser import create_parser


def test_cli_parser_defaults() -> None:
    """Verifica que el parser principal cree los subcomandos esperados."""
    parser = create_parser()
    assert isinstance(parser, argparse.ArgumentParser)

    # Test parser para comando 'check'
    args = parser.parse_args(["check", "."])
    assert args.cmd == "check"
    assert args.target == "."

    # Test parser para comando 'build'
    args_build = parser.parse_args(["build", "--clean", "--brief"])
    assert args_build.cmd == "build"
    assert args_build.clean is True
    assert args_build.brief is True

    # Test parser para comando 'scan'
    args_scan = parser.parse_args(["scan", "."])
    assert args_scan.cmd == "scan"
    assert args_scan.target == "."


def test_cli_parser_auto_mode() -> None:
    """Verifica los flags por defecto del comando auto."""
    parser = create_parser()
    args_auto = parser.parse_args(["auto", ".", "--project", "TestApp"])
    assert args_auto.cmd == "auto"
    assert args_auto.target == "."
    assert args_auto.project == "TestApp"


def test_aviso_pre_actualizacion_contiene_comando(monkeypatch) -> None:
    """El aviso pre-refresh informa de la versión nueva y el comando de actualización."""
    import context_map.infrastructure.version_check as vc
    from context_map.infrastructure.version_check import aviso_pre_actualizacion

    monkeypatch.setattr(vc, "hay_actualizacion", lambda force=False: (True, "1.4.0", "1.5.0"))
    msg = aviso_pre_actualizacion()
    assert "DESACTUALIZADO" in msg
    assert "1.5.0" in msg
    assert "uv tool install" in msg
    assert "--with" in msg  # incluye el SDK de MCP

    monkeypatch.setattr(vc, "hay_actualizacion", lambda force=False: (False, "1.5.0", "1.5.0"))
    assert aviso_pre_actualizacion() == ""


def test_refresh_imprime_aviso_pre_actualizacion(monkeypatch, capsys) -> None:
    """El refresh verifica la versión del PROGRAMA antes de actualizar el CONTEXTO."""
    import context_map.infrastructure.version_check as vc
    from context_map.application.commands import refresh as refresh_mod
    from context_map.application.commands.refresh import cmd_refresh

    # No ejecutar scan/build/check reales en el test
    monkeypatch.setattr(refresh_mod, "cmd_scan", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_build", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_check", lambda args: None)
    # Hay una actualización pendiente → debe avisarse al inicio
    monkeypatch.setattr(vc, "hay_actualizacion", lambda force=False: (True, "1.4.0", "1.5.0"))

    args = argparse.Namespace(target=".", project="Demo", quiet=False, mode="hierarchical")
    cmd_refresh(args)
    out = capsys.readouterr().out

    assert "DESACTUALIZADO" in out, "El refresh no avisó de la actualización pendiente"
    assert "1.5.0" in out
    # El aviso aparece ANTES del resultado del refresh
    assert out.index("DESACTUALIZADO") < out.index("[refresh] [OK]")


def test_refresh_importa_sesiones_automatico(monkeypatch, capsys) -> None:
    """El refresh importa las sesiones recientes de Hermes (memoria viva automática)."""
    import argparse

    from context_map.application.commands import refresh as refresh_mod
    from context_map.application.commands.refresh import cmd_refresh

    monkeypatch.setattr(refresh_mod, "cmd_scan", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_build", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_check", lambda args: None)

    llamado: dict = {}

    def _fake_importar_sesiones(**kwargs):
        llamado.update(kwargs)
        return 3

    monkeypatch.setattr(
        "context_map.infrastructure.integrations.hermes.importar_sesiones",
        _fake_importar_sesiones,
    )

    args = argparse.Namespace(target=".", project="Demo", quiet=False, mode="hierarchical")
    cmd_refresh(args)
    out = capsys.readouterr().out

    # Se importan las 5 sesiones más recientes y los eventos van al raw del proyecto
    assert llamado.get("limite") == 5
    assert "events.jsonl" in llamado.get("output_path", "")
    assert "3 evento(s) de sesiones importados" in out


def test_refresh_importar_sesiones_tolerante(monkeypatch, capsys) -> None:
    """Si la BD de sesiones no existe, el refresh NO se rompe (aviso y sigue)."""
    import argparse

    from context_map.application.commands import refresh as refresh_mod
    from context_map.application.commands.refresh import cmd_refresh

    monkeypatch.setattr(refresh_mod, "cmd_scan", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_build", lambda args: None)
    monkeypatch.setattr(refresh_mod, "cmd_check", lambda args: None)

    def _fake_importar_sesiones(**kwargs):
        raise FileNotFoundError("sin BD de sesiones")

    monkeypatch.setattr(
        "context_map.infrastructure.integrations.hermes.importar_sesiones",
        _fake_importar_sesiones,
    )

    args = argparse.Namespace(target=".", project="Demo", quiet=False, mode="hierarchical")
    cmd_refresh(args)  # no debe lanzar excepción
    out = capsys.readouterr().out
    assert "[refresh] [OK]" in out, "El refresh se rompió por la importación de sesiones"

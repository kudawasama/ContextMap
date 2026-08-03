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

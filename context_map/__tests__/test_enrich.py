"""Pruebas unitarias para el comando ctxmap enrich y su persistencia en disco."""

import argparse
import ast
import tempfile
from pathlib import Path

import pytest

from context_map.application.commands.enrich import _formatear_docstring, cmd_enrich


def test_formatear_docstring_simple() -> None:
    """Verifica el formateo de un docstring simple de una sola línea."""
    res = _formatear_docstring("Calcula el total de la orden.", "    ")
    assert len(res) == 1
    assert res[0] == '    """Calcula el total de la orden."""'


def test_formatear_docstring_multilinea() -> None:
    """Verifica el formateo de un docstring con múltiples líneas e indentación."""
    doc = """Calcula el total.

Args:
    subtotal: Monto base.
"""
    res = _formatear_docstring(doc, "    ")
    assert res[0] == '    """Calcula el total.'
    assert "    Args:" in res
    assert "        subtotal: Monto base." in res
    assert res[-1] == '    """'


def test_cmd_enrich_persiste_cambios_en_disco() -> None:
    """Verifica que cmd_enrich escriba efectivamente el docstring generado en el archivo."""
    codigo_original = "def sumar(a: int, b: int) -> int:\n    return a + b\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "matematica.py"
        test_file.write_text(codigo_original, encoding="utf-8")

        args = argparse.Namespace(path=str(test_file), model=None, dry_run=False, confirmar=True)
        ret = cmd_enrich(args)
        assert ret == 0

        contenido_nuevo = test_file.read_text(encoding="utf-8")
        assert contenido_nuevo != codigo_original

        # Validar que sea sintácticamente válido
        tree = ast.parse(contenido_nuevo)
        fn = tree.body[0]
        assert isinstance(fn, ast.FunctionDef)
        assert ast.get_docstring(fn) is not None
        assert "sumar" in ast.get_docstring(fn).lower() or len(ast.get_docstring(fn)) > 0


def test_cmd_enrich_dry_run_no_modifica_disco() -> None:
    """Verifica que en modo --dry-run el archivo en disco permanezca intacto."""
    codigo_original = "def restar(a: int, b: int) -> int:\n    return a - b\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "calculo.py"
        test_file.write_text(codigo_original, encoding="utf-8")

        args = argparse.Namespace(path=str(test_file), model=None, dry_run=True)
        ret = cmd_enrich(args)
        assert ret == 0

        contenido_despues = test_file.read_text(encoding="utf-8")
        assert contenido_despues == codigo_original


def test_enrich_sin_confirmar_no_toca_el_archivo() -> None:
    """REG-LIM-004: sin `--confirmar` la tarea cara se detiene y no escribe nada."""
    codigo_original = "def dividir(a: int, b: int) -> float:\n    return a / b\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "aritmetica.py"
        test_file.write_text(codigo_original, encoding="utf-8")

        args = argparse.Namespace(path=str(test_file), model=None, dry_run=False)
        with pytest.raises(SystemExit) as salida:
            cmd_enrich(args)

        assert salida.value.code == 2
        assert test_file.read_text(encoding="utf-8") == codigo_original


def test_enrich_en_vista_previa_no_pide_permiso() -> None:
    """La vista previa no gasta ni escribe: no hay permiso que exigir."""
    codigo_original = "def multiplicar(a: int, b: int) -> int:\n    return a * b\n"

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "producto.py"
        test_file.write_text(codigo_original, encoding="utf-8")

        args = argparse.Namespace(path=str(test_file), model=None, dry_run=True)
        assert cmd_enrich(args) == 0
        assert test_file.read_text(encoding="utf-8") == codigo_original

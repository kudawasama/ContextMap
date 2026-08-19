"""Tests para el módulo de auditoría AST local (ast_audit.py)."""

from __future__ import annotations

from context_map.domain.analyzers.ast_audit import auditar_archivo_python, auditar_proyecto_python


def test_auditar_archivo_python_detecta_eval_y_pass(tmp_path):
    """Verifica la detección de eval() y except pass."""
    code_file = tmp_path / "vulnerable.py"
    code_file.write_text(
        "def test():\n"
        "    eval('1 + 1')\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n",
        encoding="utf-8",
    )

    alertas = auditar_archivo_python(str(code_file))
    assert len(alertas) >= 2
    categorias = [a.categoria for a in alertas]
    assert "SEGURIDAD" in categorias
    assert "ROBUSTEZ" in categorias


def test_auditar_proyecto_python(tmp_path):
    """Verifica que el escáner de proyecto audite archivos .py recursivamente."""
    sub_dir = tmp_path / "core"
    sub_dir.mkdir()
    f1 = sub_dir / "db.py"
    f1.write_text("password = 'super_secret_12345'", encoding="utf-8")

    alertas = auditar_proyecto_python(str(tmp_path))
    assert len(alertas) == 1
    assert alertas[0].categoria == "SEGURIDAD"
    assert "password" in alertas[0].mensaje

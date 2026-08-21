"""Tests de seguridad del servidor MCP: confirmación destructiva y validación de rutas."""

from __future__ import annotations

from context_map.infrastructure import mcp_server


def test_mcp_build_clean_sin_confirmacion_es_rechazado():
    """Verifica que build(clean=True) exige confirm=True."""
    res = mcp_server.build(target=".", clean=True)
    assert "rechazada por seguridad" in res
    assert "confirm=True" in res


def test_mcp_doctor_fix_sin_confirmacion_es_rechazado():
    """Verifica que doctor(fix=True) exige confirm=True."""
    res = mcp_server.doctor(target=".", fix=True)
    assert "rechazada por seguridad" in res


def test_mcp_install_hooks_sin_confirmacion_es_rechazado():
    """Verifica que install_hooks exige confirm=True."""
    res = mcp_server.install_hooks(target=".", force=True)
    assert "rechazada por seguridad" in res


def test_mcp_target_invalido_devuelve_error():
    """Verifica que un target inexistente no se procesa."""
    res = mcp_server.check(target="/ruta/inexistente/xyz-123")
    assert "ERROR" in res
    assert "no es un directorio" in res

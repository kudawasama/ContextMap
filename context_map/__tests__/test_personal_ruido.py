"""Tests del predicado de ruido compartido por la ingesta y la purga."""

from __future__ import annotations

from context_map.core.personal.ruido import es_evento_ruido


def test_texto_normal_no_es_ruido() -> None:
    """Contenido real (incluido un TODO con marcador) no se descarta."""
    assert es_evento_ruido("IDEA", "Idea real y legítima", "chat:1.md") is False
    assert es_evento_ruido("RIESGO", "Alta complejidad en standardize.py", "scan") is False
    assert es_evento_ruido(
        "FUTURO", "TODO (app.py:L20): # TODO: refactorizar base", "scan"
    ) is False


def test_patrones_tecnicos_son_ruido() -> None:
    """Vacío, ``[``, archivos de sistema y cachés de despliegue son ruido."""
    assert es_evento_ruido("IDEA", "", "chat") is True
    assert es_evento_ruido("IDEA", "[", "chat") is True
    assert es_evento_ruido("IDEA", "algo", "chat:desktop.ini") is True
    assert es_evento_ruido("IDEA", "algo", "chat:Thumbs.db") is True
    assert es_evento_ruido("RIESGO", "Alta complejidad: .vercel/cache/x.py", "scan") is True
    assert es_evento_ruido("RIESGO", "cache en .next/server", "scan") is True
    assert es_evento_ruido("RIESGO", "paquete archive-v0/x.py", "scan") is True


def test_todos_falsos_positivos_son_ruido() -> None:
    """FUTURO con ``TODO (...)`` sin marcador real (docstring/logger) es ruido."""
    assert (
        es_evento_ruido(
            "FUTURO",
            'TODO (app/models.py:L31): """Campos editables (todos opcionales)."""',
            "scan",
        )
        is True
    )
    assert (
        es_evento_ruido(
            "FUTURO", 'TODO (helpers.py:L322): logger.debug("No se pudo guardar")', "scan"
        )
        is True
    )

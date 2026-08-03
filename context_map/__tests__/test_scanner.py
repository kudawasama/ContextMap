"""Pruebas unitarias para el escáner y la sincronización de riesgos/todos."""

from __future__ import annotations

import os
from context_map.core.models import Event, Node
from context_map.domain.scanning.scanner import _events_desde_contenido
from context_map.domain.synchronization.sync import _depurar_nodos_obsoletos
from context_map.infrastructure.analyzers.content import InfoContenido


def test_events_desde_contenido_riesgo_estable() -> None:
    """Verifica que los títulos de eventos RIESGO no contengan métricas dinámicas de líneas."""
    info1 = InfoContenido(
        ruta="/tmp/test_project/core/modulo_largo.py",
        complejidad="alta",
        lineas_codigo=500,
    )
    eventos = _events_desde_contenido([info1], ruta_raiz="/tmp/test_project")

    assert len(eventos) == 1
    ev = eventos[0]
    assert ev.type == "RIESGO"
    assert "500 líneas" not in ev.text
    assert "core/modulo_largo.py" in ev.text


def test_events_desde_contenido_todos_con_ubicacion() -> None:
    """Verifica que los eventos FUTURO incluyan la ruta relativa y número de línea."""
    info = InfoContenido(
        ruta="/tmp/test_project/app/cli.py",
        todos=["L42: # TODO: Refactorizar parser principal"],
    )
    eventos = _events_desde_contenido([info], ruta_raiz="/tmp/test_project")

    assert len(eventos) == 1
    ev = eventos[0]
    assert ev.type == "FUTURO"
    assert "app/cli.py:L42" in ev.text
    assert "Refactorizar parser principal" in ev.text


def test_depurar_nodos_obsoletos() -> None:
    """Verifica que _depurar_nodos_obsoletos elimine nodos RIESGO inexistentes o volátiles."""
    nodo_viejo_lineas = Node(
        id="RIESGO-01",
        type="RIESGO",
        title="Archivo complejo: writer.py (2448 líneas)",
        summary="Archivo volátil antiguo",
        source="scanner",
    )
    nodo_archivo_borrado = Node(
        id="RIESGO-02",
        type="RIESGO",
        title="Archivo complejo: archivo_inexistente_123.py",
        summary="Este archivo no existe",
        source="scanner",
    )
    nodo_valido = Node(
        id="BASE-01",
        type="BASE",
        title="Proyecto ContextMap",
        summary="Nodo base válido",
    )

    limpios = _depurar_nodos_obsoletos([nodo_viejo_lineas, nodo_archivo_borrado, nodo_valido])

    assert len(limpios) == 1
    assert limpios[0].id == "BASE-01"

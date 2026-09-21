"""Pruebas de la extracción de marcadores TODO/FIXME/HACK de comentarios.

Caso real de la auditoría 2026-09-21: la heurística buscaba la subcadena
``todo``/``bug`` en cualquier línea, así que 647 de los 685 eventos ``TODO``
de la BD personal eran prosa en español («todo el rango», «todos los módulos»),
llamadas ``logger.debug`` o líneas de docstring.
"""

from __future__ import annotations

from context_map.infrastructure.analyzers.content import extraer_todos

CODIGO_CON_FALSOS_POSITIVOS = '''"""Carpetas base que se escanean en ``sync --todos``."""

import logging

logger = logging.getLogger(__name__)


def cargar():
    """Carga y re-estandariza todo el grafo (por si quedaron viejos)."""
    for item in todos_los_items:
        # Cubre todo el rango y todo dia del periodo
        logger.debug("Encoding detection on empty bytes, %s", item)
        # Avoid unoptimized RSS usage.
        yield item
'''

CODIGO_CON_MARCADORES_REALES = """# TODO: unificar el descubrimiento de proyectos
import os  # FIXME: ruta hardcodeada a F:
# HACK: parche temporal hasta migrar la BD
# XXX revisar antes del release
valor = 1  # TODO(c) pendiente de tipar
"""


def test_no_marca_prosa_en_espanol_ni_debug_ni_docstrings(tmp_path) -> None:
    """La prosa con «todo», `logger.debug` y los docstrings NO son pendientes."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text(CODIGO_CON_FALSOS_POSITIVOS, encoding="utf-8")

    assert extraer_todos(str(archivo)) == []


def test_detecta_marcadores_reales_en_comentarios(tmp_path) -> None:
    """Los marcadores en MAYÚSCULAS dentro de comentarios sí se detectan."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text(CODIGO_CON_MARCADORES_REALES, encoding="utf-8")

    todos = extraer_todos(str(archivo))

    assert len(todos) == 5, todos
    assert todos[0].startswith("L1: # TODO: unificar")
    assert any("FIXME" in t for t in todos)
    assert any("HACK" in t for t in todos)
    assert any("XXX" in t for t in todos)


def test_todo_minuscula_no_es_marcador(tmp_path) -> None:
    """`# todo` en un comentario en español es prosa, no un marcador."""
    archivo = tmp_path / "modulo.py"
    archivo.write_text("# todo esto hay que revisarlo luego\n", encoding="utf-8")

    assert extraer_todos(str(archivo)) == []


def test_archivo_inexistente_no_falla() -> None:
    """Un archivo ilegible devuelve una lista vacía, sin propagar la excepción."""
    assert extraer_todos("ruta/que/no/existe.py") == []

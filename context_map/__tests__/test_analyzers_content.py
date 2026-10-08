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


CODIGO_CON_NEGRITA_MARKDOWN = '''"""Docstring que explica el filtro: los **TODO** crudos del código se excluyen."""



def f():
    """Ojo con **TODO** en negrita y con *TODO suelto en prosa."""
    return 1
'''


CODIGO_CON_COMENTARIOS_DE_BLOQUE = '''/* TODO: refactorizar el parser */
 * FIXME: ojo con el encoding
/** HACK: puente temporal */
<!-- TODO: documentar la API -->
'''


def test_negrita_markdown_no_es_marcador(tmp_path) -> None:
    """Regresión 2026-10-08: ``**TODO**`` (negrita Markdown) no es un comentario.

    Dogfooding: al documentar el filtro del diario, el propio docstring generó un
    nodo ``TODO (…/canvas.py:L203)`` porque ``*`` contaba como signo de comentario.
    """
    archivo = tmp_path / "modulo.py"
    archivo.write_text(CODIGO_CON_NEGRITA_MARKDOWN, encoding="utf-8")

    assert extraer_todos(str(archivo)) == []


def test_marcadores_en_comentarios_de_bloque_siguen_detectandose(tmp_path) -> None:
    """``/* TODO */``, `` * TODO`` y ``<!-- TODO -->`` siguen siendo marcadores.

    Se prueba en un ``.ts``: los comentarios de bloque no existen en Python, así
    que ahí manda la heurística por líneas (no ``tokenize``).
    """
    archivo = tmp_path / "modulo.ts"
    archivo.write_text(CODIGO_CON_COMENTARIOS_DE_BLOQUE, encoding="utf-8")

    todos = extraer_todos(str(archivo))

    assert len(todos) == 4, todos
    assert any("refactorizar el parser" in t for t in todos)
    assert any("encoding" in t for t in todos)
    assert any("puente temporal" in t for t in todos)
    assert any("documentar la API" in t for t in todos)


def test_python_solo_mira_comentarios_reales(tmp_path) -> None:
    """En ``.py`` un marcador dentro de un string o docstring NO cuenta.

    Regresión 2026-10-08: documentar el filtro generó nodos TODO fantasma porque
    se miraban líneas sueltas. Con ``tokenize`` solo cuentan los comentarios.
    """
    archivo = tmp_path / "doc.py"
    archivo.write_text(
        '"""Docstring que cita el marcador # TODO: no es un pendiente."""\n'
        '\n'
        'MENSAJE = "# FIXME: tampoco, es un string"\n'
        'RE = r"# TODO"\n'
        '\n'
        'x = 1  # TODO: este sí es un pendiente real\n',
        encoding="utf-8",
    )

    todos = extraer_todos(str(archivo))

    assert len(todos) == 1, todos
    assert "pendiente real" in todos[0]


def test_javascript_usa_la_heuristica_por_lineas(tmp_path) -> None:
    """En lenguajes sin ``tokenize`` se mantiene la heurística por líneas."""
    archivo = tmp_path / "app.ts"
    archivo.write_text(
        '// TODO: tipar el retorno\n'
        'const x = 1;\n',
        encoding="utf-8",
    )

    todos = extraer_todos(str(archivo))

    assert len(todos) == 1, todos
    assert "tipar el retorno" in todos[0]

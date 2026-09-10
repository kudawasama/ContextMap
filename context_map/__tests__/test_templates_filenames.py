"""Tests de los sanitizadores de nombre de archivo/slug (fix separadores de ruta).

Antes del fix, ``_safe_filename`` y ``_slugificar`` eliminaban ``/`` y ``\\``
sin reemplazo, concatenando las palabras de un título que embebía una ruta
(p. ej. las notas de riesgo "Archivos de alta complejidad:
carpeta/archivo.py" generaban el archivo/wikilink
"carpetaarchivo.py", ilegible).
"""

from __future__ import annotations

from context_map.presentation.vault.templates import _safe_filename, _slugificar


def test_safe_filename_preserva_separacion_de_ruta() -> None:
    """Una ruta embebida en el título no debe concatenar sus componentes."""
    resultado = _safe_filename("Archivos de alta complejidad: carpeta/archivo.py")
    assert "carpeta_archivo.py" in resultado
    assert "carpetaarchivo.py" not in resultado


def test_safe_filename_reemplaza_backslash() -> None:
    """Rutas estilo Windows también deben separar sus componentes."""
    assert _safe_filename("carpeta\\archivo.py") == "carpeta_archivo.py"


def test_safe_filename_sin_rutas_no_cambia() -> None:
    """Un título sin separadores de ruta se comporta como antes."""
    assert _safe_filename("Nota simple sin rutas") == "Nota simple sin rutas"


def test_slugificar_preserva_separacion_de_ruta() -> None:
    """El slug de wikilink tampoco debe concatenar palabras de una ruta."""
    resultado = _slugificar("Archivos complejos: carpeta/archivo.py")
    assert "carpeta-archivo" in resultado
    assert "carpetaarchivo" not in resultado

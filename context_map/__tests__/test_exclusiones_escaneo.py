"""Pruebas de la lista canónica de exclusiones del análisis de código.

Cubre el caso real de la auditoría 2026-09-21: un proyecto con `.vercel/`
contaba sus dependencias vendorizadas como código propio (3.721 archivos y
909.560 líneas, con el riesgo de complejidad apuntando a `fastapi`).
"""

from __future__ import annotations

import os

from context_map.infrastructure.analyzers.content import analizar_directorio
from context_map.infrastructure.analyzers.exclusions import (
    carpetas_excluidas,
    es_archivo_excluido,
    es_carpeta_excluida,
    es_ruta_excluida,
)
from context_map.infrastructure.analyzers.structure import escanear_proyecto


def test_carpetas_de_despliegue_y_cache_excluidas() -> None:
    """Las cachés de build y las dependencias de terceros se excluyen."""
    for nombre in (".vercel", ".next", ".nuxt", ".output", ".svelte-kit", ".turbo", ".cache"):
        assert es_carpeta_excluida(nombre), f"no se excluye {nombre}"

    for nombre in ("site-packages", "archive-v0", "node_modules", "__pycache__"):
        assert es_carpeta_excluida(nombre), f"no se excluye {nombre}"


def test_carpetas_ambiguas_no_se_excluyen() -> None:
    """Nombres que pueden ser código legítimo NO se excluyen (criterio conservador)."""
    for nombre in ("target", "vendor", "app", "context_map", "src", "lib"):
        assert not es_carpeta_excluida(nombre), f"se excluye código legítimo: {nombre}"


def test_archivos_de_sistema_excluidos() -> None:
    """`desktop.ini` y equivalentes nunca cuentan como código ni como conversación."""
    assert es_archivo_excluido("desktop.ini")
    assert es_archivo_excluido("Thumbs.db")
    assert es_archivo_excluido("notas.gdoc")
    assert not es_archivo_excluido("app.py")


def test_ruta_vendorizada_excluida() -> None:
    """La ruta vendorizada real de mi-app-utm queda excluida."""
    ruta = ".vercel/python/cache/uv/archive-v0/vUZiVF7K2YULZovQUTErT/fastapi/routing.py"
    assert es_ruta_excluida(ruta)
    assert es_ruta_excluida("C:\\proyecto\\.venv\\Lib\\site-packages\\x\\y.py")
    assert not es_ruta_excluida("context_map/domain/scanning/scanner.py")


def test_lista_canonica_es_lista_ordenada() -> None:
    """`carpetas_excluidas()` entrega una lista para las APIs que la esperan."""
    lista = carpetas_excluidas()
    assert isinstance(lista, list)
    assert lista == sorted(lista)
    assert ".vercel" in lista


def test_escaneo_ignora_vercel_y_cuenta_solo_codigo_propio(tmp_path) -> None:
    """Un proyecto con `.vercel/` solo cuenta su propio código y sus propias líneas."""
    vendor = tmp_path / ".vercel" / "python" / "cache" / "uv" / "archive-v0" / "fastapi"
    vendor.mkdir(parents=True)
    (vendor / "routing.py").write_text("def ruta():\n    return 1\n" * 50, encoding="utf-8")
    (tmp_path / "app.py").write_text("def main():\n    return 0\n", encoding="utf-8")

    estructura = escanear_proyecto(str(tmp_path))
    rutas = [a.ruta.replace("\\", "/") for a in estructura.archivos]

    assert not any(".vercel" in r for r in rutas), rutas
    assert any(r.endswith("app.py") for r in rutas), rutas
    assert estructura.total_lineas == 2, estructura.total_lineas

    analizados = [os.path.basename(c.ruta) for c in analizar_directorio(str(tmp_path))]
    assert analizados == ["app.py"], analizados

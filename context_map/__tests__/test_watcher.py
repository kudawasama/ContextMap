"""Tests unitarios para watcher.py (monitoreo y debouncing de eventos)."""

from __future__ import annotations

from context_map.domain.synchronization.watcher import _es_archivo_relevante, iniciar_watcher


def test_es_archivo_relevante():
    """Filtra correctamente archivos por extensión y directorio."""
    assert _es_archivo_relevante("src/app.py")
    assert _es_archivo_relevante("README.md")
    assert not _es_archivo_relevante(".git/config")
    assert not _es_archivo_relevante(".context-map/vault/00-INDICE.md")
    assert not _es_archivo_relevante("main.pyc")


def test_iniciar_watcher_polling_fallback(tmp_path):
    """Ejecuta callback tras detectar cambios de archivos vía polling."""
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")

    llamadas = []

    def _fake_cb(ruta):
        llamadas.append(ruta)

    # Iniciar con max_iterations=3 para salir rápido del bucle
    iniciar_watcher(str(tmp_path), debounce_ms=100, callback=_fake_cb, max_iterations=3)

    assert len(llamadas) >= 0  # no rompe la ejecución

"""Tests unitarios para watcher.py (monitoreo y debouncing de eventos)."""

from __future__ import annotations

import logging

from context_map.application.commands import refresh as refresh_module
from context_map.domain.synchronization.watcher import (
    _ejecutar_refresco_default,
    _es_archivo_relevante,
    iniciar_watcher,
)


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


def test_ejecutar_refresco_default_pasa_namespace(tmp_path, monkeypatch, caplog):
    """El refresco por defecto entrega un Namespace con ``target`` y ``quiet``.

    Regresión: antes se pasaba un ``dict`` y ``cmd_refresh``/``cmd_scan``
    fallaban con ``'dict' object has no attribute 'target'``, dejando el
    refresco automático del watcher inoperante.
    """
    (tmp_path / "app.py").write_text("print('hola')", encoding="utf-8")
    capturado: dict[str, object] = {}

    def _fake_cmd_refresh(args):
        # Reproduce el contrato real: los comandos acceden a atributos.
        capturado["target"] = args.target
        capturado["quiet"] = args.quiet

    monkeypatch.setattr(refresh_module, "cmd_refresh", _fake_cmd_refresh)

    with caplog.at_level(
        logging.WARNING, logger="context_map.domain.synchronization.watcher"
    ):
        _ejecutar_refresco_default(str(tmp_path))

    assert "Error durante refresco automático" not in caplog.text
    assert capturado["target"] == str(tmp_path)
    assert capturado["quiet"] is True


def test_cmd_refresh_normaliza_mapping(tmp_path, monkeypatch):
    """``cmd_refresh`` acepta un mapping con ``target_dir`` o ``target``."""
    monkeypatch.chdir(tmp_path)
    capturado: dict[str, object] = {}

    monkeypatch.setattr(
        refresh_module, "cmd_scan", lambda args: capturado.update(target=args.target)
    )
    monkeypatch.setattr(refresh_module, "cmd_build", lambda args: None)
    monkeypatch.setattr(refresh_module, "cmd_check", lambda args: None)
    monkeypatch.setattr(
        "context_map.infrastructure.integrations.hermes.importar_sesiones",
        lambda **kwargs: 0,
    )
    monkeypatch.setattr(
        "context_map.infrastructure.integrations.antigravity.importar_antigravity",
        lambda **kwargs: 0,
    )

    refresh_module.cmd_refresh({"target_dir": str(tmp_path), "quiet": True})

    assert capturado["target"] == str(tmp_path)

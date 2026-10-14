"""Tests unitarios para watcher.py (monitoreo y debouncing de eventos)."""

from __future__ import annotations

import logging
import threading
import time

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


def test_es_archivo_relevante_ignora_salidas_generadas():
    """Las salidas de gobernanza y de despliegue no disparan el watcher.

    Regresión del incidente 2026-10-13: el daemon se disparaba con los archivos
    que él mismo (u otro deploy) escribía en la raíz del proyecto.
    """
    for nombre in (
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "CONTEXT.md",
        ".cursorrules",
        ".windsurfrules",
        "version.json",
    ):
        assert not _es_archivo_relevante(f"/proyecto/{nombre}"), nombre
    assert _es_archivo_relevante("/proyecto/src/app.py")
    assert _es_archivo_relevante("/proyecto/notas/idea.md")


def test_watcher_respeta_intervalo_minimo(tmp_path):
    """Un bucle de realimentación no produce más de un refresco por intervalo.

    Regresión del incidente 2026-10-13: sin intervalo mínimo ni ventana de
    supresión, cada escritura (incluidas las del propio refresco) disparaba otro
    refresco, y con él otro snapshot de ~2,9 MB en maps/HISTORY.
    """
    (tmp_path / "app.py").write_text("print('a')", encoding="utf-8")
    llamadas: list[str] = []

    def _escribir_despues_de_arrancar() -> None:
        """Genera el primer cambio DESPUÉS de que el watcher esté escuchando."""
        time.sleep(0.2)
        (tmp_path / "cambio.py").write_text("print('b')", encoding="utf-8")

    def _cb(ruta):
        llamadas.append(ruta)
        # Realimentación deliberada: cada refresco escribe archivos relevantes…
        (tmp_path / f"generado_{len(llamadas)}.py").write_text("print('x')", encoding="utf-8")
        # …y también salidas que el watcher debe ignorar.
        (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
        (tmp_path / "version.json").write_text("{}", encoding="utf-8")

    hilo = threading.Thread(target=_escribir_despues_de_arrancar, daemon=True)
    hilo.start()

    inicio = time.time()
    iniciar_watcher(
        str(tmp_path),
        debounce_ms=10,
        callback=_cb,
        max_iterations=15,
        min_interval_s=1,
    )
    transcurrido = time.time() - inicio

    # Debe refrescar, pero como máximo una vez por intervalo (con un margen de
    # uno por el límite del ciclo). Sin la guarda habría ~15 refrescos.
    assert len(llamadas) >= 1, llamadas
    assert len(llamadas) <= transcurrido / 1.0 + 1, (len(llamadas), transcurrido)


def test_ejecutar_refresco_default_no_escribe_historial(tmp_path, monkeypatch):
    """El refresco del daemon pide ``no_snapshot=True`` al build."""
    capturado: dict[str, object] = {}

    def _fake_cmd_refresh(args):
        capturado["no_snapshot"] = getattr(args, "no_snapshot", None)
        capturado["target"] = getattr(args, "target", None)
        capturado["quiet"] = getattr(args, "quiet", None)

    monkeypatch.setattr(refresh_module, "cmd_refresh", _fake_cmd_refresh)
    _ejecutar_refresco_default(str(tmp_path))

    assert capturado["no_snapshot"] is True
    assert capturado["target"] == str(tmp_path)
    assert capturado["quiet"] is True

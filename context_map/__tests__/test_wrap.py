"""Comando wrap: cierre de sesión (R3, auditoría 2026-08-14).

Verifica que ``cmd_wrap`` ejecuta refresh y luego imprime un resumen de
lo registrado (eventos en events.jsonl) vs lo que queda sin importar
(sesiones de Hermes posteriores al último build).
"""

from __future__ import annotations

import json

from context_map.application.commands.wrap import cmd_wrap


def _hacer_proyecto(tmp_path) -> str:
    """Crea un mini proyecto con un events.jsonl con 3 eventos."""
    raw = tmp_path / ".context-map" / "raw"
    state = tmp_path / ".context-map" / "state"
    raw.mkdir(parents=True)
    state.mkdir(parents=True)
    (state / "last_build.json").write_text(
        json.dumps({"clean": False, "timestamp": "2000-01-01T00:00:00"}),
        encoding="utf-8",
    )
    with open(raw / "events.jsonl", "w", encoding="utf-8") as f:
        for i in range(3):
            f.write(json.dumps({"type": "IDEA", "text": f"evento {i}"}) + "\n")
    return str(tmp_path)


def test_wrap_ejecuta_refresh_y_resume(tmp_path, monkeypatch, capsys):
    """wrap corre refresh y reporta eventos registrados + sesiones pendientes."""
    ruta = _hacer_proyecto(tmp_path)
    llamadas = []

    def _fake_refresh(args):  # noqa: ANN001
        llamadas.append(args)
        print("[refresh] OK")

    def _fake_pendientes(_ruta):  # noqa: ANN001
        return 2

    monkeypatch.setattr("context_map.application.commands.wrap.cmd_refresh", _fake_refresh)
    monkeypatch.setattr(
        "context_map.application.commands.wrap._sesiones_pendientes", _fake_pendientes,
    )

    class Args:
        target = ruta
        project = "MiProyecto"

    cmd_wrap(Args())
    salida = capsys.readouterr().out

    assert len(llamadas) == 1  # refresh ejecutado
    assert "3" in salida  # eventos registrados
    assert "2" in salida  # sesiones pendientes


def test_wrap_sin_events_jsonl_no_falla(tmp_path, monkeypatch, capsys):
    """Si no existe events.jsonl, wrap no falla y reporta 0 eventos."""
    ruta = str(tmp_path)

    def _fake_refresh(args):  # noqa: ANN001
        print("[refresh] OK")

    monkeypatch.setattr("context_map.application.commands.wrap.cmd_refresh", _fake_refresh)
    monkeypatch.setattr(
        "context_map.application.commands.wrap._sesiones_pendientes", lambda _r: 0,
    )

    class Args:
        target = ruta
        project = "MiProyecto"

    cmd_wrap(Args())
    salida = capsys.readouterr().out
    assert "0" in salida

"""Tests del comando `ctxmap history` (list y prune)."""

from __future__ import annotations

import json
import os
import time

from context_map.application.commands.history_cmd import cmd_history


def _hist(tmp_path, n: int = 30, peso: int = 2048):
    """Crea `n` snapshots .md con mtime creciente en el historial del proyecto."""
    d = tmp_path / ".context-map" / "maps" / "HISTORY"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        f = d / f"snap-{i:03d}.md"
        f.write_bytes(b"x" * peso)
        os.utime(f, (time.time() + i, time.time() + i))
    return d


def test_history_list_json(tmp_path, monkeypatch, capsys):
    """`history list --json` reporta archivos y bytes del historial."""
    monkeypatch.chdir(tmp_path)
    _hist(tmp_path, 5)
    cmd_history({"action": "list", "target_dir": ".", "json": True})
    datos = json.loads(capsys.readouterr().out)
    assert datos["files"] == 5
    assert datos["bytes"] == 5 * 2048
    assert datos["max_snapshots"] == 20


def test_history_prune_keep_y_dry_run(tmp_path, monkeypatch, capsys):
    """`prune` respeta --keep y no borra nada con dry-run."""
    monkeypatch.chdir(tmp_path)
    d = _hist(tmp_path, 8)
    cmd_history({"action": "prune", "target_dir": ".", "keep": 3, "dry_run": True})
    assert len(list(d.glob("*.md"))) == 8  # dry-run no borra
    assert "simulación" in capsys.readouterr().out
    cmd_history({"action": "prune", "target_dir": ".", "keep": 3, "dry_run": False})
    assert len(list(d.glob("*.md"))) == 3


def test_history_accion_desconocida(tmp_path, monkeypatch, capsys):
    """Una acción inválida se informa sin romper."""
    monkeypatch.chdir(tmp_path)
    cmd_history({"action": "borrar-todo", "target_dir": "."})
    assert "desconocida" in capsys.readouterr().out

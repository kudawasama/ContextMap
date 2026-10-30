"""Tests del comando `ctxmap history` (list y prune)."""

from __future__ import annotations

import json
import os
import time

from context_map.application.commands.history_cmd import cmd_history


def _hist(tmp_path, n: int = 8, peso: int = 2048):
    """Crea `n` snapshots .md con mtime creciente en el historial del proyecto."""
    d = tmp_path / ".context-map" / "maps" / "HISTORY"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        f = d / f"snap-{i:03d}.md"
        f.write_bytes(b"x" * peso)
        momento = time.time() + i
        os.utime(f, (momento, momento))
    return d


def test_history_list_json(tmp_path, monkeypatch, capsys):
    """`history list --json` reporta snapshots, tamaño y retención."""
    monkeypatch.chdir(tmp_path)
    _hist(tmp_path, 5)
    cmd_history({"action": "list", "target_dir": ".", "json": True})
    datos = json.loads(capsys.readouterr().out)
    assert datos["snapshots"] == 5
    assert datos["bytes"] == 5 * 2048
    assert datos["keep_default"] == 20


def test_history_prune_archiva_lo_sobrante(tmp_path, monkeypatch, capsys):
    """`prune` conserva los recientes y archiva el resto sin borrar nada."""
    monkeypatch.chdir(tmp_path)
    d = _hist(tmp_path, 8)
    cmd_history({
        "action": "prune",
        "target_dir": ".",
        "keep": 3,
        "keep_days": 0,
        "dry_run": False,
    })
    quedan = sorted(p.name for p in d.glob("*.md"))
    assert len(quedan) == 3, quedan
    archivo = tmp_path / ".context-map" / "maps" / "archive"
    assert list(archivo.glob("*.tar.gz")), "lo podado debe quedar archivado"


def test_history_prune_dry_run_no_toca_nada(tmp_path, monkeypatch, capsys):
    """`prune --dry-run` solo informa."""
    monkeypatch.chdir(tmp_path)
    d = _hist(tmp_path, 6)
    cmd_history({
        "action": "prune",
        "target_dir": ".",
        "keep": 2,
        "keep_days": 0,
        "dry_run": True,
    })
    assert len(list(d.glob("*.md"))) == 6
    assert "simulación" in capsys.readouterr().out


def test_history_accion_desconocida(tmp_path, monkeypatch, capsys):
    """Una acción inválida se informa sin romper."""
    monkeypatch.chdir(tmp_path)
    cmd_history({"action": "borrar-todo", "target_dir": "."})
    assert "desconocida" in capsys.readouterr().out

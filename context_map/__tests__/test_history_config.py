"""Tests de la configuración declarativa de retención del historial."""

from __future__ import annotations

from context_map.core.storage.config_loader import load_project_config


def test_config_historial_desde_contextmap_toml(tmp_path):
    """`.contextmap.toml` parametriza retención y watcher."""
    (tmp_path / ".contextmap.toml").write_text(
        'project_name = "Demo"\n'
        "max_snapshots = 3\n"
        "history_max_mb = 64\n"
        "history_min_free_mb = 128\n"
        "watch_min_interval_s = 120\n",
        encoding="utf-8",
    )
    cfg = load_project_config(str(tmp_path))
    assert cfg.max_snapshots == 3
    assert cfg.history_max_mb == 64
    assert cfg.history_min_free_mb == 128
    assert cfg.watch_min_interval_s == 120


def test_config_historial_desde_pyproject(tmp_path):
    """`[tool.contextmap]` de pyproject.toml también aporta los parámetros."""
    (tmp_path / "pyproject.toml").write_text(
        "[tool.contextmap]\n"
        'project_name = "DemoPy"\n'
        "max_snapshots = 7\n"
        "history_max_mb = 128\n",
        encoding="utf-8",
    )
    cfg = load_project_config(str(tmp_path))
    assert cfg.max_snapshots == 7
    assert cfg.history_max_mb == 128
    assert cfg.history_min_free_mb == 512  # valor por defecto intacto


def test_config_historial_defaults(tmp_path):
    """Sin configuración se aplican los valores seguros por defecto."""
    cfg = load_project_config(str(tmp_path))
    assert (cfg.max_snapshots, cfg.history_max_mb, cfg.watch_min_interval_s) == (20, 512, 60)

"""Tests de `snapshot_map`: guardas de espacio, deduplicado, nombres y poda."""

from __future__ import annotations

import os
import re

import pytest

from context_map.core.storage import store
from context_map.core.storage.history import HISTORY_DIR


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    """Prepara un proyecto mínimo con su `.context-map/maps/ACTIVE.md`."""
    monkeypatch.chdir(tmp_path)
    maps = tmp_path / ".context-map" / "maps"
    maps.mkdir(parents=True)
    (maps / "ACTIVE.md").write_text("# mapa\ncontenido inicial\n", encoding="utf-8")
    return tmp_path


def test_snapshot_omitido_sin_espacio(proyecto, monkeypatch, caplog):
    """Sin espacio libre no se crea snapshot y se registra la causa."""
    monkeypatch.setattr(store, "hay_espacio", lambda *a, **k: False)
    with caplog.at_level("WARNING"):
        resultado = store.snapshot_map(name="prueba.md")
    assert resultado is None
    assert not os.path.exists(os.path.join(HISTORY_DIR, "prueba.md"))
    assert "Snapshot omitido" in caplog.text


def test_snapshot_duplicado_no_repite(proyecto):
    """Dos llamadas con el mismo contenido dejan un único snapshot."""
    primero = store.snapshot_map(name="dup.md")
    segundo = store.snapshot_map(name="dup.md")
    assert primero is not None
    assert segundo is None
    assert len(os.listdir(HISTORY_DIR)) == 1


def test_snapshot_poda_al_superar_keep(proyecto):
    """La retención recorta el historial en cada snapshot."""
    activo = proyecto / ".context-map" / "maps" / "ACTIVE.md"
    for i in range(4):
        activo.write_text(f"# mapa v{i}\n", encoding="utf-8")
        assert store.snapshot_map(name=f"snap-{i}.md", keep=2) is not None
    assert len(os.listdir(HISTORY_DIR)) == 2


def test_colision_de_nombre_no_usa_series_infinitas(proyecto):
    """Una colisión de nombre se resuelve con timestamp, sin series -2..-N."""
    hist = proyecto / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / "forzado.md").write_text("otro contenido\n", encoding="utf-8")

    primero = store.snapshot_map(name="forzado.md")
    assert primero is not None
    assert primero != str(hist / "forzado.md")

    (proyecto / ".context-map" / "maps" / "ACTIVE.md").write_text(
        "# mapa\nv2\n", encoding="utf-8"
    )
    segundo = store.snapshot_map(name="forzado.md")
    assert segundo is not None
    assert segundo != primero

    nombres = sorted(p.name for p in hist.glob("*.md"))
    assert len(nombres) == 3
    # Tras quitar la marca temporal no debe quedar ningún contador tipo `-2..-N`
    sin_marca = [re.sub(r"-\d{8}-\d{6}", "", n) for n in nombres]
    assert not any(re.search(r"-\d+\.md$", n) for n in sin_marca), nombres

"""Tests de la gestión del historial de snapshots (retención y métricas)."""

from __future__ import annotations

import os
import time

from context_map.core.storage.history import (
    PodaResult,
    espacio_libre_mb,
    estadisticas,
    hay_espacio,
    huella_archivo,
    podar,
)


def _crear_snapshots(dir_hist, cantidad: int, peso: int = 1024) -> None:
    """Crea `cantidad` snapshots .md con mtime creciente."""
    dir_hist.mkdir(parents=True, exist_ok=True)
    for i in range(cantidad):
        f = dir_hist / f"snap-{i:03d}.md"
        f.write_bytes(b"x" * peso)
        os.utime(f, (time.time() + i, time.time() + i))


def test_estadisticas_cuenta_y_suma(tmp_path):
    """Cuenta archivos y bytes del historial."""
    _crear_snapshots(tmp_path, 3, peso=100)
    st = estadisticas(str(tmp_path))
    assert st.files == 3
    assert st.bytes == 300


def test_podar_por_cantidad_conserva_los_mas_recientes(tmp_path):
    """Conserva exactamente `keep` snapshots y borra los más antiguos."""
    _crear_snapshots(tmp_path, 10)
    res = podar(str(tmp_path), keep=4, max_mb=0)  # max_mb=0 desactiva el tope por tamaño
    assert isinstance(res, PodaResult)
    assert len(res.borrados) == 6
    assert res.restantes == 4
    nombres = sorted(p.name for p in tmp_path.glob("*.md"))
    assert nombres == ["snap-006.md", "snap-007.md", "snap-008.md", "snap-009.md"]


def test_podar_por_tamano_nunca_borra_el_mas_reciente(tmp_path):
    """Con un tope muy bajo deja al menos un archivo (el más reciente)."""
    _crear_snapshots(tmp_path, 5, peso=1024 * 1024)  # 1 MB cada uno
    res = podar(str(tmp_path), keep=99, max_mb=2)
    assert res.restantes == 2
    assert (tmp_path / "snap-004.md").exists()


def test_podar_dry_run_no_borra(tmp_path):
    """`dry_run` calcula la poda sin tocar el disco."""
    _crear_snapshots(tmp_path, 6)
    res = podar(str(tmp_path), keep=2, max_mb=0, dry_run=True)
    assert len(res.borrados) == 4
    assert len(list(tmp_path.glob("*.md"))) == 6


def test_podar_directorio_inexistente(tmp_path):
    """No explota si el historial no existe."""
    res = podar(str(tmp_path / "no-existe"), keep=5)
    assert res.borrados == []
    assert res.restantes == 0


def test_huella_archivo_es_estable(tmp_path):
    """La huella depende del contenido, no del nombre."""
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("contenido", encoding="utf-8")
    b.write_text("contenido", encoding="utf-8")
    assert huella_archivo(str(a)) == huella_archivo(str(b))
    b.write_text("otro", encoding="utf-8")
    assert huella_archivo(str(a)) != huella_archivo(str(b))


def test_hay_espacio_umbral(tmp_path):
    """`hay_espacio` respeta el umbral pedido."""
    assert hay_espacio(str(tmp_path), min_free_mb=1) is True
    assert isinstance(espacio_libre_mb(str(tmp_path)), float)

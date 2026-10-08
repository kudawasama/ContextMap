"""Retención de snapshots (plan de revisión 2026-10-08).

El historial creaba un snapshot en **cada** build: 482 ficheros y 52 MB (93% del
peso de `.context-map`) con el grafo en 0,3 MB. Ahora: no se duplica si el mapa
no cambió, se conserva el detalle reciente y lo antiguo se **archiva** comprimido.
"""

from __future__ import annotations

import os
import tarfile
import time

from context_map.core.storage.store import purgar_snapshots, snapshot_map


def _crear_historial(tmp_path, n: int, dias_atras: int = 0) -> str:
    """Crea ``n`` snapshots falsos en maps/HISTORY con mtime escalonado.

    Args:
        tmp_path: Ruta temporal de pytest.
        n (int): Número de snapshots.
        dias_atras (int): Días hacia atrás del primero (los demás se acercan).

    Returns:
        str: Ruta absoluta de la carpeta del historial.
    """
    history = tmp_path / ".context-map" / "maps" / "HISTORY"
    history.mkdir(parents=True)
    base = time.time() - dias_atras * 86400
    for i in range(n):
        fichero = history / f"snap-{i:03d}.md"
        fichero.write_text(f"# snapshot {i}\n", encoding="utf-8")
        momento = base + i * 60
        os.utime(fichero, (momento, momento))
    return str(history)


def test_no_duplica_snapshot_si_el_mapa_no_cambio(tmp_path, monkeypatch) -> None:
    """Dos builds idénticos producen UN solo snapshot (idempotencia)."""
    monkeypatch.chdir(tmp_path)
    activo = tmp_path / ".context-map" / "maps" / "ACTIVE.md"
    activo.parent.mkdir(parents=True)
    activo.write_text("# mapa\n\ncontenido estable\n", encoding="utf-8")

    primero = snapshot_map()
    segundo = snapshot_map()

    history = tmp_path / ".context-map" / "maps" / "HISTORY"
    creados = list(history.glob("*.md"))
    assert primero is not None and segundo is not None
    assert len(creados) == 1, f"debería reutilizar el snapshot: {creados}"
    assert primero == segundo


def test_snapshot_nuevo_cuando_el_mapa_cambia(tmp_path, monkeypatch) -> None:
    """Si el mapa cambia, sí se crea un snapshot nuevo."""
    monkeypatch.chdir(tmp_path)
    activo = tmp_path / ".context-map" / "maps" / "ACTIVE.md"
    activo.parent.mkdir(parents=True)
    activo.write_text("# mapa v1\n", encoding="utf-8")
    snapshot_map()

    activo.write_text("# mapa v2 (cambió)\n", encoding="utf-8")
    snapshot_map()

    history = tmp_path / ".context-map" / "maps" / "HISTORY"
    assert len(list(history.glob("*.md"))) == 2


def test_retencion_conserva_los_recientes_y_archiva_el_resto(tmp_path, monkeypatch) -> None:
    """Con keep=3 quedan 3 ficheros y el resto se archiva comprimido (sin borrar)."""
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP", "3")
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP_DAYS", "0")
    history = _crear_historial(tmp_path, n=8)

    res = purgar_snapshots(history)

    quedan = sorted(os.listdir(history))
    assert len(quedan) == 3, quedan
    assert "snap-007.md" in quedan, "debe conservar el más reciente"
    assert res["archivados"] == 5 and res["eliminados"] == 0

    tar = str(res["archivo"])
    assert os.path.exists(tar), "el archivo comprimido debe existir"
    with tarfile.open(tar, "r:gz") as t:
        nombres = set(t.getnames())
    assert {"snap-000.md", "snap-004.md"} <= nombres, nombres


def test_conserva_uno_por_dia(tmp_path, monkeypatch) -> None:
    """Además de los recientes, se conserva el último snapshot de cada día."""
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP", "1")
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP_DAYS", "3")
    history = tmp_path / ".context-map" / "maps" / "HISTORY"
    history.mkdir(parents=True)
    # Un snapshot por día, del más nuevo al más antiguo (5 días distintos).
    ahora = time.time()
    for dia in range(5):
        fichero = history / f"dia-{dia}.md"
        fichero.write_text(f"# día {dia}\n", encoding="utf-8")
        momento = ahora - dia * 86400
        os.utime(fichero, (momento, momento))

    res = purgar_snapshots(str(history))

    quedan = sorted(os.listdir(history))
    assert len(quedan) == 3, quedan  # el más reciente + uno por día (3 días)
    assert "dia-0.md" in quedan and "dia-2.md" in quedan
    assert "dia-4.md" not in quedan
    assert res["archivados"] == 2


def test_modo_borrado_explicito(tmp_path, monkeypatch) -> None:
    """CTXMAP_SNAPSHOT_ARCHIVE=0 borra en vez de archivar (opt-in)."""
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP", "1")
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP_DAYS", "0")
    monkeypatch.setenv("CTXMAP_SNAPSHOT_ARCHIVE", "0")
    history = _crear_historial(tmp_path, n=4)

    res = purgar_snapshots(history)

    assert len(os.listdir(history)) == 1
    assert res["eliminados"] == 3 and res["archivados"] == 0
    assert not os.path.exists(str(res["archivo"]) or "no-existe")


def test_no_toca_ficheros_que_no_son_snapshots(tmp_path, monkeypatch) -> None:
    """Solo se podan los ``*.md`` del historial; el resto queda intacto."""
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP", "1")
    monkeypatch.setenv("CTXMAP_SNAPSHOT_KEEP_DAYS", "0")
    history = _crear_historial(tmp_path, n=3)
    ajeno = os.path.join(history, "LEEME.txt")
    with open(ajeno, "w", encoding="utf-8") as f:
        f.write("no es un snapshot\n")

    purgar_snapshots(history)

    assert os.path.exists(ajeno), "un fichero ajeno no debe tocarse"


def test_historial_vacio_no_falla(tmp_path) -> None:
    """Sin historial no hay nada que podar (y no revienta)."""
    res = purgar_snapshots(str(tmp_path / "no-existe"))
    assert res["conservados"] == 0 and res["archivados"] == 0

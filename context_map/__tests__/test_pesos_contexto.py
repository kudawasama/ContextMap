"""Medición del peso del contexto y aviso de excesos (plan de revisión 2026-10-08).

El 93% del peso de `.context-map` eran snapshots sin retención. La retención es
automática, pero debe poder **verse** el desglose y avisar si vuelve a crecer.
"""

from __future__ import annotations

from context_map.domain.health import pesos


def _proyecto_falso(tmp_path, snapshots: int = 3, tars: int = 1) -> str:
    """Crea un `.context-map` con áreas de tamaños conocidos."""
    ctx = tmp_path / ".context-map"
    (ctx / "maps" / "HISTORY").mkdir(parents=True)
    (ctx / "maps" / "archive").mkdir(parents=True)
    (ctx / "vault-Demo").mkdir()
    (ctx / "state").mkdir()
    (ctx / "_legacy" / "vault-Viejo").mkdir(parents=True)

    (ctx / "maps" / "ACTIVE.md").write_text("x" * 500, encoding="utf-8")
    for i in range(snapshots):
        (ctx / "maps" / "HISTORY" / f"snap-{i}.md").write_text("y" * 200, encoding="utf-8")
    for i in range(tars):
        (ctx / "maps" / "archive" / f"2026-0{i + 1}.tar.gz").write_bytes(b"z" * 300)
    (ctx / "vault-Demo" / "nota.md").write_text("v" * 400, encoding="utf-8")
    (ctx / "state" / "graph.jsonl").write_text("g" * 100, encoding="utf-8")
    (ctx / "_legacy" / "vault-Viejo" / "viejo.md").write_text("l" * 250, encoding="utf-8")
    return str(tmp_path)


def test_sin_context_map_no_falla(tmp_path) -> None:
    """Sin `.context-map` devuelve un resultado vacío, sin excepción."""
    datos = pesos.medir_pesos(str(tmp_path))
    assert datos["existe"] is False
    assert datos["total_bytes"] == 0
    assert datos["alerta"] == ""
    assert "sin `.context-map`" in pesos.formatear_pesos(datos)[0]


def test_mide_areas_snapshots_y_archivo(tmp_path) -> None:
    """Cuenta snapshots vivos y comprimidos, y separa el archivo del historial."""
    raiz = _proyecto_falso(tmp_path, snapshots=3, tars=2)
    datos = pesos.medir_pesos(raiz)

    assert datos["existe"] is True
    assert datos["snapshots_vivos"] == 3
    assert datos["archivos_comprimidos"] == 2
    assert datos["total_bytes"] > 0
    assert "archive" in datos["areas"] and "maps" in datos["areas"]
    assert "legacy" in datos["areas"] and "vault" in datos["areas"]

    # El historial vivo NO debe incluir el peso del archivo comprimido.
    assert datos["areas"]["archive"] == 600  # 2 tars * 300 bytes
    assert datos["areas"]["maps"] == 500 + 3 * 200  # ACTIVE.md + snapshots


def test_alerta_por_tope_de_peso(tmp_path, monkeypatch) -> None:
    """Si el total supera el tope, hay alerta con sugerencia accionable."""
    raiz = _proyecto_falso(tmp_path)
    monkeypatch.setattr(pesos, "TOPE_MB", 0.0001)

    datos = pesos.medir_pesos(raiz)

    assert "tope" in datos["alerta"]
    assert "ctxmap build" in datos["sugerencia"]
    assert any("Peso elevado" in linea for linea in pesos.formatear_pesos(datos))


def test_alerta_por_exceso_de_snapshots(tmp_path, monkeypatch) -> None:
    """Demasiados snapshots vivos también avisan (aunque el peso sea bajo)."""
    raiz = _proyecto_falso(tmp_path, snapshots=5)
    monkeypatch.setattr(pesos, "TOPE_SNAPSHOTS", 2)

    datos = pesos.medir_pesos(raiz)

    assert "snapshots vivos" in datos["alerta"]
    assert datos["snapshots_vivos"] == 5


def test_sin_alerta_en_situacion_sana(tmp_path) -> None:
    """Un contexto pequeño y con pocos snapshots no genera avisos."""
    raiz = _proyecto_falso(tmp_path, snapshots=2, tars=1)
    datos = pesos.medir_pesos(raiz)
    assert datos["alerta"] == ""
    assert not any("⚠️" in linea for linea in pesos.formatear_pesos(datos))


def test_formato_incluye_total_y_desglose(tmp_path) -> None:
    """El formato resume el total y muestra las áreas principales."""
    raiz = _proyecto_falso(tmp_path)
    lineas = pesos.formatear_pesos(pesos.medir_pesos(raiz))
    assert any("Peso del contexto" in linea and "MB" in linea for linea in lineas)
    assert len(lineas) >= 2, lineas

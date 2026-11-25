"""Tests del anuncio de costo y la puerta de ``--confirmar`` (``REG-LIM-004``).

La regla se cumple cuando el motor **mide** el trabajo pendiente y **no arranca**
sin permiso. Se prueba con árboles reales: contar archivos de mentira no demuestra
nada, y una puerta que se abre sola tampoco.
"""

from __future__ import annotations

import json
import os

import pytest

from context_map.application.commands import _coste
from context_map.core.audit.bitacora import CODIGO_RECHAZO


def _arbol(tmp_path, extensiones: dict[str, int]) -> str:
    """Crea archivos con esas extensiones y devuelve la carpeta."""
    raiz = os.path.join(str(tmp_path), "docs")
    os.makedirs(raiz, exist_ok=True)
    for extension, cuantos in extensiones.items():
        for i in range(cuantos):
            with open(os.path.join(raiz, f"doc{i}{extension}"), "w", encoding="utf-8") as f:
                f.write("x" * 100)
    return raiz


def test_cuenta_solo_los_archivos_que_el_comando_procesa(tmp_path) -> None:
    """``ingest`` mira documentos; un `.exe` colado no es trabajo."""
    raiz = _arbol(tmp_path, {".pdf": 3, ".md": 2, ".exe": 4})

    archivos, bytes_totales = _coste.medir(raiz, "ingest")

    assert archivos == 5
    assert bytes_totales == 500


def test_enrich_cuenta_solo_codigo(tmp_path) -> None:
    """``enrich`` trabaja sobre Python, no sobre documentos."""
    raiz = _arbol(tmp_path, {".py": 4, ".pdf": 2})

    archivos, _ = _coste.medir(raiz, "enrich")

    assert archivos == 4


def test_un_archivo_suelto_tambien_se_mide(tmp_path) -> None:
    """El objetivo puede ser un archivo, no una carpeta."""
    archivo = os.path.join(str(tmp_path), "suelto.md")
    with open(archivo, "w", encoding="utf-8") as f:
        f.write("x" * 2048)

    archivos, bytes_totales = _coste.medir(archivo, "ingest")

    assert (archivos, bytes_totales) == (1, 2048)


def test_sin_historial_no_se_inventan_segundos(tmp_path) -> None:
    """Sin bitácora se dice «sin historial», no una cifra al azar."""
    assert _coste.referencia_historica("ingest", str(tmp_path)) is None

    estimacion = _coste.estimar("ingest", _arbol(tmp_path, {".md": 2}), str(tmp_path))

    assert estimacion["referencia_s"] is None
    assert estimacion["archivos"] == 2


def test_la_referencia_sale_de_la_bitacora(tmp_path) -> None:
    """La mediana de lo que tardó antes es el único pronóstico con evidencia."""
    estado = os.path.join(str(tmp_path), ".context-map", "state")
    os.makedirs(estado, exist_ok=True)
    entradas = [
        {"ts": "2026-11-25T10:00:00", "comando": "ingest", "exit": 0, "duracion_s": 10.0},
        {"ts": "2026-11-25T11:00:00", "comando": "ingest", "exit": 0, "duracion_s": 20.0},
        {"ts": "2026-11-25T12:00:00", "comando": "ingest", "exit": 0, "duracion_s": 90.0},
        {"ts": "2026-11-25T13:00:00", "comando": "build", "exit": 0, "duracion_s": 5.0},
    ]
    with open(os.path.join(estado, "bitacora.jsonl"), "w", encoding="utf-8") as f:
        for entrada in entradas:
            f.write(json.dumps(entrada) + "\n")

    assert _coste.referencia_historica("ingest", str(tmp_path)) == 20.0


def test_el_anuncio_dice_cuantos_archivos_y_cuanto_pesa(tmp_path, capsys) -> None:
    """El anuncio es una cifra concreta, no una advertencia genérica."""
    raiz = _arbol(tmp_path, {".md": 3})

    costo = _coste.anunciar({"confirmar": True}, "ingest", raiz, str(tmp_path))

    salida = capsys.readouterr().out
    assert "3 archivo(s)" in salida
    assert "Confirmado con `--confirmar`" in salida
    assert costo["puede_seguir"] is True


def test_sin_confirmar_el_anuncio_avisa_que_se_detiene(tmp_path, capsys) -> None:
    """Un aviso que se puede ignorar no es una puerta: se dice y no se sigue."""
    raiz = _arbol(tmp_path, {".md": 1})

    costo = _coste.anunciar({"confirmar": False}, "ingest", raiz, str(tmp_path))

    salida = capsys.readouterr().out
    assert costo["puede_seguir"] is False
    assert "Falta `--confirmar`" in salida
    assert str(CODIGO_RECHAZO) in salida


def test_el_anuncio_no_copia_la_ruta_absoluta(tmp_path, capsys) -> None:
    """La salida nombra el objetivo, no la ruta completa de la máquina."""
    raiz = _arbol(tmp_path, {".md": 1})

    _coste.anunciar({"confirmar": False}, "ingest", raiz, str(tmp_path))

    assert str(tmp_path) not in capsys.readouterr().out


def test_detener_sale_con_el_codigo_de_rechazo() -> None:
    """El código de rechazo es lo que permite distinguir «no lo hice» de «falló»."""
    with pytest.raises(SystemExit) as salida:
        _coste.detener()

    assert salida.value.code == CODIGO_RECHAZO


def test_acepta_namespace_y_dict(tmp_path, capsys) -> None:
    """El comando recibe ambas formas según quién lo invoque."""
    from types import SimpleNamespace

    raiz = _arbol(tmp_path, {".md": 1})

    por_dict = _coste.anunciar({"confirmar": True}, "ingest", raiz, str(tmp_path))
    por_namespace = _coste.anunciar(
        SimpleNamespace(confirmar=False), "ingest", raiz, str(tmp_path)
    )

    assert por_dict["puede_seguir"] is True
    assert por_namespace["puede_seguir"] is False
    capsys.readouterr()


def test_ingest_se_detiene_sin_confirmar(tmp_path, capsys) -> None:
    """Integración: el comando real no procesa nada si falta el permiso."""
    from context_map.application.commands.ingest import cmd_ingest

    raiz = _arbol(tmp_path, {".md": 2})

    with pytest.raises(SystemExit) as salida:
        cmd_ingest({"target": raiz, "confirmar": False, "project": "Demo"})

    assert salida.value.code == CODIGO_RECHAZO
    assert "Falta `--confirmar`" in capsys.readouterr().out


def test_solo_las_tareas_caras_tienen_puerta() -> None:
    """`scan`, `build` y `refresh` son recorridos locales: no piden bandera."""
    from context_map.core.audit.bitacora import COMANDOS_CON_PERMISO

    assert "ingest" in COMANDOS_CON_PERMISO
    assert "enrich" in COMANDOS_CON_PERMISO
    for barato in ("scan", "build", "refresh", "check", "doctor"):
        assert barato not in COMANDOS_CON_PERMISO

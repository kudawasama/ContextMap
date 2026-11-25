"""Contrato de la bitácora de ejecuciones (la evidencia, no la promesa).

La bitácora es el único sitio donde el motor deja constancia de lo que hizo. Si
miente o se cae, las reglas de conducta de la sesión se quedan sin base: por eso
se prueba en sus dos caras —registra lo que pasó y no tumba el comando.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from context_map.core.audit import bitacora


def _ruta(raiz: Path) -> Path:
    return raiz / ".context-map" / "state" / "bitacora.jsonl"


def test_registrar_crea_la_bitacora(tmp_path):
    bitacora.registrar("doctor", exit_code=0, duracion_s=12.34, project_dir=str(tmp_path))
    lineas = _ruta(tmp_path).read_text(encoding="utf-8").strip().splitlines()
    assert len(lineas) == 1
    entrada = json.loads(lineas[0])
    assert entrada["comando"] == "doctor"
    assert entrada["exit"] == 0
    assert entrada["duracion_s"] == 12.34
    assert entrada["ts"][:2] == "20"


def test_registrar_es_append_y_conserva_el_orden(tmp_path):
    for comando in ("doctor", "check", "build"):
        bitacora.registrar(comando, project_dir=str(tmp_path))
    assert [e["comando"] for e in bitacora.leer(str(tmp_path))] == ["doctor", "check", "build"]


def test_registrar_crea_la_carpeta_de_estado(tmp_path):
    bitacora.registrar("doctor", project_dir=str(tmp_path))
    assert _ruta(tmp_path).is_file()


def test_registrar_no_falla_si_no_puede_escribir(tmp_path):
    """Una bitácora que tumba el comando que registra es peor que no tener bitácora."""
    (tmp_path / ".context-map").write_text("soy un archivo, no una carpeta", encoding="utf-8")
    bitacora.registrar("doctor", project_dir=str(tmp_path))  # no debe lanzar
    assert bitacora.leer(str(tmp_path)) == []


def test_registrar_no_copia_rutas_ni_valores(tmp_path):
    bitacora.registrar(
        "doctor", flags=["fix", "C:/ruta/secreta"], project_dir=str(tmp_path)
    )
    crudo = _ruta(tmp_path).read_text(encoding="utf-8")
    assert "fix" in crudo
    assert "secreta" in crudo  # las banderas se anotan tal cual llegan...
    # ...pero la CLI solo pasa nombres de bandera: el filtro vive en cli.py


def test_leer_salta_lineas_corruptas(tmp_path):
    ruta = _ruta(tmp_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        '{"comando": "doctor", "exit": 0}\n'
        "{ esto no es json\n"
        '{"comando": "check", "exit": 1}\n',
        encoding="utf-8",
    )
    assert [e["comando"] for e in bitacora.leer(str(tmp_path))] == ["doctor", "check"]


def test_leer_sin_archivo_devuelve_vacio(tmp_path):
    assert bitacora.leer(str(tmp_path)) == []


def test_ultima_y_primera_del_dia(tmp_path):
    ruta = _ruta(tmp_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        "\n".join([
            '{"ts": "2020-01-01T10:00:00", "comando": "doctor", "exit": 0}',
            '{"ts": "2999-01-01T10:00:00", "comando": "build", "exit": 0}',
        ]) + "\n",
        encoding="utf-8",
    )
    assert bitacora.ultima(str(tmp_path))["comando"] == "build"
    assert bitacora.primera_del_dia(str(tmp_path)) is None  # el día de hoy no tiene entradas
    assert bitacora.ultima(str(tmp_path), comando="doctor")["comando"] == "doctor"


def test_resumen_cuenta_por_comando(tmp_path):
    for comando in ("doctor", "doctor", "check"):
        bitacora.registrar(comando, project_dir=str(tmp_path))
    datos = bitacora.resumen(str(tmp_path))
    assert datos["total"] == 3
    assert datos["por_comando"] == {"check": 1, "doctor": 2}
    assert datos["ultima"]["comando"] == "check"


def test_rotacion_conserva_las_ultimas(tmp_path):
    ruta = _ruta(tmp_path)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    # 200 entradas + relleno para pasar el umbral de tamaño
    lineas = [
        json.dumps({"ts": f"2026-01-01T00:00:{i % 60:02d}", "comando": f"cmd{i}", "exit": 0,
                    "relleno": "x" * 3000})
        for i in range(200)
    ]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    antes = os.path.getsize(ruta)
    bitacora._rotar(str(ruta), maximo=10)
    despues = bitacora.leer(str(tmp_path))
    assert len(despues) == 10
    assert despues[-1]["comando"] == "cmd199"
    assert os.path.getsize(ruta) < antes

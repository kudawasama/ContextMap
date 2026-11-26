"""Tests de la evidencia de sesión (``REG-EJE-005``).

El informe sale del registro que escribe el motor, no de lo que el agente
cuenta: se comprueba que copia lo que la bitácora tiene, que declara lo que falta
y que no transporta datos que no le tocan.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from context_map.domain.reporting.evidencia import (
    FUERA_DE_ALCANCE,
    PUERTAS,
    construir_evidencia,
    formatear_evidencia_texto,
)

HOY = datetime.now().strftime("%Y-%m-%d")
AYER = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


def _bitacora(raiz: Path, entradas: list[dict]) -> Path:
    """Escribe la bitácora del proyecto con las entradas dadas."""
    estado = raiz / ".context-map" / "state"
    estado.mkdir(parents=True, exist_ok=True)
    ruta = estado / "bitacora.jsonl"
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        for entrada in entradas:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    return ruta


def _lecturas(raiz: Path, ts: str, rutas: list[str]) -> Path:
    """Escribe la huella de lecturas con las rutas dadas."""
    estado = raiz / ".context-map" / "state"
    estado.mkdir(parents=True, exist_ok=True)
    ruta = estado / "lecturas.jsonl"
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        for r in rutas:
            f.write(json.dumps({"ts": ts, "ruta": r, "origen": "test"}, ensure_ascii=False) + "\n")
    return ruta


def _todo_verde() -> list[dict]:
    """Bitácora de una sesión completa del día."""
    return [
        {"ts": f"{HOY}T09:00:00", "comando": "brief", "exit": 0, "duracion_s": 0.4},
        {"ts": f"{HOY}T09:05:00", "comando": "doctor", "exit": 0, "duracion_s": 9.5, "fallos": 0},
        {"ts": f"{HOY}T09:10:00", "comando": "check", "exit": 0, "duracion_s": 2.0},
        {"ts": f"{HOY}T09:12:00", "comando": "reglas", "exit": 0, "duracion_s": 1.1},
    ]


# ── lo que se copia ─────────────────────────────────────────────────────────

def test_lista_las_ejecuciones_del_dia(tmp_path):
    _bitacora(tmp_path, _todo_verde())
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["total"] == 4
    assert [e["comando"] for e in reporte["ejecuciones"]] == ["brief", "doctor", "check", "reglas"]
    assert reporte["estado"] == "completa"


def test_no_inventa_ejecuciones_de_otros_dias(tmp_path):
    _bitacora(tmp_path, [
        {"ts": f"{AYER}T09:00:00", "comando": "brief", "exit": 0},
        {"ts": f"{HOY}T09:00:00", "comando": "build", "exit": 0},
    ])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["total"] == 1
    assert reporte["ejecuciones"][0]["comando"] == "build"


def test_se_puede_revisar_otro_dia(tmp_path):
    _bitacora(tmp_path, [
        {"ts": f"{AYER}T09:00:00", "comando": "brief", "exit": 0},
        {"ts": f"{HOY}T09:00:00", "comando": "build", "exit": 0},
    ])
    reporte = construir_evidencia(str(tmp_path), fecha=AYER)
    assert reporte["fecha"] == AYER
    assert reporte["total"] == 1
    assert reporte["ejecuciones"][0]["comando"] == "brief"


def test_muestra_solo_las_ultimas_y_dice_cuantas_omite(tmp_path):
    entradas = [
        {"ts": f"{HOY}T09:{i:02d}:00", "comando": "build", "exit": 0} for i in range(10)
    ]
    _bitacora(tmp_path, entradas)
    reporte = construir_evidencia(str(tmp_path), limite=3)
    assert len(reporte["ejecuciones"]) == 3
    assert reporte["omitidas"] == 7
    assert reporte["total"] == 10
    assert "7 ejecución(es) más antiguas" in formatear_evidencia_texto(reporte)


def test_no_transporta_campos_que_no_le_tocan(tmp_path):
    """La bitácora es del usuario: se copia lo declarado y nada más."""
    _bitacora(tmp_path, [{
        "ts": f"{HOY}T09:00:00",
        "comando": "build",
        "exit": 0,
        "ruta_secreta": "/home/alguien/proyecto/privado",
        "prompt": "texto que escribió el agente",
        "texto": "no debe salir en el informe",
    }])
    reporte = construir_evidencia(str(tmp_path))
    serializado = json.dumps(reporte, ensure_ascii=False)
    for prohibido in ("/home/alguien", "texto que escribió el agente", "no debe salir"):
        assert prohibido not in serializado
    assert "privado" not in formatear_evidencia_texto(reporte)


def test_una_linea_corrupta_no_tumba_el_informe(tmp_path):
    ruta = _bitacora(tmp_path, [{"ts": f"{HOY}T09:00:00", "comando": "build", "exit": 0}])
    with open(ruta, "a", encoding="utf-8", newline="\n") as f:
        f.write("{ esto no es json\n")
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["total"] == 1


# ── puertas: aviso no es fallo ──────────────────────────────────────────────

def test_una_puerta_en_rojo_marca_la_sesion_incompleta(tmp_path):
    _bitacora(tmp_path, _todo_verde() + [
        {"ts": f"{HOY}T10:00:00", "comando": "doctor", "exit": 1, "fallos": 2},
    ])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["puertas"]["doctor"]["ok"] is False
    assert "doctor" in reporte["en_rojo"]
    assert reporte["estado"] == "incompleta"


def test_strict_warn_con_cero_fallos_es_aviso_no_rojo(tmp_path):
    """La bandera más estricta sale con 1 aunque solo avise."""
    _bitacora(tmp_path, _todo_verde() + [
        {"ts": f"{HOY}T10:00:00", "comando": "doctor", "exit": 1, "fallos": 0,
         "flags": ["strict-warn"]},
    ])
    reporte = construir_evidencia(str(tmp_path))
    puerta = reporte["puertas"]["doctor"]
    assert puerta["ok"] is True
    assert puerta["avisos"] is True
    assert reporte["estado"] == "completa"
    assert "doctor ⚠️" in formatear_evidencia_texto(reporte)


def test_sin_campo_fallos_manda_el_codigo_de_salida(tmp_path):
    _bitacora(tmp_path, _todo_verde() + [
        {"ts": f"{HOY}T10:00:00", "comando": "check", "exit": 1},
    ])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["puertas"]["check"]["ok"] is False
    assert reporte["puertas"]["check"]["avisos"] is False


# ── lo que falta se declara ─────────────────────────────────────────────────

def test_una_puerta_no_ejecutada_se_declara_faltante(tmp_path):
    _bitacora(tmp_path, [{"ts": f"{HOY}T09:00:00", "comando": "build", "exit": 0}])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["faltantes"] == list(PUERTAS)
    assert reporte["estado"] == "incompleta"
    texto = formatear_evidencia_texto(reporte)
    assert "no se ejecutó, no se supone" in texto


def test_sin_bitacora_no_se_juzga_se_declara(tmp_path):
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["sin_registro"] is True
    assert reporte["estado"] == "sin-registro"
    texto = formatear_evidencia_texto(reporte)
    assert "no hay evidencia que leer" in texto
    assert "no se juzga" in texto


def test_sin_actividad_hoy_lo_dice(tmp_path):
    _bitacora(tmp_path, [{"ts": f"{AYER}T09:00:00", "comando": "build", "exit": 0}])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["estado"] == "sin-actividad"
    assert "no se puede juzgar" in formatear_evidencia_texto(reporte)


def test_lo_que_no_pasa_por_la_cli_se_declara_fuera_de_alcance(tmp_path):
    """Un «los tests pasan» no tiene evidencia aquí: decirlo es la evidencia."""
    _bitacora(tmp_path, _todo_verde())
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["fuera_de_alcance"] == list(FUERA_DE_ALCANCE)
    assert any("pytest" in x for x in reporte["fuera_de_alcance"])
    assert "Sin evidencia aquí: pytest" in formatear_evidencia_texto(reporte)


# ── lecturas ────────────────────────────────────────────────────────────────

def test_cuenta_las_lecturas_del_dia(tmp_path):
    _bitacora(tmp_path, _todo_verde())
    _lecturas(tmp_path, f"{HOY}T09:01:00", ["context_map/a.py", "context_map/b.py"])
    _lecturas(tmp_path, f"{AYER}T09:01:00", ["context_map/viejo.py"])
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["lecturas"] == 2
    assert reporte["archivos_leidos"] == ["context_map/a.py", "context_map/b.py"]
    assert "Lecturas registradas: 2" in formatear_evidencia_texto(reporte)


# ── el informe es un dato, no una prosa ────────────────────────────────────

def test_el_informe_es_serializable(tmp_path):
    _bitacora(tmp_path, _todo_verde())
    reporte = construir_evidencia(str(tmp_path))
    ida_y_vuelta = json.loads(json.dumps(reporte, ensure_ascii=False))
    assert ida_y_vuelta["total"] == reporte["total"]
    assert ida_y_vuelta["puertas"]["brief"]["ok"] is True


def test_cada_puerta_declara_su_regla(tmp_path):
    _bitacora(tmp_path, _todo_verde())
    reporte = construir_evidencia(str(tmp_path))
    assert reporte["puertas"]["doctor"]["regla"] == "REG-INI-001"
    assert all(p["regla"] for p in reporte["puertas"].values())

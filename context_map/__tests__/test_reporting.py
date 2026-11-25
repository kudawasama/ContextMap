"""Contrato de `domain/reporting`: el reporte semanal cuenta lo que debe contar.

Este test existe porque el chequeo `modulos_con_test` (``REG-ARQ-004``) detectó
que `domain/reporting/` no tenía ninguno: el submódulo se podía romper sin que
la suite se enterara.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from context_map.domain.reporting import generar_semanal, guardar_reporte


def _evento(texto: str, tipo: str, dias_atras: int = 0) -> dict:
    """Evento con la forma que escribe el grafo de contexto."""
    fecha = (datetime.now() - timedelta(days=dias_atras)).isoformat()
    return {"text": texto, "type": tipo, "created_at": fecha, "timestamp": fecha}


def _estado(tmp_path, eventos: list[dict]) -> str:
    """Directorio de estado con un `graph.jsonl` real."""
    estado = tmp_path / "state"
    estado.mkdir()
    with open(estado / "graph.jsonl", "w", encoding="utf-8") as fh:
        for evento in eventos:
            fh.write(json.dumps(evento, ensure_ascii=False) + "\n")
    return str(estado)


def test_el_reporte_cuenta_solo_la_ventana_pedida(tmp_path):
    estado = _estado(tmp_path, [
        _evento("cambio de hoy", "CAMBIO", dias_atras=0),
        _evento("idea de ayer", "IDEA", dias_atras=1),
        _evento("riesgo viejo", "RIESGO", dias_atras=40),
    ])

    reporte = generar_semanal(estado, dias=7)

    assert "**Total de eventos**: 2" in reporte
    assert "cambio de hoy" in reporte
    assert "riesgo viejo" not in reporte


def test_el_reporte_reparte_por_tipo_con_su_emoji(tmp_path):
    estado = _estado(tmp_path, [
        _evento("uno", "CAMBIO"),
        _evento("dos", "CAMBIO"),
        _evento("tres", "IDEA"),
    ])

    reporte = generar_semanal(estado, dias=7)

    assert "CAMBIO" in reporte and "IDEA" in reporte
    assert "2" in reporte


def test_sin_eventos_el_reporte_avisa_en_vez_de_reventar(tmp_path):
    estado = _estado(tmp_path, [])

    reporte = generar_semanal(estado, dias=7)

    assert "**Total de eventos**: 0" in reporte


def test_linea_corrupta_no_tumba_el_reporte(tmp_path):
    estado = _estado(tmp_path, [_evento("bueno", "CAMBIO")])
    with open(os.path.join(estado, "graph.jsonl"), "a", encoding="utf-8") as fh:
        fh.write("{esto no es json}\n")

    reporte = generar_semanal(estado, dias=7)

    assert "**Total de eventos**: 1" in reporte


def test_guardar_reporte_escribe_el_archivo_y_devuelve_la_ruta(tmp_path):
    estado = _estado(tmp_path, [_evento("algo", "HITO")])
    salida = tmp_path / "reporte.md"

    devuelta = guardar_reporte(estado, str(salida), dias=7)

    assert devuelta == str(salida)
    assert salida.is_file()
    assert "Reporte Semanal" in salida.read_text(encoding="utf-8")

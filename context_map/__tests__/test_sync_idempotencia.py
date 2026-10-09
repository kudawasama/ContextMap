"""Regresión P2.4: el hash de evento debe ser una huella de una sola línea.

Bug (2026-10-09): ``_hash_evento`` devolvía ``f"{type}|{text[:80]}|{source}"``.
Cuando el texto contenía saltos de línea, ``processed_events.txt`` (una marca
por línea) quedaba corrompido y la marca nunca volvía a coincidir, así que esos
eventos se reprocesaban en **cada** ``sync`` (se veía ``nodos 333 -> 344`` una y
otra vez). Arreglado con una huella sha1 hexadecimal del texto completo.
"""

from __future__ import annotations

import json
import os
import tempfile

from context_map.core.models import Event
from context_map.domain.synchronization import sync_incremental
from context_map.domain.synchronization.sync import _hash_evento


def test_hash_evento_es_hex_y_no_tiene_saltos_de_linea() -> None:
    """La huella es hexadecimal, de 40 caracteres y sin saltos de línea."""
    e = Event(type="IDEA", text="linea1\nlinea2 ✅ acentos", timestamp="t", source="chat")
    h = _hash_evento(e)
    assert "\n" not in h and "\r" not in h
    assert len(h) == 40
    assert all(c in "0123456789abcdef" for c in h)


def test_hash_evento_distingue_textos_que_coincidian_en_los_primeros_80() -> None:
    """Sin truncado, dos textos con los mismos 80 primeros caracteres no colisionan."""
    base = "X" * 80
    a = Event(type="IDEA", text=base + "AAA", timestamp="t", source="s")
    b = Event(type="IDEA", text=base + "BBB", timestamp="t", source="s")
    assert _hash_evento(a) != _hash_evento(b)


def test_sync_es_idempotente_con_eventos_multilinea() -> None:
    """Un segundo ``sync`` sin cambios no debe reprocesar ni agregar nodos."""
    temp = tempfile.mkdtemp(prefix="ctxmap_sync_idem_")
    chats = os.path.join(temp, "chats")
    raw = os.path.join(temp, "raw")
    state = os.path.join(temp, "state")
    for d in (chats, raw, state):
        os.makedirs(d)
    with open(os.path.join(raw, "events.jsonl"), "w", encoding="utf-8") as f:
        f.write(
            json.dumps(
                {
                    "type": "IDEA",
                    "text": "Titulo\n\ncuerpo con salto ✅",
                    "timestamp": "2026-01-01",
                    "source": "chat",
                }
            )
            + "\n"
        )

    s1 = sync_incremental(chats, raw, state)
    s2 = sync_incremental(chats, raw, state)

    assert s1["eventos_nuevos"] == 1
    assert s2["eventos_nuevos"] == 0, "los eventos ya marcados no deben reprocesarse"
    assert s2["nodos_agregados"] == 0
    assert s1["nodos_existentes"] == s2["nodos_existentes"]

    # La marca quedó en UNA línea por evento (no partida por los saltos de línea).
    with open(os.path.join(state, "processed_events.txt"), encoding="utf-8") as f:
        marcas = [ln for ln in f.read().splitlines() if ln.strip()]
    assert len(marcas) == 1
    assert len(marcas[0]) == 40

"""Repaso espaciado (SM-2) sobre la wiki del mundo conocimiento.

Implementa el algoritmo **SM-2** de SuperMemo de forma local y determinista:
cada página de la wiki tiene un estado (`repetitions`, `interval`, `ease`, `due`)
y el agente/usuario la califica de 0 a 5 tras repasarla. El estado vive en
``.context-map/state/review.json`` (fuera del vault, es estado operativo).

- ``paginas_due``  → qué toca repasar hoy (incluye páginas nunca vistas).
- ``calificar``    → aplica SM-2, reprograma la página y persiste el estado.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta

from context_map.domain.knowledge import wiki as kb

ESTADO_RELATIVO = os.path.join("state", "review.json")
EASE_MINIMO = 1.3
EASE_INICIAL = 2.5


def ruta_estado(vault_dir: str) -> str:
    """Ruta del archivo de estado del repaso (``.context-map/state/review.json``).

    Args:
        vault_dir (str): Directorio raíz del vault (``.context-map/vault-X``).

    Returns:
        str: Ruta absoluta del estado.
    """
    return os.path.join(os.path.dirname(vault_dir), ESTADO_RELATIVO)


def cargar_estado(vault_dir: str) -> dict:
    """Carga el estado de repaso; devuelve un estado vacío si no existe o está corrupto.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        dict: Estado con la clave ``paginas`` (dict de ruta→estado).
    """
    ruta = ruta_estado(vault_dir)
    if not os.path.exists(ruta):
        return {"paginas": {}}
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict) and isinstance(datos.get("paginas"), dict):
            return datos
    except Exception:  # noqa: BLE001 — estado inválido se regenera
        pass
    return {"paginas": {}}


def guardar_estado(vault_dir: str, estado: dict) -> None:
    """Persiste el estado de repaso en disco.

    Args:
        vault_dir (str): Directorio raíz del vault.
        estado (dict): Estado a guardar.
    """
    ruta = ruta_estado(vault_dir)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def calcular_sm2(estado: dict | None, calidad: int, hoy: date) -> dict:
    """Aplica SM-2 a un ítem y devuelve su nuevo estado.

    Args:
        estado (dict | None): Estado previo (o None si es la primera vez).
        calidad (int): Calificación 0-5 (>=3 se considera acierto).
        hoy (date): Fecha del repaso.

    Returns:
        dict: Estado actualizado (``repetitions``, ``interval``, ``ease``,
        ``due``, ``last``).
    """
    calidad = max(0, min(5, int(calidad)))
    previo = estado or {}
    repetitions = int(previo.get("repetitions", 0))
    interval = int(previo.get("interval", 0))
    ease = float(previo.get("ease", EASE_INICIAL))

    if calidad < 3:
        repetitions = 0
        interval = 1
    else:
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = max(1, round(interval * ease))
        repetitions += 1

    ease = ease + (0.1 - (5 - calidad) * (0.08 + (5 - calidad) * 0.02))
    ease = max(EASE_MINIMO, round(ease, 2))

    return {
        "repetitions": repetitions,
        "interval": interval,
        "ease": ease,
        "due": (hoy + timedelta(days=interval)).isoformat(),
        "last": hoy.isoformat(),
    }


def paginas_due(vault_dir: str, hoy: date | None = None, limite: int = 20) -> list[dict]:
    """Páginas de la wiki que toca repasar hoy (nunca vistas o vencidas).

    Args:
        vault_dir (str): Directorio raíz del vault.
        hoy (date | None): Fecha de referencia (default: hoy).
        limite (int): Máximo de páginas a devolver.

    Returns:
        list[dict]: Items con ``titulo``, ``cita`` y ``due`` ('' si es nueva).
    """
    hoy = hoy or date.today()
    estado = cargar_estado(vault_dir).get("paginas", {})
    pendientes: list[dict] = []
    for pagina in kb.listar_paginas(vault_dir):
        rel = kb.backlink_relativo(vault_dir, pagina["ruta"])
        item = estado.get(rel, {})
        due = str(item.get("due", ""))
        if due and date.fromisoformat(due) > hoy:
            continue
        pendientes.append({"titulo": pagina["titulo"], "cita": pagina["cita"], "due": due})
    pendientes.sort(key=lambda x: (x["due"] or "0000-00-00"))
    return pendientes[:limite]


def calificar(vault_dir: str, cita: str, calidad: int, hoy: date | None = None) -> dict:
    """Califica una página (por su cita/wikilink o título) y reprograma su repaso.

    Args:
        vault_dir (str): Directorio raíz del vault.
        cita (str): Título de la página o wikilink (``[[ruta|titulo]]``).
        calidad (int): Calificación 0-5.
        hoy (date | None): Fecha del repaso (default: hoy).

    Returns:
        dict: Estado nuevo de la página.

    Raises:
        ValueError: Si ninguna página coincide con ``cita``.
    """
    hoy = hoy or date.today()
    objetivo = cita.split("|")[-1].split("]]")[0].strip()
    for pagina in kb.listar_paginas(vault_dir):
        rel = kb.backlink_relativo(vault_dir, pagina["ruta"])
        if pagina["titulo"] == objetivo or rel == objetivo or pagina["cita"] == cita:
            estado = cargar_estado(vault_dir)
            nuevo = calcular_sm2(estado["paginas"].get(rel), calidad, hoy)
            estado["paginas"][rel] = nuevo
            guardar_estado(vault_dir, estado)
            return {"titulo": pagina["titulo"], "ruta": rel, **nuevo}
    raise ValueError(f"No existe una página de la wiki que coincida con: {cita}")


def contar_due(vault_dir: str, hoy: date | None = None) -> int:
    """Cantidad de páginas de la wiki pendientes de repaso hoy.

    Args:
        vault_dir (str): Directorio raíz del vault.
        hoy (date | None): Fecha de referencia.

    Returns:
        int: Número de páginas vencidas o nuevas.
    """
    return len(paginas_due(vault_dir, hoy=hoy, limite=10_000))

"""Medición del peso de ``.context-map`` y aviso de excesos.

Plan de revisión 2026-10-08: el **93% del peso** (54 de 58 MB) eran snapshots
creados sin retención. La retención ya es automática, pero el usuario y el agente
deben poder **ver** de dónde viene el peso y recibir un aviso si vuelve a crecer.

Uso:
    - ``ctxmap doctor --sizes`` → desglose legible.
    - ``ctxmap check`` → una línea con el total y aviso si excede el tope.
"""

from __future__ import annotations

import os
from typing import Any

# Topes de aviso (ajustables por entorno).
TOPE_MB = 100.0
TOPE_SNAPSHOTS = 200

# Áreas reconocidas del contexto y su etiqueta legible.
ETIQUETAS = {
    "maps": "📜 historial (snapshots vivos)",
    "archive": "🗜️ archivo comprimido",
    "state": "🧠 estado del grafo",
    "raw": "📥 documentos crudos",
    "chats": "💬 chats importados",
    "legacy": "🗄️ vaults antiguos (_legacy)",
    "vault": "🌳 vault de Obsidian",
    "tools": "🔧 herramientas",
    "plantillas": "📄 plantillas",
    "otros": "📦 otros",
}


def _peso(ruta: str) -> int:
    """Suma el tamaño (bytes) de todos los ficheros bajo ``ruta``."""
    if os.path.isfile(ruta):
        try:
            return os.path.getsize(ruta)
        except OSError:
            return 0
    total = 0
    for raiz, _dirs, ficheros in os.walk(ruta):
        for nombre in ficheros:
            try:
                total += os.path.getsize(os.path.join(raiz, nombre))
            except OSError:
                continue
    return total


def _mb(bytes_: int) -> float:
    """Convierte bytes a megabytes con un decimal."""
    return round(bytes_ / 1048576, 1)


def medir_pesos(project_dir: str = ".") -> dict[str, Any]:
    """Mide el peso de ``.context-map`` por áreas y evalúa si hay exceso.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        dict[str, Any]: ``existe``, ``total_bytes``, ``areas`` (bytes por área),
        ``snapshots_vivos``, ``archivos_comprimidos``, ``alerta`` (mensaje o
        cadena vacía), ``sugerencia`` y ``tope_mb``. Nunca lanza excepción.
    """
    ctx = os.path.join(project_dir, ".context-map")
    datos: dict[str, Any] = {
        "existe": os.path.isdir(ctx),
        "total_bytes": 0,
        "areas": {},
        "snapshots_vivos": 0,
        "archivos_comprimidos": 0,
        "alerta": "",
        "sugerencia": "",
        "tope_mb": TOPE_MB,
    }
    if not datos["existe"]:
        return datos

    areas: dict[str, int] = {}
    for entrada in sorted(os.listdir(ctx)):
        ruta = os.path.join(ctx, entrada)
        if entrada == "_legacy":
            areas["legacy"] = areas.get("legacy", 0) + _peso(ruta)
        elif entrada.startswith("vault"):
            areas["vault"] = areas.get("vault", 0) + _peso(ruta)
        elif entrada in ("maps", "state", "raw", "chats", "tools", "plantillas"):
            areas[entrada] = areas.get(entrada, 0) + _peso(ruta)
        else:
            areas["otros"] = areas.get("otros", 0) + _peso(ruta)

    history = os.path.join(ctx, "maps", "HISTORY")
    archive = os.path.join(ctx, "maps", "archive")
    datos["snapshots_vivos"] = (
        len([n for n in os.listdir(history) if n.endswith(".md")])
        if os.path.isdir(history)
        else 0
    )
    datos["archivos_comprimidos"] = (
        len([n for n in os.listdir(archive) if n.endswith(".tar.gz")])
        if os.path.isdir(archive)
        else 0
    )

    # Separar el historial vivo del archivo comprimido (dentro de maps).
    maps_total = _peso(os.path.join(ctx, "maps"))
    archive_bytes = _peso(archive)
    areas["maps"] = max(maps_total - archive_bytes, 0)
    areas["archive"] = archive_bytes

    datos["areas"] = {k: v for k, v in areas.items() if v}
    datos["total_bytes"] = sum(datos["areas"].values())

    # Comparar con el valor REAL (no el redondeado para mostrar).
    total_mb_real = datos["total_bytes"] / 1048576
    if total_mb_real > TOPE_MB:
        datos["alerta"] = f"el contexto pesa {_mb(datos['total_bytes'])} MB (tope {TOPE_MB:.0f} MB)"
        datos["sugerencia"] = (
            "ejecuta `ctxmap build` (poda y archiva) y revisa `CTXMAP_SNAPSHOT_KEEP`"
        )
    elif datos["snapshots_vivos"] > TOPE_SNAPSHOTS:
        datos["alerta"] = (
            f"hay {datos['snapshots_vivos']} snapshots vivos (tope {TOPE_SNAPSHOTS})"
        )
        datos["sugerencia"] = "baja `CTXMAP_SNAPSHOT_KEEP` o ejecuta `ctxmap build`"
    return datos


def formatear_pesos(datos: dict[str, Any]) -> list[str]:
    """Convierte la medición en líneas legibles para CLI/Markdown.

    Args:
        datos (dict[str, Any]): Resultado de :func:`medir_pesos`.

    Returns:
        list[str]: Líneas con el total, el desglose y la alerta (si la hay).
    """
    if not datos.get("existe"):
        return ["- 📦 Peso del contexto: _(sin `.context-map` en este proyecto)_"]

    lineas = [
        f"- 📦 Peso del contexto: **{_mb(datos['total_bytes'])} MB**"
        f" ({datos['snapshots_vivos']} snapshots vivos,"
        f" {datos['archivos_comprimidos']} archivo(s) comprimido(s))"
    ]
    areas = datos.get("areas", {})
    top = sorted(areas.items(), key=lambda x: -x[1])[:4]
    if top:
        detalle = " · ".join(f"{ETIQUETAS.get(k, k)} {_mb(v)} MB" for k, v in top)
        lineas.append(f"  - _{detalle}_")
    if datos.get("alerta"):
        lineas.append(f"- ⚠️ Peso elevado: {datos['alerta']} — {datos['sugerencia']}")
    return lineas

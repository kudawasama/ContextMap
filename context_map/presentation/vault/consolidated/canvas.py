"""Herramientas visuales de Obsidian para el vault jerárquico.

Genera el mapa mental conectado en las herramientas nativas de Obsidian:
- ``00-MAPA-MENTAL.canvas`` (Lienzo): nodos ``file`` + aristas reales.
- ``.obsidian/graph.json`` (Graph View): grupos de color por estado.
- ``.context-map/plantillas/`` (Plantillas): nota de sesión manual con
  ``preserve: true``.
- ``.context-map/vault-<proj>/7.0-MANUAL/Diario/YYYY-MM-DD.md`` (Nota del día):
  enlaza los nodos ingresados ese día.

Regla de oro: SOLO se referencian archivos que existen (sin nodos fantasma).
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date, datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo


def render_canvas(
    output_dir: str,
    nodes: list[Node],
    edges: list[Edge],
) -> str:
    """Genera ``00-MAPA-MENTAL.canvas`` con el mapa mental conectado.

    Fix 2026-08-11 (Etapa 2 — el lienzo estaba muerto: 55 tarjetas, 0 aristas,
    duplicados). Ahora:
    - Dedup por archivo: una tarjeta por nota (antes había duplicados).
    - Agrupación por sección: columnas por carpeta raíz (1.0, 2.0, ... 8.0).
    - Aristas REALES: edges del grafo + conexiones semánticas derivadas
      (``conexiones_de_nodo``, igual que 00-CONEXIONES.md).

    Args:
        output_dir (str): Directorio raíz del vault.
        nodes (list[Node]): Nodos del mapa.
        edges (list[Edge]): Aristas del mapa.

    Returns:
        str: Ruta del archivo generado.
    """
    from context_map.presentation.vault.consolidated.rutas import (
        conexiones_de_nodo,
        ruta_archivo_nodo,
    )

    # 1. Dedup por archivo: un nodo (y una tarjeta) por ruta real
    ruta_a_nodo: dict[str, Node] = {}
    for n in nodes:
        ruta = ruta_archivo_nodo(n)
        if ruta:
            ruta_a_nodo.setdefault(ruta, n)

    def _columna(ruta: str) -> int:
        """Columna por sección raíz: 1.0→1, 2.0→2, ... 8.0→8; resto→9."""
        seccion = ruta.split("/")[0] if "/" in ruta else ""
        if not seccion or seccion.startswith("adjuntos"):
            return 9
        try:
            return int(seccion.split(".")[0])
        except ValueError:
            return 9

    # 2. Posicionar: columna por sección, fila apilada dentro de la columna
    ids: dict[str, str] = {}          # ruta → uuid
    canvas_nodes: list[dict] = []
    filas_por_col: dict[int, int] = {}
    for ruta in sorted(ruta_a_nodo):
        col = _columna(ruta)
        fila = filas_por_col.get(col, 0)
        filas_por_col[col] = fila + 1
        uid = str(uuid.uuid4())
        ids[ruta] = uid
        canvas_nodes.append({
            "id": uid,
            "type": "file",
            "file": ruta,
            "x": 260 * col,
            "y": 60 * fila,
            "width": 240,
            "height": 50,
        })

    # 3. Aristas: edges reales del grafo + conexiones semánticas derivadas
    pares: set[tuple[str, str]] = set()
    for e in edges:
        r_src = next((r for r, n in ruta_a_nodo.items() if n.id == e.source), None)
        r_dst = next((r for r, n in ruta_a_nodo.items() if n.id == e.target), None)
        if r_src and r_dst and r_src != r_dst:
            pares.add(tuple(sorted((r_src, r_dst))))

    nodos_unicos = list(ruta_a_nodo.values())
    for ruta, n in ruta_a_nodo.items():
        for rel in conexiones_de_nodo(n, nodos_unicos, limite=3):
            r_rel = ruta_archivo_nodo(rel)
            if r_rel and r_rel != ruta and r_rel in ids:
                pares.add(tuple(sorted((ruta, r_rel))))

    canvas_edges: list[dict] = []
    for r_src, r_dst in sorted(pares):
        canvas_edges.append({
            "id": str(uuid.uuid4()),
            "fromNode": ids[r_src],
            "fromSide": "right",
            "toNode": ids[r_dst],
            "toSide": "left",
            "label": "",
        })

    payload = {"nodes": canvas_nodes, "edges": canvas_edges}
    ruta_canvas = os.path.join(output_dir, "00-MAPA-MENTAL.canvas")
    with open(ruta_canvas, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return ruta_canvas


def render_graph_json(output_dir: str, nodes: list[Node]) -> str:
    """Genera ``.obsidian/graph.json`` con grupos de color por estado.

    Args:
        output_dir (str): Directorio raíz del vault.
        nodes (list[Node]): Nodos del mapa (no se usa en el layout actual).

    Returns:
        str: Ruta del archivo generado.
    """
    grupos = [
        {"query": "path:2.1-Ideas-Pendientes", "color": {"a": 1, "rgb": 0xEAB308}},
        {"query": "path:2.2-Ideas-Futuras", "color": {"a": 1, "rgb": 0x3B82F6}},
        {"query": "path:2.3-Ideas-Completas", "color": {"a": 1, "rgb": 0x22C55E}},
        {"query": "path:4.0-RIESGOS", "color": {"a": 1, "rgb": 0xEF4444}},
        {"query": "path:3.0-ESTRUCTURA", "color": {"a": 1, "rgb": 0xA855F7}},
    ]
    conf = {
        "collapse-filter": True,
        "search": "",
        "showTags": False,
        "showAttachment": False,
        "hideUnresolved": True,
        "groups": grupos,
    }
    obs_dir = os.path.join(output_dir, ".obsidian")
    os.makedirs(obs_dir, exist_ok=True)
    ruta = os.path.join(obs_dir, "graph.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
    return ruta


def render_plantillas(output_dir: str, project_name: str) -> str:
    """Genera la plantilla de nota de sesión en ``.context-map/plantillas/``.

    Args:
        output_dir (str): Directorio raíz del proyecto (donde vive .context-map).
        project_name (str): Nombre del proyecto.

    Returns:
        str: Ruta de la plantilla generada.
    """
    ruta = os.path.join(output_dir, ".context-map", "plantillas", "nota-sesion.md")
    # Fix CI (2026-08-12): si el directorio base no es escribible (p. ej. la
    # raíz del sistema al renderizar en un temp dir de 2 niveles), las
    # plantillas se omiten — son un extra opcional del vault.
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
    except OSError as err:
        logging.getLogger(__name__).warning("No se pudieron crear plantillas en %s: %s", output_dir, err)
        return ""
    contenido = """---
type: nota-manual
preserve: true
created: {{fecha}}
project: "{{proyecto}}"
tags: [sesion, manual]
---
# Sesión — {{fecha}}

## ¿Qué se hizo?

## Decisiones

## Pendiente
"""
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return ruta


def render_nota_dia(output_dir: str, project_name: str, nodes: list[Node]) -> str | None:
    """Genera la nota del día (Diario) con los nodos ingresados hoy.

    Escribe en la zona protegida ``.manual/Diario/YYYY-MM-DD.md`` con wikilinks
    a los nodos cuyo ``created_at`` coincide con la fecha de hoy.

    Args:
        output_dir (str): Directorio raíz del proyecto.
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Nodos del mapa.

    Returns:
        str | None: Ruta de la nota generada, o None si no hay nodos de hoy.
    """
    safe = project_name.strip().replace(" ", "-").replace("/", "-")
    hoy = date.today().isoformat()
    ingresados = [n for n in nodes if (n.created_at or "")[:10] == hoy]

    if not ingresados:
        return None

    diario_dir = os.path.join(
        output_dir, ".context-map", f"vault-{safe}", "7.0-MANUAL", "Diario",
    )
    os.makedirs(diario_dir, exist_ok=True)
    ruta = os.path.join(diario_dir, f"{hoy}.md")

    partes = [
        "---",
        "type: nota-dia",
        "preserve: true",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        f'project: "{project_name}"',
        "tags: [diario, manual]",
        "---",
        "",
        f"# Diario — {hoy}",
        "",
        f"Nodos ingresados hoy: **{len(ingresados)}**",
        "",
        "## 📌 Ingresados hoy",
        "",
    ]
    for n in ingresados:
        ruta_nodo = ruta_archivo_nodo(n)
        if ruta_nodo:
            partes.append(f"- [[{ruta_nodo}|{n.title[:60]}]]")
        else:
            partes.append(f"- **{n.title[:60]}**")
    partes.append("")

    # Memoria viva: si la nota del día ya existe con preserve: true (escrita
    # por el AGENTE con alma), NO la sobrescribimos — solo añadimos los nodos
    # nuevos del scanner que falten, en una sección aparte.
    if os.path.exists(ruta):
        try:
            with open(ruta, encoding="utf-8") as f:
                existente = f.read()
            if "preserve: true" in existente:
                faltantes = [
                    n for n in ingresados
                    if (n.title or "")[:60] not in existente
                ]
                if faltantes:
                    anexo = [
                        "",
                        "## 🤖 Ingresados por el scanner (autogenerado)",
                        "",
                    ]
                    for n in faltantes:
                        anexo.append(f"- **{n.title[:60]}**")
                    anexo.append("")
                    with open(ruta, "a", encoding="utf-8") as f:
                        f.write("\n".join(anexo))
                return ruta
        except Exception:
            pass  # si no se puede leer, regenerar normal

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    return ruta

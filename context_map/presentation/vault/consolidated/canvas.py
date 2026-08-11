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

    Args:
        output_dir (str): Directorio raíz del vault.
        nodes (list[Node]): Nodos del mapa.
        edges (list[Edge]): Aristas del mapa.

    Returns:
        str: Ruta del archivo generado.
    """
    ids: dict[str, str] = {}
    canvas_nodes: list[dict] = []
    idx = 0
    for n in nodes:
        ruta = ruta_archivo_nodo(n)
        if not ruta:
            continue
        uid = str(uuid.uuid4())
        ids[n.id] = uid
        canvas_nodes.append({
            "id": uid,
            "type": "file",
            "file": ruta,
            "x": 220 * (idx % 6),
            "y": 180 * (idx // 6),
            "width": 260,
            "height": 60,
        })
        idx += 1

    canvas_edges: list[dict] = []
    for e in edges:
        if e.source in ids and e.target in ids:
            canvas_edges.append({
                "id": str(uuid.uuid4()),
                "fromNode": ids[e.source],
                "fromSide": "right",
                "toNode": ids[e.target],
                "toSide": "left",
                "label": e.kind,
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
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
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

"""Configuración de Obsidian para el mundo conocimiento (F5).

Siembra dentro del vault la configuración recomendada del mundo PKM:

- ``.obsidian/community-plugins.json`` — plugins de comunidad recomendados
  (Calendar, Kanban, Tasks, Dataview, Templater, Web Clipper, Obsidian Git,
  Remotely Save, Periodic Notes).
- ``.obsidian/core-plugins.json`` — plugins núcleo (incluye Daily Notes y
  Templates).
- ``.obsidian/daily-notes.json`` — la nota del día se crea en el inbox PKM.
- ``templates/nota-pkm.md`` — plantilla de nota de conocimiento.

Es **idempotente**: solo escribe si el archivo no existe. Como ``.obsidian``
ahora es zona preservada (``ZONAS_MANUALES``), la config del usuario sobrevive
a cada build y este módulo solo completa lo que falta.
"""

from __future__ import annotations

import json
import os

# Plugins de comunidad recomendados (se activan al instalarlos en Obsidian).
PLUGINS_COMUNIDAD: list[str] = [
    "calendar",
    "obsidian-kanban",
    "obsidian-tasks-plugin",
    "dataview",
    "templater-obsidian",
    "obsidian-web-clipper",
    "obsidian-git",
    "remotely-save",
    "periodic-notes",
]

# Plugins núcleo activos (Daily Notes + Templates para el flujo PKM).
CORE_PLUGINS: list[str] = [
    "file-explorer", "global-search", "switcher", "graph", "backlink",
    "outgoing-link", "tag-pane", "page-preview", "templates", "daily-notes",
    "command-palette", "outline", "word-count", "file-recovery", "canvas",
]

PLANTILLA_PKM: str = """---
type: nota
namespace: knowledge
preserve: true
title: "{{title}}"
source: ""
status: inbox
tags: [knowledge, inbox]
---

# {{title}}


---
[[90-CONOCIMIENTO/00-INBOX/00-INBOX|⬅ Volver a 00-INBOX]]
"""


def _escribir_si_falta(ruta: str, contenido: str) -> bool:
    """Escribe contenido solo si la ruta no existe (idempotente)."""
    if os.path.exists(ruta):
        return False
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)
    return True


def sembrar_config_obsidian(output_dir: str) -> list[str]:
    """Crea la configuración Obsidian recomendada del mundo PKM (idempotente).

    Solo escribe archivos que no existan: no pisa la config real del usuario.

    Args:
        output_dir (str): Directorio raíz del vault Obsidian.

    Returns:
        list[str]: Rutas relativas de los archivos creados.
    """
    obsidian_dir = os.path.join(output_dir, ".obsidian")
    os.makedirs(obsidian_dir, exist_ok=True)

    destino_contenido: dict[str, str] = {
        os.path.join(obsidian_dir, "community-plugins.json"): (
            json.dumps(PLUGINS_COMUNIDAD, ensure_ascii=False, indent=2) + "\n"
        ),
        os.path.join(obsidian_dir, "core-plugins.json"): (
            json.dumps(CORE_PLUGINS, ensure_ascii=False, indent=2) + "\n"
        ),
        os.path.join(obsidian_dir, "daily-notes.json"): (
            json.dumps({
                "folder": "90-CONOCIMIENTO/00-INBOX",
                "format": "YYYY-MM-DD",
                "template": "templates/nota-pkm",
            }, ensure_ascii=False, indent=2)
            + "\n"
        ),
        os.path.join(output_dir, "templates", "nota-pkm.md"): PLANTILLA_PKM,
    }

    creados: list[str] = []
    for ruta, contenido in destino_contenido.items():
        if _escribir_si_falta(ruta, contenido):
            creados.append(os.path.relpath(ruta, output_dir))
    return creados

"""Tests de la configuración Obsidian del mundo conocimiento (F5)."""

from __future__ import annotations

import json
import os

from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento
from context_map.presentation.vault.consolidated.obsidian_config import (
    PLANTILLA_PKM,
    PLUGINS_COMUNIDAD,
    sembrar_config_obsidian,
)


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM y devuelve su ruta."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def _leer(ruta: str) -> str:
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def test_siembra_config_obsidian(tmp_path):
    """Se crean los archivos de configuración del mundo PKM."""
    vdir = _vault(tmp_path)
    creados = sembrar_config_obsidian(vdir)
    norm = [c.replace("\\", "/") for c in creados]
    assert "templates/nota-pkm.md" in norm

    obs = os.path.join(vdir, ".obsidian")
    plugins = json.loads(_leer(os.path.join(obs, "community-plugins.json")))
    assert plugins == PLUGINS_COMUNIDAD
    assert "dataview" in plugins and "templater-obsidian" in plugins

    daily = json.loads(_leer(os.path.join(obs, "daily-notes.json")))
    assert daily["folder"] == "90-CONOCIMIENTO/00-INBOX"
    assert daily["template"] == "templates/nota-pkm"

    plantilla = _leer(os.path.join(vdir, "templates", "nota-pkm.md"))
    assert plantilla == PLANTILLA_PKM
    assert "namespace: knowledge" in plantilla


def test_no_sobrescribe_config_existente(tmp_path):
    """Si el usuario ya configuró Obsidian, no se pisa nada (idempotente)."""
    vdir = _vault(tmp_path)
    obs = os.path.join(vdir, ".obsidian")
    os.makedirs(obs, exist_ok=True)
    with open(os.path.join(obs, "community-plugins.json"), "w", encoding="utf-8") as f:
        f.write('["mi-plugin-1"]')

    sembrar_config_obsidian(vdir)
    assert json.loads(_leer(os.path.join(obs, "community-plugins.json"))) == ["mi-plugin-1"]
    # Lo que faltaba sí se completa
    assert os.path.exists(os.path.join(vdir, "templates", "nota-pkm.md"))


def test_obsidian_es_zona_preservada():
    """El build preserva .obsidian para no perder la config del usuario."""
    from context_map.presentation.vault.preservar import ZONAS_MANUALES

    assert ".obsidian" in ZONAS_MANUALES

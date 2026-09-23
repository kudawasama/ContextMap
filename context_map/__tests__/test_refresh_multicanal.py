"""Tests unitarios para el ciclo de auto-importación multicanal en cmd_refresh.

Valida la integración y tolerancia de fallos al procesar:
- Sesiones de Hermes
- Sesiones de Antigravity IDE
- Chats externos (.context-map/chats/)
- Documentos de referencia (.context-map/raw/docs/)
"""

from __future__ import annotations

import os
import types
from unittest.mock import patch

from context_map.application.commands.refresh import cmd_refresh


def test_refresh_multicanal_orquestacion(tmp_path, monkeypatch):
    """Verifica que refresh ejecute todos los canales de memoria viva e ingesta."""
    monkeypatch.chdir(tmp_path)
    os.makedirs(os.path.join(".context-map", "raw", "docs"), exist_ok=True)
    os.makedirs(os.path.join(".context-map", "chats"), exist_ok=True)

    # Crear documento de prueba en raw/docs
    doc_path = os.path.join(".context-map", "raw", "docs", "guia.md")
    with open(doc_path, "w", encoding="utf-8") as f:
        f.write("# Guía de Arquitectura\n\nEsta es una guía de inversión y arquitectura modular para el sistema.")

    # Crear chat de prueba en chats/
    chat_path = os.path.join(".context-map", "chats", "chat_user.txt")
    with open(chat_path, "w", encoding="utf-8") as f:
        f.write("Alice: Decidimos usar Clean Architecture para el núcleo.\nBob: De acuerdo.\n")

    args = types.SimpleNamespace(
        target=".",
        project="TestProject",
        quiet=True,
        mode="hierarchical",
    )

    with (
        patch("context_map.application.commands.refresh.cmd_scan") as mock_scan,
        patch("context_map.application.commands.refresh.cmd_build") as mock_build,
        patch("context_map.application.commands.refresh.cmd_check") as mock_check,
        patch("context_map.infrastructure.integrations.hermes.importar_sesiones", return_value=2) as mock_hermes,
        patch("context_map.infrastructure.integrations.antigravity.importar_antigravity", return_value=3) as mock_ag,
    ):
        cmd_refresh(args)

        # Validar llamadas a escaneo, construcción y diagnóstico
        assert mock_scan.called
        assert mock_build.called
        assert mock_check.called

        # Validar llamadas a importadores
        assert mock_hermes.called
        assert mock_ag.called

        # Verificar que el chat fue procesado en events.jsonl
        events_file = os.path.join(".context-map", "raw", "events.jsonl")
        assert os.path.exists(events_file)
        with open(events_file, encoding="utf-8") as f:
            contenido_events = f.read()
            assert "Alice" in contenido_events

        # Verificar que el documento fue agregado al grafo
        graph_file = os.path.join(".context-map", "state", "graph.jsonl")
        assert os.path.exists(graph_file)
        with open(graph_file, encoding="utf-8") as f:
            contenido_graph = f.read()
            assert "guia" in contenido_graph.lower()


def test_refresh_multicanal_tolerancia_fallos(tmp_path, monkeypatch):
    """Verifica que fallos en un canal de importación no aborten el ciclo de refresh."""
    monkeypatch.chdir(tmp_path)

    args = types.SimpleNamespace(
        target=".",
        project="TestProject",
        quiet=True,
        mode="hierarchical",
    )

    with (
        patch("context_map.application.commands.refresh.cmd_scan") as mock_scan,
        patch("context_map.application.commands.refresh.cmd_build") as mock_build,
        patch("context_map.application.commands.refresh.cmd_check") as mock_check,
        patch(
            "context_map.infrastructure.integrations.hermes.importar_sesiones",
            side_effect=RuntimeError("Error simulado en Hermes"),
        ),
        patch(
            "context_map.infrastructure.integrations.antigravity.importar_antigravity",
            side_effect=RuntimeError("Error simulado en Antigravity"),
        ),
    ):
        # cmd_refresh no debe lanzar excepción
        cmd_refresh(args)

        assert mock_scan.called
        assert mock_build.called
        assert mock_check.called

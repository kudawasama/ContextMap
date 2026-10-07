"""Regresión: `build` sin eventos nuevos no debe fallar.

Bug encontrado en la prueba end-to-end (2026-10-07): `estandarizar_nodo` se
importaba dentro de ``if extra_events:`` pero se usaba fuera de ese bloque, así
que un build sin eventos nuevos lanzaba ``UnboundLocalError``.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile


def test_build_sin_eventos_nuevos_no_falla() -> None:
    """Con graph.jsonl existente y sin eventos nuevos, `build` completa y genera el brief."""
    from context_map.application.commands.build import cmd_build

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_build_vacio_")
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        state = os.path.join(temp_dir, ".context-map", "state")
        os.makedirs(state)
        with open(os.path.join(state, "graph.jsonl"), "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "id": "b1", "type": "BASE", "title": "Núcleo del sistema",
                "summary": "Componente central", "source": "test",
            }) + "\n")

        class Args:
            target = "."
            project = "SinEventos"
            clean = False
            brief = True
            quiet = True
            mode = "hierarchical"
            raw = False

        cmd_build(Args())

        assert os.path.exists(os.path.join(temp_dir, ".context-map", "CONTEXT.md"))
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)

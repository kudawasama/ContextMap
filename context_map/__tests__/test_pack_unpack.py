"""Tests unitarios para el empaquetado y desempaquetado de contexto (.ctxpack)."""

from __future__ import annotations

import os

from context_map.domain.storage.packer import (
    crear_paquete_contexto,
    desempaquetar_contexto,
)


def test_pack_y_unpack_flujo_completo(tmp_path):
    """Verifica la creación y extracción completa de un archivo .ctxpack."""
    # 1. Crear estructura simulada .context-map/
    src_dir = tmp_path / "proyecto_origen"
    ctx_dir = src_dir / ".context-map"
    state_dir = ctx_dir / "state"
    state_dir.mkdir(parents=True)

    graph_file = state_dir / "graph.jsonl"
    graph_file.write_text(
        '{"id": "idea_1", "type": "IDEA", "title": "Idea 1"}\n'
        '{"id": "base_1", "type": "BASE", "title": "Base 1"}\n',
        encoding="utf-8",
    )

    brief_file = ctx_dir / "CONTEXT.md"
    brief_file.write_text("# Brief de Contexto", encoding="utf-8")

    agents_file = src_dir / "AGENTS.md"
    agents_file.write_text("# Reglas Agénticas", encoding="utf-8")

    # 2. Empaquetar
    out_file = tmp_path / "backup.ctxpack"
    ruta_gen, size, manifest = crear_paquete_contexto(
        target_dir=str(src_dir),
        output_path=str(out_file),
        project_name="ProyectoPrueba",
    )

    assert os.path.isfile(ruta_gen)
    assert size > 0
    assert manifest["project"] == "ProyectoPrueba"
    assert manifest["node_count"] == 2

    # 3. Desempaquetar en directorio destino
    dst_dir = tmp_path / "proyecto_destino"
    res_manifest = desempaquetar_contexto(
        archive_path=str(out_file),
        target_dir=str(dst_dir),
    )

    assert res_manifest["project"] == "ProyectoPrueba"
    assert (dst_dir / ".context-map" / "state" / "graph.jsonl").exists()
    assert (dst_dir / ".context-map" / "CONTEXT.md").exists()
    assert (dst_dir / "AGENTS.md").exists()

    content = (dst_dir / ".context-map" / "state" / "graph.jsonl").read_text(encoding="utf-8")
    assert "idea_1" in content
    assert "base_1" in content

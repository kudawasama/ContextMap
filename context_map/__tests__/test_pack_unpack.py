"""Tests unitarios para el empaquetado y desempaquetado de contexto (.ctxpack)."""

from __future__ import annotations

import io
import os
import tarfile

import pytest

from context_map.domain.storage.packer import (
    _sha256_archivo,
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


def test_manifest_incluye_checksums_sha256(tmp_path):
    """Verifica que el manifiesto registra un checksum SHA-256 por archivo."""
    src_dir = tmp_path / "origen"
    state_dir = src_dir / ".context-map" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "graph.jsonl").write_text("hola\n", encoding="utf-8")

    out_file = tmp_path / "backup.ctxpack"
    _, _, manifest = crear_paquete_contexto(str(src_dir), str(out_file), project_name="Checksums")

    ruta_rel = os.path.join(".context-map", "state", "graph.jsonl")
    assert ruta_rel in manifest["files"]
    assert manifest["files"][ruta_rel] == _sha256_archivo(str(state_dir / "graph.jsonl"))


def test_unpack_detecta_integridad_comprometida(tmp_path):
    """Verifica que un paquete con contenido alterado se rechaza por checksum."""
    src_dir = tmp_path / "origen"
    state_dir = src_dir / ".context-map" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "graph.jsonl").write_text('{"id": "a", "type": "IDEA"}\n', encoding="utf-8")

    out_file = tmp_path / "backup.ctxpack"
    crear_paquete_contexto(str(src_dir), str(out_file), project_name="Integridad")

    # Reescribir el tar alterando graph.jsonl sin actualizar el manifiesto
    tampered = tmp_path / "tampered.ctxpack"
    with tarfile.open(str(out_file), "r:gz") as tar, tarfile.open(str(tampered), "w:gz") as out:
        for m in tar.getmembers():
            f = tar.extractfile(m)
            contenido = f.read() if f else b""
            if m.name == ".context-map/state/graph.jsonl":
                contenido = b'{"id": "ALTERADO_TAMPERED"}\n'
            ti = tarfile.TarInfo(m.name)
            ti.size = len(contenido)
            ti.mode = m.mode
            out.addfile(ti, io.BytesIO(contenido))

    with pytest.raises(ValueError, match="Integridad"):
        desempaquetar_contexto(str(tampered), str(tmp_path / "destino"))


def _crear_tar_con_symlink(path: str) -> None:
    """Crea un .ctxpack malicioso con un symlink apuntando fuera del destino."""
    with tarfile.open(path, "w:gz") as tar:
        data = b"contenido"
        ti = tarfile.TarInfo(".context-map/state/graph.jsonl")
        ti.size = len(data)
        tar.addfile(ti, io.BytesIO(data))

        # Symlink malicioso que apunta fuera del directorio destino
        sl = tarfile.TarInfo("escape")
        sl.type = tarfile.SYMTYPE
        sl.linkname = "/tmp/ctxmap_escape_target"
        tar.addfile(sl)


def test_unpack_rechaza_symlinks(tmp_path):
    """Verifica que un .ctxpack con symlinks no los extrae (hardening)."""
    archivo = tmp_path / "malicioso.ctxpack"
    _crear_tar_con_symlink(str(archivo))

    destino = tmp_path / "destino"
    desempaquetar_contexto(str(archivo), str(destino))

    assert (destino / ".context-map" / "state" / "graph.jsonl").exists()
    assert not (destino / "escape").exists()  # el symlink no se extrae

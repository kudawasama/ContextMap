"""Módulo de empaquetado y desempaquetado de contexto portátil (.ctxpack).

Permite comprimir la memoria viva completa de un proyecto (.context-map/)
en un archivo único transportable y restaurarlo 100% offline en cualquier máquina.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tarfile
from contextlib import suppress
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


def _sha256_archivo(path: str) -> str:
    """Calcula el hash SHA-256 de un archivo leyéndolo por chunks.

    Args:
        path: Ruta absoluta del archivo.

    Returns:
        str: Hash hexadecimal de 64 caracteres.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def crear_paquete_contexto(
    target_dir: str = ".",
    output_path: str | None = None,
    project_name: str | None = None,
) -> tuple[str, int, dict[str, Any]]:
    """Empaqueta la estructura .context-map/ del proyecto en un archivo .ctxpack.

    Args:
        target_dir: Directorio raíz del proyecto.
        output_path: Ruta del archivo de salida .ctxpack (opcional).
        project_name: Nombre descriptivo del proyecto (opcional).

    Returns:
        Tuple[str, int, Dict[str, Any]]: (Ruta del archivo generado, Tamaño en bytes, Manifiesto).
    """
    abs_target = os.path.abspath(target_dir)
    context_dir = os.path.join(abs_target, ".context-map")

    if not os.path.isdir(context_dir):
        raise FileNotFoundError(f"No existe el directorio de contexto '.context-map' en {target_dir}")

    proj = project_name or os.path.basename(abs_target) or "Proyecto"
    if not output_path:
        safe_name = proj.strip().replace(" ", "-").replace("/", "-").replace("\\", "-")
        output_path = os.path.join(abs_target, f"{safe_name}.ctxpack")

    if not output_path.endswith(".ctxpack"):
        output_path += ".ctxpack"

    # Contar nodos si existe graph.jsonl
    total_nodos = 0
    graph_jsonl = os.path.join(context_dir, "state", "graph.jsonl")
    if os.path.isfile(graph_jsonl):
        try:
            with open(graph_jsonl, encoding="utf-8") as f:
                total_nodos = sum(1 for line in f if line.strip())
        except Exception:
            pass

    # Recolectar archivos y calcular checksums SHA-256 ANTES de escribir el
    # manifiesto (así pack_manifest.json no se hashea a sí mismo).
    archivos_empaquetar: list[tuple[str, str]] = []  # (ruta_absoluta, arcname)
    hashes: dict[str, str] = {}
    for raiz, _, archivos in os.walk(context_dir):
        for f in archivos:
            full_p = os.path.join(raiz, f)
            rel_p = os.path.relpath(full_p, abs_target)
            archivos_empaquetar.append((full_p, rel_p))
            hashes[rel_p] = _sha256_archivo(full_p)

    # Incluir CONTEXT.md si existe en la raíz de .context-map
    brief_p = os.path.join(abs_target, ".context-map", "CONTEXT.md")
    if os.path.isfile(brief_p):
        arc_brief = os.path.join(".context-map", "CONTEXT.md")
        archivos_empaquetar.append((brief_p, arc_brief))
        hashes[arc_brief] = _sha256_archivo(brief_p)

    # Incluir AGENTS.md si existe en la raíz del proyecto
    agents_p = os.path.join(abs_target, "AGENTS.md")
    if os.path.isfile(agents_p):
        archivos_empaquetar.append((agents_p, "AGENTS.md"))
        hashes["AGENTS.md"] = _sha256_archivo(agents_p)

    manifest = {
        "format": "ctxpack-v1",
        "project": proj,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "node_count": total_nodos,
        "generator": "ContextMap-v2.2.1",
        "files": hashes,
    }

    # Escribir manifiesto temporal en .context-map/pack_manifest.json
    manifest_path = os.path.join(context_dir, "pack_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    try:
        with tarfile.open(output_path, "w:gz") as tar:
            for full_p, rel_p in archivos_empaquetar:
                tar.add(full_p, arcname=rel_p)

            # Incluir el manifiesto (no se hashea a sí mismo; su checksum no
            # puede estar dentro de sí mismo por definición)
            tar.add(manifest_path, arcname=os.path.join(".context-map", "pack_manifest.json"))

    finally:
        if os.path.isfile(manifest_path):
            with suppress(Exception):
                os.remove(manifest_path)

    tamanio = os.path.getsize(output_path)
    return output_path, tamanio, manifest


def desempaquetar_contexto(
    archive_path: str,
    target_dir: str = ".",
) -> dict[str, Any]:
    """Desempaqueta un archivo .ctxpack en el directorio destino.

    Args:
        archive_path: Ruta del archivo .ctxpack.
        target_dir: Directorio donde se restaurará el contexto.

    Returns:
        Dict[str, Any]: Manifiesto del paquete restaurado.
    """
    if not os.path.isfile(archive_path):
        raise FileNotFoundError(f"No se encontró el archivo de paquete: {archive_path}")

    abs_target = os.path.abspath(target_dir)
    os.makedirs(abs_target, exist_ok=True)

    manifest: dict[str, Any] = {}

    with tarfile.open(archive_path, "r:gz") as tar:
        # Intentar leer pack_manifest.json
        try:
            member = tar.getmember(".context-map/pack_manifest.json")
            f = tar.extractfile(member)
            if f:
                manifest = json.loads(f.read().decode("utf-8"))
        except Exception:
            manifest = {"format": "ctxpack-v1", "project": "Desconocido"}

        # Extraer todos los miembros de forma segura
        archivo_hashes = manifest.get("files") if isinstance(manifest.get("files"), dict) else None
        for member in tar.getmembers():
            # Evitar Path Traversal de seguridad
            norm_name = os.path.normpath(member.name)
            if norm_name.startswith("..") or os.path.isabs(norm_name):
                continue
            # Evitar symlinks, hardlinks y ficheros especiales (FIFO/device):
            # una entrada maliciosa podría escribir fuera del destino o colgar
            # el proceso (ej. FIFO).
            if member.issym() or member.islnk() or member.isdev():
                continue
            tar.extract(member, path=abs_target)
            # Verificar integridad contra los checksums del manifiesto
            if member.isfile() and archivo_hashes and norm_name in archivo_hashes:
                destino = os.path.join(abs_target, norm_name)
                if os.path.isfile(destino) and _sha256_archivo(destino) != archivo_hashes[norm_name]:
                    raise ValueError(f"Integridad del paquete comprometida en: {member.name}")

    # Limpiar manifiesto extraído de .context-map/ si quedó en disco
    extracted_manifest = os.path.join(abs_target, ".context-map", "pack_manifest.json")
    if os.path.isfile(extracted_manifest):
        with suppress(Exception):
            os.remove(extracted_manifest)

    return manifest

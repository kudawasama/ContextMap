"""Módulo de empaquetado y desempaquetado de contexto portátil (.ctxpack).

Permite comprimir la memoria viva completa de un proyecto (.context-map/)
en un archivo único transportable y restaurarlo 100% offline en cualquier máquina.
"""

from __future__ import annotations

import json
import logging
import os
import tarfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def crear_paquete_contexto(
    target_dir: str = ".",
    output_path: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Tuple[str, int, Dict[str, Any]]:
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
            with open(graph_jsonl, "r", encoding="utf-8") as f:
                total_nodos = sum(1 for line in f if line.strip())
        except Exception:
            pass

    manifest = {
        "format": "ctxpack-v1",
        "project": proj,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "node_count": total_nodos,
        "generator": "ContextMap-v2.2.0",
    }

    # Escribir manifiesto temporal en .context-map/pack_manifest.json
    manifest_path = os.path.join(context_dir, "pack_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    try:
        with tarfile.open(output_path, "w:gz") as tar:
            for raiz, _, archivos in os.walk(context_dir):
                for f in archivos:
                    full_p = os.path.join(raiz, f)
                    rel_p = os.path.relpath(full_p, abs_target)
                    tar.add(full_p, arcname=rel_p)

            # Incluir CONTEXT.md si existe en la raíz de .context-map
            brief_p = os.path.join(abs_target, ".context-map", "CONTEXT.md")
            if os.path.isfile(brief_p):
                tar.add(brief_p, arcname=os.path.join(".context-map", "CONTEXT.md"))

            # Incluir AGENTS.md si existe en la raíz del proyecto
            agents_p = os.path.join(abs_target, "AGENTS.md")
            if os.path.isfile(agents_p):
                tar.add(agents_p, arcname="AGENTS.md")

    finally:
        if os.path.isfile(manifest_path):
            try:
                os.remove(manifest_path)
            except Exception:
                pass

    tamanio = os.path.getsize(output_path)
    return output_path, tamanio, manifest


def desempaquetar_contexto(
    archive_path: str,
    target_dir: str = ".",
) -> Dict[str, Any]:
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

    manifest: Dict[str, Any] = {}

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
        for member in tar.getmembers():
            # Evitar Path Traversal de seguridad
            norm_name = os.path.normpath(member.name)
            if norm_name.startswith("..") or os.path.isabs(norm_name):
                continue
            tar.extract(member, path=abs_target)

    # Limpiar manifiesto extraído de .context-map/ si quedó en disco
    extracted_manifest = os.path.join(abs_target, ".context-map", "pack_manifest.json")
    if os.path.isfile(extracted_manifest):
        try:
            os.remove(extracted_manifest)
        except Exception:
            pass

    return manifest

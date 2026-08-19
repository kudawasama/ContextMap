"""Comandos CLI pack y unpack: empaquetado y desempaquetado de contexto portátil.

Permite comprimir la estructura .context-map/ en un archivo .ctxpack
y restaurarlo 100% offline en cualquier equipo.
"""

from __future__ import annotations

import os

from context_map.domain.storage.packer import (
    crear_paquete_contexto,
    desempaquetar_contexto,
)


def cmd_pack(args) -> None:
    """Ejecuta el empaquetado de contexto en un archivo .ctxpack.

    Args:
        args: Namespace de argparse con atributos ``target`` y ``output``.
    """
    target = getattr(args, "target", ".") or "."
    output = getattr(args, "output", None)
    quiet = getattr(args, "quiet", False)

    try:
        ruta_salida, tamanio, manifest = crear_paquete_contexto(
            target_dir=target,
            output_path=output,
        )
        if not quiet:
            kb = tamanio / 1024.0
            print(f"🗜️ [pack] Contexto empaquetado exitosamente en: {ruta_salida} ({kb:.1f} KB)")
            print(f"   · Proyecto: {manifest.get('project')} | Nodos: {manifest.get('node_count')} | Formato: {manifest.get('format')}")
    except Exception as err:
        if not quiet:
            print(f"❌ [pack] Error al empaquetar contexto: {err}")
        raise


def cmd_unpack(args) -> None:
    """Ejecuta el desempaquetado de un archivo .ctxpack.

    Args:
        args: Namespace de argparse con atributos ``archive`` y ``target``.
    """
    archive = getattr(args, "archive", None)
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)

    if not archive:
        if not quiet:
            print("❌ [unpack] Debe especificar la ruta del archivo .ctxpack")
        return

    try:
        manifest = desempaquetar_contexto(
            archive_path=archive,
            target_dir=target,
        )
        if not quiet:
            print(f"📦 [unpack] Contexto desempaquetado exitosamente en: {os.path.abspath(target)}")
            print(f"   · Proyecto: {manifest.get('project', 'Restaurado')} | Nodos: {manifest.get('node_count', 0)} | Generado: {manifest.get('timestamp', 'N/A')}")
    except Exception as err:
        if not quiet:
            print(f"❌ [unpack] Error al desempaquetar contexto: {err}")
        raise

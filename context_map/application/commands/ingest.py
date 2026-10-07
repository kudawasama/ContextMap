"""Comando ingest: ingiere documentos externos al mapa de contexto.

Convierte archivos brutos (MD, TXT, PDF) en nodos ``DOCUMENTO`` con
síntesis y citas, los persiste en el estado y reconstruye el vault
(sección 3.2-DOCUMENTOS) respetando la topología estricta en árbol.
"""

from __future__ import annotations

import os

from context_map.application.commands._helpers import (
    STATE_DIR,
    append_nodes_edges,
    ensure_dirs,
    project_name,
    vault_dir,
)
from context_map.core.models import Node
from context_map.core.storage import load_jsonl
from context_map.domain.ingestion import crear_nodo_documento, extraer_texto

EXTENSIONES_SOPORTADAS: tuple[str, ...] = (
    ".md", ".markdown", ".txt", ".text", ".pdf", ".html", ".htm", ".docx",
)


def _recolectar_archivos(target: str) -> list[str]:
    """Recolecta archivos soportados desde un archivo o directorio.

    Args:
        target (str): Ruta a un archivo o directorio.

    Returns:
        list[str]: Rutas de documentos a ingerir.

    Raises:
        ValueError: Si el target no existe o no hay archivos soportados.
    """
    if not os.path.exists(target):
        raise ValueError(f"La ruta no existe: {target}")

    if os.path.isfile(target):
        return [target]

    archivos: list[str] = []
    for root, _dirs, files in os.walk(target):
        for f in sorted(files):
            if f.endswith(EXTENSIONES_SOPORTADAS):
                archivos.append(os.path.join(root, f))
    if not archivos:
        raise ValueError(
            f"No se encontraron archivos soportados ({', '.join(EXTENSIONES_SOPORTADAS)}) en {target}"
        )
    return archivos


def _existe_titulo(titulo: str, nodos_existentes: list[Node]) -> bool:
    """Verifica si ya existe un nodo con el mismo título (dedup)."""
    return any(
        n.title.strip().lower() == titulo.strip().lower()
        for n in nodos_existentes
    )


def _cmd_captura_fuente(args, fuente: str, es_youtube: bool) -> None:
    """Captura una URL o transcripción de YouTube al mundo conocimiento (PKM).

    Args:
        args: Namespace de argparse (``--titulo``, ``--destino``, ``--entidades``).
        fuente (str): URL o video de YouTube a capturar.
        es_youtube (bool): True si es transcripción de YouTube.
    """
    import types

    from context_map.domain.knowledge import captura as cap

    proj_args = types.SimpleNamespace(
        cmd="ingest", target=".", project=getattr(args, "project", "Repo"),
    )
    proj = project_name(proj_args)
    vdir = vault_dir(proj)
    destino = getattr(args, "destino", "inbox") or "inbox"
    entidades = getattr(args, "entidades", "") or ""
    titulo = getattr(args, "titulo", "") or ""

    try:
        if es_youtube:
            titulo_final, texto = cap.descargar_transcripcion_youtube(fuente, titulo or None)
            total = len(texto.split())
            res = cap.capturar(vdir, texto, titulo_final, fuente, destino, entidades)
        else:
            res = cap.capturar_desde_url(vdir, fuente, titulo, destino, entidades)
            total = -1
        print(f"[ingest] 📥 Captura a {res['destino']}: {res['ruta']}")
        if total >= 0:
            print(f"[ingest]   transcripción: {total} palabras")
        if res.get("entidades"):
            print(f"[ingest]   entidades wiki: {res['entidades']}")
    except Exception as err:  # noqa: BLE001 — informar sin romper el CLI
        print(f"[ingest] ✗ Captura fallida: {err}")


def cmd_ingest(args) -> None:
    """Ejecuta la ingesta de documentos externos.

    Si se pasa ``--url`` o ``--youtube`` deriva a la captura PKM (mundo
    conocimiento: inbox o wiki) sin tocar el mapa de código.

    Args:
        args: Namespace de argparse con ``target``, ``--project``, ``--mode``,
        ``--url``, ``--youtube``, ``--destino``, ``--entidades``.
    """
    import types

    # Captura de fuentes al mundo conocimiento (F4, Web Clipper + video).
    url = getattr(args, "url", "") or ""
    youtube = getattr(args, "youtube", "") or ""
    video = getattr(args, "video", "") or ""
    if url or youtube or video:
        fuente = url or youtube or video
        _cmd_captura_fuente(args, fuente, es_youtube=bool(youtube or video))
        return

    # El proyecto se resuelve desde la raíz del repo, no desde el target de documentos
    proj_args = types.SimpleNamespace(
        cmd="ingest", target=".", project=getattr(args, "project", "Repo"),
    )
    proj = project_name(proj_args)
    ensure_dirs(proj)

    target = getattr(args, "target", None) or "."
    try:
        archivos = _recolectar_archivos(target)
    except ValueError as err:
        print(f"[ingest] {err}")
        return

    # Cargar nodos existentes para dedup
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    existentes = [Node.from_dict(r) for r in records]

    creados: list[Node] = []
    fallidos: list[str] = []

    for ruta in archivos:
        try:
            texto, _tipo = extraer_texto(ruta)
            nodo = crear_nodo_documento(ruta, texto, proj)
            if _existe_titulo(nodo.title, existentes):
                print(f"[ingest] omitido (ya existe): {os.path.basename(ruta)}")
                continue
            creados.append(nodo)
            existentes.append(nodo)
            print(f"[ingest] + {nodo.title} (concepto: {nodo.concept}, {len(nodo.evidence)} citas)")
        except (ValueError, FileNotFoundError) as err:
            fallidos.append(f"{os.path.basename(ruta)}: {err}")
            print(f"[ingest] ✗ {os.path.basename(ruta)}: {err}")

    if not creados:
        print("[ingest] Nada nuevo que ingerir.")
        if fallidos:
            print(f"[ingest] {len(fallidos)} archivo(s) con errores.")
        return

    append_nodes_edges(creados, [])
    print(f"[ingest] {len(creados)} documento(s) persistidos.")

    # Reconstruir vault con los nuevos nodos (build corre sobre la raíz del proyecto)
    import types

    build_args = types.SimpleNamespace(
        cmd="build",
        target=".",
        project=getattr(args, "project", "Repo"),
        mode=getattr(args, "mode", "hierarchical"),
        raw=getattr(args, "raw", False),
        clean=True,
        brief=getattr(args, "brief", False),
        quiet=getattr(args, "quiet", False),
        snapshot_name=None,
    )
    from context_map.application.commands.build import cmd_build

    cmd_build(build_args)
    print(f"[ingest] vault actualizado: {vault_dir(proj)}")

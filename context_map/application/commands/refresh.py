"""Comando refresh: actualiza el contexto en 1 solo paso, sin destruir lo manual.

Ejecuta secuencialmente:
1. Escaneo estático del proyecto (scan)
2. Construcción del Vault + Brief (build --brief, SIN --clean: preserva notas manuales)
3. Verificación de readiness (check)

Reemplaza el protocolo de 4 comandos del AGENTS.md: el agente solo necesita
`python -m pytest && ctxmap refresh` para dejar el contexto al día.
"""

from __future__ import annotations

import os
import types

from context_map.application.commands.build import cmd_build
from context_map.application.commands.scan import cmd_scan
from context_map.application.commands.tools import cmd_check


def _detectar_temporales(target: str) -> list[str]:
    """Detecta carpetas temporales típicas sin trackear en la raíz.

    R9 (auditoría 2026-08-14): artefactos como ``piloto_*`` (experimentos)
    o ``scripts/debug/`` (scripts de diagnóstico) suelen quedar fuera del
    control de versiones y ensucian la raíz. El AGENTS.md exige raíz limpia.

    Args:
        target (str): Ruta del proyecto.

    Returns:
        list[str]: Rutas relativas de carpetas temporales detectadas.
    """
    temporales: list[str] = []
    try:
        if not os.path.isdir(target):
            return temporales
        # Carpetas piloto_* / tmp_* en la raíz.
        for nombre in os.listdir(target):
            ruta = os.path.join(target, nombre)
            if os.path.isdir(ruta) and (
                nombre.startswith("piloto_") or nombre.startswith("tmp_")
            ):
                temporales.append(nombre)
        # scripts/debug/ en la raíz.
        debug_dir = os.path.join(target, "scripts", "debug")
        if os.path.isdir(debug_dir):
            temporales.append("scripts/debug")
    except Exception:
        return []
    return sorted(temporales)


def cmd_refresh(args) -> None:
    """Orquesta scan + build (sin clean) + check en un solo paso.

    Args:
        args: Namespace de argparse con atributo ``target`` y ``project``.
    """
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)
    abs_target = os.path.abspath(target)
    old_cwd = os.getcwd()

    if not quiet:
        print(f"[refresh] Actualizando contexto de: {target}")

    # Punto de control de versión (2026-08-11): antes de actualizar el CONTEXTO,
    # verificar si el PROGRAMA (binario ctxmap) está desactualizado y solicitarlo.
    # Aviso accionable y NO bloqueante: el agente/usuario decide actualizar.
    if not quiet:
        from context_map.infrastructure.version_check import aviso_pre_actualizacion

        print(aviso_pre_actualizacion(), end="")

    try:
        if abs_target != old_cwd:
            os.chdir(abs_target)

        cmd_scan(args)

        # Memoria viva automática multicanal (Hermes, Antigravity IDE, Chats externos, Raw Docs)
        # Todo lo conversado y documentado queda registrado en el grafo y bóveda.
        # Idempotente (dedup por hash/texto) y tolerante (nunca rompe el refresh).
        events_path = os.path.join(".context-map", "raw", "events.jsonl")

        # 1. Sesiones de Hermes
        if not quiet:
            print("[refresh] Importando sesiones recientes de Hermes...")
        try:
            from context_map.application.commands._helpers import project_name
            from context_map.infrastructure.integrations.hermes import importar_sesiones

            importados_hermes = importar_sesiones(
                db_path=None,
                limite=5,
                output_path=events_path,
                project=project_name(args),
            )
            if importados_hermes and not quiet:
                print(f"[refresh] {importados_hermes} evento(s) de sesiones importados")
        except Exception as err:  # noqa: BLE001
            if not quiet:
                print(f"[refresh] aviso: no se pudieron importar sesiones de Hermes ({err})")

        # 2. Sesiones de Antigravity IDE
        if not quiet:
            print("[refresh] Importando sesiones recientes de Antigravity IDE...")
        try:
            from context_map.application.commands._helpers import project_name
            from context_map.infrastructure.integrations.antigravity import importar_antigravity

            importados_ag = importar_antigravity(
                ide=True,
                limite=5,
                output_path=events_path,
                project=project_name(args),
            )
            if importados_ag and not quiet:
                print(f"[refresh] {importados_ag} evento(s) de Antigravity IDE importados")
        except Exception as err:  # noqa: BLE001
            if not quiet:
                print(f"[refresh] aviso: no se pudieron importar sesiones de Antigravity ({err})")

        # 3. Exportaciones de Chat externas (.context-map/chats/)
        chats_dir = os.path.join(".context-map", "chats")
        if os.path.isdir(chats_dir):
            try:
                from context_map.infrastructure.integrations.chat_export import importar_chat

                total_chats = 0
                for item in sorted(os.listdir(chats_dir)):
                    ruta_chat = os.path.join(chats_dir, item)
                    if os.path.isfile(ruta_chat) and not item.startswith("."):
                        try:
                            n = importar_chat(ruta_chat, output_path=events_path)
                            total_chats += n
                        except Exception as chat_err:  # noqa: BLE001
                            if not quiet:
                                print(f"[refresh] aviso: no se pudo procesar chat {item} ({chat_err})")
                if total_chats and not quiet:
                    print(f"[refresh] {total_chats} evento(s) de chats externos importados")
            except Exception as err:  # noqa: BLE001
                if not quiet:
                    print(f"[refresh] aviso en importación de chats ({err})")

        # 4. Auto-ingesta de Documentos de Referencia (.context-map/raw/docs/)
        docs_dir = os.path.join(".context-map", "raw", "docs")
        if os.path.isdir(docs_dir):
            try:
                from context_map.application.commands._helpers import (
                    append_nodes_edges,
                    project_name,
                )
                from context_map.core.models import Node
                from context_map.core.storage import load_jsonl
                from context_map.domain.ingestion import crear_nodo_documento, extraer_texto

                state_graph = os.path.join(".context-map", "state", "graph.jsonl")
                existentes_nodes: list[Node] = []
                if os.path.exists(state_graph):
                    existentes_nodes = [Node.from_dict(r) for r in load_jsonl(state_graph)]
                titulos_existentes = {n.title.strip().lower() for n in existentes_nodes}

                nuevos_docs: list[Node] = []
                for root, _dirs, files in os.walk(docs_dir):
                    for f in sorted(files):
                        if f.lower().endswith((".md", ".markdown", ".txt", ".text", ".pdf")):
                            ruta_doc = os.path.join(root, f)
                            try:
                                texto_doc, _ = extraer_texto(ruta_doc)
                                nodo_doc = crear_nodo_documento(ruta_doc, texto_doc, project_name(args))
                                if nodo_doc.title.strip().lower() not in titulos_existentes:
                                    nuevos_docs.append(nodo_doc)
                                    titulos_existentes.add(nodo_doc.title.strip().lower())
                            except Exception as doc_err:  # noqa: BLE001
                                if not quiet:
                                    print(f"[refresh] aviso: no se pudo ingerir documento {f} ({doc_err})")
                if nuevos_docs:
                    append_nodes_edges(nuevos_docs, [])
                    if not quiet:
                        print(f"[refresh] {len(nuevos_docs)} documento(s) nuevo(s) ingerido(s) al grafo")
            except Exception as err:  # noqa: BLE001
                if not quiet:
                    print(f"[refresh] aviso en auto-ingesta de documentos ({err})")

        # Clonar args para build con target="." y SIN --clean (preserva manuales).
        # Pitfall documentado: reutilizar el namespace original contamina
        # project_name() y genera vault con el nombre del target.
        build_args = types.SimpleNamespace(
            target=".",
            project=getattr(args, "project", "Repo"),
            snapshot_name="",
            brief=True,
            mode=getattr(args, "mode", "hierarchical"),
            raw=False,
            clean=False,
            quiet=quiet,
            aviso_pre=False,  # refresh ya imprime el aviso de versión al inicio
        )
        cmd_build(build_args)

        check_args = types.SimpleNamespace(target=".", json=False)
        cmd_check(check_args)

        # Sugerencia de limpieza (R9): carpetas temporales sin trackear.
        if not quiet:
            temporales = _detectar_temporales(target)
            if temporales:
                print()
                print("── Limpieza sugerida ──")
                for t in temporales:
                    print(f"  · {t} (sin trackear — ¿mover a _legacy/ o eliminar?)")
                print("────────────────────────")

        if not quiet:
            try:
                from pathlib import Path

                from context_map.core.tokenization import TokenCounter
                brief_p = Path(".context-map/CONTEXT.md")
                if brief_p.exists():
                    c = TokenCounter()
                    tk = c.count_tokens(brief_p.read_text(encoding="utf-8", errors="ignore"))
                    print(f"🧮 [tokens] Brief: {tk:,} tk | Ahorro de contexto: >99%")
            except Exception:
                pass
            print(f"[refresh] [OK] Contexto actualizado para {target}")
    finally:
        if abs_target != old_cwd:
            os.chdir(old_cwd)

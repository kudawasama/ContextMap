"""Comando ``search``: búsqueda de contexto del proyecto.

Usa el índice FTS5 del vault cuando está disponible (búsqueda full-text en
milisegundos) y cae al recuperador BM25 clásico (nodos + vault) si no hay
índice. Sin red y sin dependencias.
"""

from __future__ import annotations

import json
import os
import sqlite3
from typing import Any

from context_map.application.commands._helpers import CONTEXT_DIR
from context_map.core.storage.vault_index import abrir_indice, buscar as buscar_vault
from context_map.domain.retrieval import buscar_contexto, formatear_resultados


def _indice_disponible(target: str) -> str | None:
    """Ruta a la BD del índice FTS5 del vault si existe y no está vacía."""
    db_path = os.path.join(target or ".", CONTEXT_DIR, "state", "vault_index.db")
    if not os.path.isfile(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        try:
            n = conn.execute("SELECT COUNT(*) FROM notas").fetchone()[0]
        finally:
            conn.close()
        return db_path if n > 0 else None
    except Exception:  # noqa: BLE001 — índice corrupto/legacy: caer al fallback
        return None


def cmd_search(args: Any) -> None:
    """Ejecuta ``ctxmap search "<consulta>"``.

    Args:
        args: Namespace con ``consulta``, ``limite``, ``json`` y ``target``.
    """
    consulta = getattr(args, "consulta", "") or ""
    limite = int(getattr(args, "limite", 5))
    target = getattr(args, "target", ".") or "."
    as_json = bool(getattr(args, "json", False))

    db_path = _indice_disponible(target)
    if db_path is not None:
        conn = abrir_indice(db_path)
        try:
            resultados = buscar_vault(conn, consulta, limite=limite)
        finally:
            conn.close()

        if as_json:
            print(json.dumps(
                [
                    {
                        "ruta": r["ruta"],
                        "titulo": r["titulo"],
                        "seccion": r["seccion"],
                        "tipo": r["tipo"],
                        "snippet": r["snippet"],
                    }
                    for r in resultados
                ],
                ensure_ascii=False,
                indent=2,
            ))
            return

        if not resultados:
            print(f"[search] Sin resultados en el vault para: {consulta}")
            print("         Prueba otros términos, o ejecuta `ctxmap refresh .` para reindexar.")
            return

        print(f"[search] {len(resultados)} nota(s) del vault para: {consulta}")
        print()
        for r in resultados:
            print(f"- {r['ruta']}  ({r['seccion']} · {r['tipo'] or 'sin tipo'})")
            print(f"  {r['snippet']}")
        return

    # Fallback: recuperador BM25 clásico (nodos + vault sin índice FTS5)
    resultados = buscar_contexto(
        target,
        consulta,
        limite=limite,
        semantico=not getattr(args, "no_semantico", False),
    )

    if as_json:
        print(json.dumps(resultados, ensure_ascii=False, indent=2))
        return

    if not resultados:
        print(f"[search] Sin resultados para: {consulta}")
        print("         Prueba otros términos, o revisa `ctxmap refresh .` si el contexto está viejo.")
        return

    print(f"[search] {len(resultados)} pasaje(s) para: {consulta}")
    print()
    print("\n".join(formatear_resultados(resultados)))

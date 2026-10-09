"""Comando ``search``: búsqueda de contexto del proyecto con citas (P1.1).

Recupera pasajes relevantes de la **memoria del proyecto** (nodos del grafo +
notas del vault) usando BM25 local, para que el agente pida solo lo que necesita
en vez de leer ficheros completos. Sin red y sin dependencias.
"""

from __future__ import annotations

import json
from typing import Any

from context_map.domain.retrieval import buscar_contexto, formatear_resultados


def cmd_search(args: Any) -> None:
    """Ejecuta ``ctxmap search "<consulta>"``.

    Args:
        args: Namespace con ``consulta``, ``limite``, ``json`` y ``target``.
    """
    consulta = getattr(args, "consulta", "") or ""
    limite = int(getattr(args, "limite", 5))
    target = getattr(args, "target", ".") or "."
    as_json = bool(getattr(args, "json", False))

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

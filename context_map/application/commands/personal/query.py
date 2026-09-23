"""Búsqueda de texto completo (FTS5) y operaciones puntuales en personal.

Permite consultar eventos, lecciones y decisiones con filtros de proyecto,
así como registrar notas al vuelo y generar respaldos de la base SQLite.
"""

from __future__ import annotations

import json
import os
import shutil

from context_map.core.personal import Decision, Leccion, PersonalDB


def _cmd_personal_add(args) -> None:
    """Registra una lección o decisión al vuelo en la BD."""
    db = PersonalDB(args.db)
    try:
        texto = args.texto.strip()
        tipo = getattr(args, "tipo", "leccion") or "leccion"
        proyecto = getattr(args, "proyecto", None)
        contexto = getattr(args, "contexto", "") or ""
        tags = [t.strip() for t in (getattr(args, "tags", "") or "").split(",") if t.strip()]

        if tipo == "decision":
            ok = db.agregar_decision(
                Decision(
                    decision=texto,
                    contexto=contexto,
                    proyecto=proyecto,
                )
            )
            etiqueta = "decisión"
        else:
            ok = db.agregar_leccion(
                Leccion(
                    leccion=texto,
                    como_se_resolvio=contexto,
                    proyecto=proyecto,
                    tags=tags,
                )
            )
            etiqueta = "lección"

        if ok:
            print(f"personal: {etiqueta} guardada en {db.ruta}")
        else:
            print(f"personal: {etiqueta} ya existía (idempotente, sin duplicado)")
    finally:
        db.cerrar()


def _cmd_personal_query(args) -> None:
    """Busca en eventos, lecciones y decisiones con FTS5."""
    db = PersonalDB(args.db)
    try:
        resultados = db.buscar(
            args.consulta,
            proyecto=getattr(args, "proyecto", None),
            limite=getattr(args, "limite", 10) or 10,
        )
        if getattr(args, "json", False):
            print(
                json.dumps(
                    [
                        {
                            "tabla": r.tabla,
                            "texto": r.texto,
                            "proyecto": r.proyecto,
                            "puntaje": r.puntaje,
                        }
                        for r in resultados
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        if not resultados:
            print(f"personal: sin resultados para '{args.consulta}'")
            return

        print(f"personal: {len(resultados)} resultado(s) para '{args.consulta}':")
        print()
        for i, r in enumerate(resultados, 1):
            proy = f" [{r.proyecto}]" if r.proyecto else " [personal]"
            print(f"{i:2d}. ({r.tabla}){proy}")
            print(f"    {r.texto}")
            print()
    finally:
        db.cerrar()


def _cmd_personal_backup(args) -> None:
    """Copia la BD personal a otra ruta (pendrive, disco externo)."""
    db = PersonalDB(args.db)
    db.cerrar()

    destino = getattr(args, "destino", None)
    if not destino:
        print("personal: usa --destino <ruta> (ej. /run/media/usb/personal.db)")
        return

    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    shutil.copy2(db.ruta, destino)
    print(f"personal: backup -> {destino}")
    print(f"  origen: {db.ruta}")

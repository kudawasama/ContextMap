"""Comando ``wiki``: LLM Wiki (patrón Karpathy) del mundo conocimiento.

Expone la wiki PKM (``90-CONOCIMIENTO/05-WIKI``) desde la CLI:

- ``ctxmap wiki ingest <archivo>``  → página de resumen + índices + entry log + entidades.
- ``ctxmap wiki query "<pregunta>"`` → páginas relevantes CON CITAS.
- ``ctxmap wiki ask "<pregunta>"``  → respuesta extractiva local (sin LLM) con citas.
- ``ctxmap wiki moc``               → regenera el MOC (mapa de contenido).
- ``ctxmap wiki lint``              → salud: enlaces rotos, huérfanas, conceptos, contradicciones.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from context_map.application.commands._helpers import project_name, vault_dir
from context_map.domain.knowledge import wiki as kb


def _resolver_vault(args) -> str:
    """Resuelve el directorio del vault del proyecto objetivo."""
    return vault_dir(project_name(args))


def cmd_wiki(args) -> None:
    """Despacha las acciones del subcomando ``wiki``.

    Args:
        args: Namespace de argparse con ``wiki_cmd`` y sus opciones.
    """
    accion = getattr(args, "wiki_cmd", None)
    if not accion:
        print("Uso: ctxmap wiki {ingest|query|ask|moc|lint} [opciones]")
        return

    vdir = _resolver_vault(args)

    if accion == "ingest":
        archivo = getattr(args, "archivo", "")
        if not os.path.isfile(archivo):
            print(f"[wiki] El archivo no existe: {archivo}")
            return
        with open(archivo, encoding="utf-8") as f:
            contenido = f.read()
        resultado = kb.ingresar(
            vdir,
            titulo=getattr(args, "titulo", "") or "",
            contenido=contenido,
            fuente=getattr(args, "fuente", ""),
            entidades=getattr(args, "entidades", ""),
        )
        print(f"[wiki] 📄 Resumen creado: {resultado['ruta']}")
        if resultado["entidades"]:
            print(f"[wiki] 🔖 Entidades: {resultado['entidades']}")

    elif accion == "query":
        pregunta = getattr(args, "pregunta", "")
        limite = int(getattr(args, "limite", 5))
        resultados = kb.consultar(vdir, pregunta, limite=limite)
        if getattr(args, "json", False):
            print(json.dumps(resultados, ensure_ascii=False, indent=2))
            return
        if not resultados:
            print("[wiki] Sin páginas relevantes para esa consulta.")
            return
        print(f"[wiki] {len(resultados)} página(s) relevante(s) para: {pregunta}")
        for r in resultados:
            print(f"\n  📌 {r['titulo']}")
            print(f"     Cita: {r['cita']}")
            print(f"     {r['excerpt']}")

    elif accion == "ask":
        pregunta = getattr(args, "pregunta", "")
        limite = int(getattr(args, "limite", 5))
        sintesis = kb.sintetizar(vdir, pregunta, limite=limite)
        if getattr(args, "json", False):
            print(json.dumps(sintesis, ensure_ascii=False, indent=2))
            return
        if not sintesis["respuesta"]:
            print("[wiki] Sin páginas relevantes para responder esa pregunta.")
            return
        print(f"[wiki] 🧠 Respuesta (extractiva, local) para: {pregunta}\n")
        print(sintesis["respuesta"])
        print("\n[wiki] Fuentes:")
        for i, fuente in enumerate(sintesis["fuentes"], 1):
            print(f"  [{i}] {fuente['titulo']} — {fuente['cita']}")

    elif accion == "moc":
        ruta_moc = kb.generar_moc(vdir)
        if getattr(args, "json", False):
            print(json.dumps({"moc": ruta_moc}, ensure_ascii=False, indent=2))
            return
        print(f"[wiki] 🗺️ MOC regenerado: {ruta_moc}")

    elif accion == "lint":
        reporte = kb.lint(vdir)
        if getattr(args, "json", False):
            print(json.dumps(asdict(reporte), ensure_ascii=False, indent=2))
            return
        print(f"[wiki] 🩺 Salud de la wiki: {'OK' if reporte.ok else 'PROBLEMAS'}")
        for e in reporte.errores:
            print(f"  ⚠️  {e}")
        for a in reporte.avisos:
            print(f"  💬 {a}")
        if not reporte.errores and not reporte.avisos:
            print("  (sin errores ni avisos)")

    else:
        print(f"[wiki] Acción desconocida: {accion}")

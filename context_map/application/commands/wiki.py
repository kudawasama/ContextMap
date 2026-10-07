"""Comando ``wiki``: LLM Wiki (patrón Karpathy) del mundo conocimiento.

Expone la wiki PKM (``90-CONOCIMIENTO/05-WIKI``) desde la CLI:

- ``ctxmap wiki ingest <archivo>``  → página de resumen + índices + entry log + entidades.
- ``ctxmap wiki query "<pregunta>"`` → páginas relevantes CON CITAS.
- ``ctxmap wiki ask "<pregunta>"``  → respuesta extractiva local con citas (o con LLM con --llm).
- ``ctxmap wiki llm``               → estado del LLM opcional de síntesis.
- ``ctxmap wiki moc``               → regenera el MOC (mapa de contenido).
- ``ctxmap wiki lint``              → salud: enlaces rotos, huérfanas, conceptos, contradicciones.
- ``ctxmap wiki embeddings``        → estado/construcción del índice semántico opcional.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict

from context_map.application.commands._helpers import project_name, vault_dir
from context_map.domain.knowledge import embeddings
from context_map.domain.knowledge import llm as modulo_llm
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
        print("Uso: ctxmap wiki {ingest|query|ask|llm|moc|lint|embeddings} [opciones]")
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
        usar_llm: bool | None = None
        if getattr(args, "llm", False):
            usar_llm = True
        elif getattr(args, "no_llm", False):
            usar_llm = False
        sintesis = kb.sintetizar(vdir, pregunta, limite=limite, usar_llm=usar_llm)
        if getattr(args, "json", False):
            print(json.dumps(sintesis, ensure_ascii=False, indent=2))
            return
        if not sintesis["respuesta"]:
            print("[wiki] Sin páginas relevantes para responder esa pregunta.")
            return
        if usar_llm is True and sintesis.get("motor") != "llm":
            print("[wiki] aviso: el LLM no está configurado o falló; respuesta extractiva local.")
        print(f"[wiki] 🧠 Respuesta ({sintesis.get('motor', 'extractivo')}) para: {pregunta}\n")
        print(sintesis["respuesta"])
        print("\n[wiki] Fuentes:")
        for i, fuente in enumerate(sintesis["fuentes"], 1):
            print(f"  [{i}] {fuente['titulo']} — {fuente['cita']}")

    elif accion == "llm":
        diag = modulo_llm.estado()
        if getattr(args, "probar", False):
            prueba = modulo_llm.generar(
                "Responde con la palabra OK si recibes este contexto.",
                [("prueba", "El comando de prueba del LLM está funcionando.")],
            )
            diag["prueba"] = prueba or "sin respuesta"
        if getattr(args, "json", False):
            print(json.dumps(diag, ensure_ascii=False, indent=2))
            return
        print("[wiki] 🤖 Síntesis con LLM (opcional)")
        if not diag["disponible"]:
            print("  Estado: NO configurado — la wiki responde de forma extractiva local.")
            print(f"  Motivo: {diag['motivo']}")
            print(f"  Variables: {', '.join(diag['variables'])}")
            return
        print(f"  Modelo: {diag['modelo']}")
        print(f"  Endpoint: {diag['base_url']}")
        print("  Clave: configurada")
        if "prueba" in diag:
            print(f"  Prueba: {diag['prueba']}")
        print('  Uso: ctxmap wiki ask "<pregunta>" --llm')

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

    elif accion == "embeddings":
        rebuild = bool(getattr(args, "rebuild", False))
        indice = embeddings.construir_indice(vdir, forzar=True) if rebuild else {}
        diag = embeddings.estado(vdir)
        diag["reconstruido"] = rebuild and bool(indice.get("paginas"))
        if indice.get("motivo"):
            diag["motivo"] = indice["motivo"]
        if getattr(args, "json", False):
            print(json.dumps(diag, ensure_ascii=False, indent=2))
            return
        print("[wiki] 🧠 Búsqueda semántica (opcional)")
        if not diag["disponible"]:
            print("  Estado: NO disponible — el ranking sigue usando BM25.")
            print(f"  Motivo: {diag['motivo']}")
            print(f"  Instalar: {diag['instalar']}")
            return
        print(f"  Modelo: {diag['modelo']}")
        print(f"  Páginas de la wiki: {diag['paginas_wiki']}")
        print(f"  Páginas indexadas: {diag['paginas_indexadas']}")
        print(f"  Caché al día: {'sí' if diag['cache_al_dia'] else 'no (usa --rebuild)'}")
        if rebuild:
            print(f"  Índice reconstruido: {'sí' if diag['reconstruido'] else 'no'}")
        if diag.get("motivo"):
            print(f"  Motivo: {diag['motivo']}")
        print(f"  Caché: {diag['ruta_cache']}")

    else:
        print(f"[wiki] Acción desconocida: {accion}")

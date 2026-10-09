"""Búsqueda de contexto del proyecto: nodos del grafo + notas del vault (P1.1).

En vez de leer el brief completo y los ficheros enteros, el agente **pide lo que
necesita**: este módulo recupera los pasajes más relevantes de la memoria del
proyecto con **BM25 puro en Python** (sin dependencias) y devuelve **citas**
(`nodo:<id>` o la ruta de la nota) para poder profundizar.

Corpus:
- **Nodos** del grafo (``state/graph.jsonl``): título + resumen + evidencias.
- **Notas** del vault (``.context-map/vault-*/**/*.md``): manual, knowledge, diario…

El ranking replica el esquema de ``domain/knowledge/wiki.py`` (k1=1.5, b=0.75).
Unificar ambos BM25 en un helper común queda como refactor futuro (P2).
"""

from __future__ import annotations

import contextlib
import math
import os
import re
import unicodedata
from collections import Counter
from typing import Any

import context_map.core.vectorial as vectorial
from context_map.core.storage import load_jsonl

_PATRON_TERMINO = re.compile(r"[a-z0-9]{3,}")

# Palabras vacías (normalizadas sin acentos), mismo criterio que la wiki.
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en",
    "y", "o", "a", "para", "por", "con", "que", "se", "su", "al", "lo", "como",
    "es", "son", "mas", "pero", "sobre", "entre", "esto", "esta", "the",
    "of", "and", "to", "in", "on", "for",
}

K1, B = 1.5, 0.75
ANCHO_EXTRACTO = 240
PESO_SEMANTICO = 0.5
"""Peso de la señal semántica al fusionar con BM25 (mismo criterio que la wiki)."""
ESTADO_RELATIVO = os.path.join("state", "embeddings-contexto.json")


def _sin_acentos(texto: str) -> str:
    """Quita las marcas diacríticas (``generación`` → ``generacion``)."""
    descompuesto = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _terminos(texto: str) -> list[str]:
    """Términos buscables (minúsculas, sin acentos, sin stopwords) con repetición."""
    normal = _sin_acentos((texto or "").lower())
    return [t for t in _PATRON_TERMINO.findall(normal) if t not in _STOPWORDS]


def _titulo_nota(contenido: str, ruta: str) -> str:
    """Título de una nota: su primer encabezado ``#`` o el nombre del fichero."""
    for linea in contenido.splitlines():
        if linea.startswith("# "):
            return linea[2:].strip()
    return os.path.splitext(os.path.basename(ruta))[0].replace("-", " ")


def _documentos(project_dir: str = ".") -> list[dict[str, str]]:
    """Corpus buscable: nodos del grafo + notas del vault.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        list[dict[str, str]]: Documentos con ``titulo``, ``tipo``, ``cita``,
        ``ruta`` y ``texto``.
    """
    docs: list[dict[str, str]] = []

    ruta_grafo = os.path.join(project_dir, ".context-map", "state", "graph.jsonl")
    for registro in load_jsonl(ruta_grafo):
        titulo = str(registro.get("title") or "").strip()
        if not titulo:
            continue
        partes = [
            titulo,
            str(registro.get("summary") or ""),
            " ".join(str(e) for e in (registro.get("evidence") or [])),
        ]
        docs.append({
            "titulo": titulo,
            "tipo": str(registro.get("type") or "NODO"),
            "cita": f"nodo:{registro.get('id', '')}",
            "ruta": ruta_grafo,
            "texto": " ".join(p for p in partes if p),
        })

    contexto = os.path.join(project_dir, ".context-map")
    if os.path.isdir(contexto):
        for entrada in sorted(os.listdir(contexto)):
            if not entrada.startswith("vault"):
                continue
            raiz_vault = os.path.join(contexto, entrada)
            for raiz, _dirs, ficheros in os.walk(raiz_vault):
                for nombre in sorted(ficheros):
                    if not nombre.endswith(".md"):
                        continue
                    ruta = os.path.join(raiz, nombre)
                    try:
                        with open(ruta, encoding="utf-8") as f:
                            contenido = f.read()
                    except OSError:
                        continue
                    relativa = os.path.relpath(ruta, project_dir)
                    docs.append({
                        "titulo": _titulo_nota(contenido, ruta),
                        "tipo": "NOTA",
                        "cita": relativa,
                        "ruta": ruta,
                        "texto": contenido,
                    })
    return docs


def _extracto(texto: str, terminos: set[str], ancho: int = ANCHO_EXTRACTO) -> str:
    """Fragmento del texto centrado en la primera aparición de un término."""
    plano = re.sub(r"\s+", " ", texto).strip()
    if not plano:
        return ""
    bajo = _sin_acentos(plano.lower())
    posiciones = [bajo.find(t) for t in terminos if bajo.find(t) >= 0]
    if not posiciones:
        return plano[:ancho]
    pos = min(posiciones)
    inicio = max(0, pos - ancho // 3)
    trozo = plano[inicio:inicio + ancho].strip()
    return ("…" if inicio else "") + trozo + ("…" if inicio + ancho < len(plano) else "")


def _similitudes_contexto(
    project_dir: str,
    docs: list[dict[str, str]],
    consulta: str,
    codificador: vectorial.Codificador | None = None,
) -> dict[str, float]:
    """Similitud semántica (opcional) de la consulta contra el corpus del proyecto.

    Reutiliza el núcleo vectorial con su **propia caché** (``state/embeddings-contexto.json``)
    para no mezclarla con la de la wiki. Si ``sentence-transformers`` no está
    instalado (y no se inyecta codificador), devuelve ``{}``.

    Args:
        project_dir (str): Raíz del proyecto.
        docs (list[dict[str, str]]): Documentos del corpus (con ``cita`` y ``texto``).
        consulta (str): Texto de la consulta.
        codificador (vectorial.Codificador | None): Codificador inyectable (tests).

    Returns:
        dict[str, float]: ``{cita: similitud}``.
    """
    documentos = [(d["cita"], d["texto"]) for d in docs]
    ruta_cache = os.path.join(project_dir, ".context-map", ESTADO_RELATIVO)
    indice = vectorial.construir_indice(
        documentos, ruta_cache=ruta_cache, codificador=codificador
    )
    return vectorial.similitudes(consulta, indice, codificador=codificador)


def buscar_contexto(
    project_dir: str = ".",
    consulta: str = "",
    limite: int = 5,
    *,
    semantico: bool = True,
    codificador: vectorial.Codificador | None = None,
) -> list[dict[str, Any]]:
    """Recupera los pasajes más relevantes de la memoria del proyecto.

    Fusiona **BM25** (solape de términos, siempre disponible) con **similitud
    semántica** opcional (P1.3): así una paráfrasis sin solape léxico también
    encuentra su página. Sin ``sentence-transformers`` el comportamiento es BM25.

    Args:
        project_dir (str): Raíz del proyecto.
        consulta (str): Términos a buscar.
        limite (int): Máximo de resultados (default 5).
        semantico (bool): Usar embeddings si están disponibles (default True).
        codificador (vectorial.Codificador | None): Codificador inyectable (tests).

    Returns:
        list[dict[str, Any]]: Resultados con ``titulo``, ``tipo``, ``cita``,
        ``ruta``, ``extracto`` y ``puntaje``, ordenados por relevancia.
    """
    if limite <= 0 or not (consulta or "").strip():
        return []
    terminos = set(_terminos(consulta))

    docs = _documentos(project_dir)
    if not docs:
        return []

    tokenizados = [_terminos(d["texto"]) for d in docs]
    n_docs = len(docs)
    largo_medio = sum(len(t) for t in tokenizados) / n_docs or 1.0
    frecuencia_doc: Counter[str] = Counter()
    for tokens in tokenizados:
        frecuencia_doc.update(set(tokens))

    # BM25 (k1/b como en la wiki): pondera frecuencia, rareza del término y longitud.
    puntajes_bm25: dict[str, float] = {}
    if terminos:
        for doc, tokens in zip(docs, tokenizados, strict=True):
            tf = Counter(tokens)
            largo = len(tokens) or 1
            puntaje = 0.0
            for termino in terminos:
                if termino not in tf:
                    continue
                df = frecuencia_doc[termino]
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                puntaje += idf * (tf[termino] * (K1 + 1)) / (
                    tf[termino] + K1 * (1 - B + B * largo / largo_medio)
                )
            if puntaje > 0:
                puntajes_bm25[doc["cita"]] = puntaje

    semanticas: dict[str, float] = {}
    if semantico:
        with contextlib.suppress(Exception):
            semanticas = _similitudes_contexto(project_dir, docs, consulta, codificador)

    if not puntajes_bm25 and not semanticas:
        return []

    max_bm25 = max(puntajes_bm25.values(), default=0.0) or 1.0
    resultados: list[tuple[float, dict[str, Any]]] = []
    for doc in docs:
        cita = doc["cita"]
        puntaje = puntajes_bm25.get(cita, 0.0) / max_bm25 + (
            PESO_SEMANTICO * semanticas.get(cita, 0.0)
        )
        if puntaje <= 0:
            continue
        resultados.append((puntaje, {
            "titulo": doc["titulo"],
            "tipo": doc["tipo"],
            "cita": cita,
            "ruta": doc["ruta"],
            "extracto": _extracto(doc["texto"], terminos),
            "puntaje": round(puntaje, 3),
        }))

    resultados.sort(key=lambda x: x[0], reverse=True)
    return [r for _p, r in resultados[:limite]]


def formatear_resultados(resultados: list[dict[str, Any]]) -> list[str]:
    """Convierte los resultados en líneas legibles para CLI/MCP.

    Args:
        resultados (list[dict[str, Any]]): Salida de :func:`buscar_contexto`.

    Returns:
        list[str]: Una línea por resultado, con su cita y extracto.
    """
    lineas: list[str] = []
    for i, r in enumerate(resultados, 1):
        lineas.append(f"{i}. [{r['tipo']}] {r['titulo']}")
        lineas.append(f"   cita: {r['cita']}")
        lineas.append(f"   {r['extracto']}")
    return lineas

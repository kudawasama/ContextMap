"""P1.3: búsqueda semántica opcional sobre la memoria del proyecto.

Comprueba la **fusión** BM25 ∥ embeddings sin instalar ``sentence-transformers``:
se inyecta un codificador falso con sinónimos, de modo que una paráfrasis sin
solape léxico ("amnesia entre sesiones") encuentre su página ("memoria viva").
"""

from __future__ import annotations

import json
import os
import unicodedata

from context_map.core import vectorial
from context_map.domain.retrieval import buscar_contexto

# Sinónimos → término canónico (para que el codificador falso "entienda").
_SINONIMOS = {"amnesia": "memoria", "olvido": "memoria", "recuerdo": "memoria"}
_VOCAB = ("memoria", "vault", "snapshot", "riesgo", "agente")


def _norm(texto: str) -> str:
    """Minúsculas sin acentos (codificador falso)."""
    d = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in d if unicodedata.category(c) != "Mn")


def _codificador_falso(textos: list[str]) -> list[list[float]]:
    """Bolsa de palabras con sinónimos: 'amnesia' activa la dimensión 'memoria'."""
    vectores = []
    for texto in textos:
        palabras = {_SINONIMOS.get(p, p) for p in _norm(texto).split()}
        vectores.append([1.0 if v in palabras else 0.0 for v in _VOCAB])
    return vectores


def _proyecto(tmp_path) -> str:
    """Proyecto falso con un nodo sobre memoria y otro sobre riesgos."""
    raiz = str(tmp_path)
    estado = os.path.join(raiz, ".context-map", "state")
    os.makedirs(estado, exist_ok=True)
    nodos = [
        {"id": "BASE.1", "type": "BASE", "title": "Memoria viva del proyecto",
         "summary": "La memoria del proyecto evita que la IA olvide lo conversado."},
        {"id": "RIESGO.1", "type": "RIESGO", "title": "Snapshots sin retención",
         "summary": "El historial de snapshots crecía sin límite."},
    ]
    with open(os.path.join(estado, "graph.jsonl"), "w", encoding="utf-8") as f:
        for n in nodos:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    return raiz


def test_parafrasis_sin_solape_lexico_usa_la_semantica(tmp_path) -> None:
    """'amnesia entre sesiones' encuentra la página de memoria (0 solape léxico)."""
    raiz = _proyecto(tmp_path)

    # BM25 puro no la encuentra (no comparten términos)…
    assert buscar_contexto(raiz, "amnesia entre sesiones", semantico=False) == []

    # …pero con la señal semántica sí.
    resultados = buscar_contexto(raiz, "amnesia entre sesiones", codificador=_codificador_falso)

    assert resultados, "la fusión semántica debe recuperar la página"
    assert resultados[0]["titulo"] == "Memoria viva del proyecto"
    assert resultados[0]["cita"].startswith("nodo:")


def test_sin_semantica_el_ranking_sigue_siendo_bm25(tmp_path) -> None:
    """Desactivar la semántica deja el comportamiento léxico de siempre."""
    raiz = _proyecto(tmp_path)
    resultados = buscar_contexto(raiz, "snapshots historial", semantico=False)
    assert resultados and resultados[0]["titulo"] == "Snapshots sin retención"


def test_el_indice_semantico_se_cachea(tmp_path) -> None:
    """La segunda consulta NO vuelve a codificar el corpus (usa la caché)."""
    raiz = _proyecto(tmp_path)
    llamadas: list[int] = []

    def _codificador_que_cuenta(textos: list[str]) -> list[list[float]]:
        llamadas.append(len(textos))
        return _codificador_falso(textos)

    buscar_contexto(raiz, "amnesia entre sesiones", codificador=_codificador_que_cuenta)
    assert len(llamadas) == 2, f"esperado corpus + consulta: {llamadas}"
    assert llamadas[0] > 1, "el primer batch debe ser el corpus"

    llamadas.clear()
    resultados = buscar_contexto(raiz, "amnesia entre sesiones", codificador=_codificador_que_cuenta)
    assert resultados, "la segunda consulta debe seguir respondiendo"
    assert llamadas == [1], f"solo debe codificar la consulta (caché): {llamadas}"

    cache = os.path.join(raiz, ".context-map", "state", "embeddings-contexto.json")
    assert os.path.isfile(cache), "el índice debe quedar cacheado en el estado"


def test_sin_libreria_degrada_a_bm25(tmp_path, monkeypatch) -> None:
    """Sin sentence-transformers y sin codificador inyectado: solo BM25."""
    monkeypatch.setattr(vectorial, "_spec_instalada", lambda _nombre: False)
    raiz = _proyecto(tmp_path)

    assert buscar_contexto(raiz, "amnesia entre sesiones") == []  # sin solape léxico
    resultados = buscar_contexto(raiz, "snapshots historial")     # con solape
    assert resultados and resultados[0]["titulo"] == "Snapshots sin retención"

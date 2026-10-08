"""Búsqueda de contexto del proyecto (P1.1): nodos + notas con BM25 y citas.

El objetivo del "RAG del proyecto" es que el agente pida **solo lo que necesita**
en vez de leer el brief y los ficheros completos. Estas pruebas fijan el contrato:
recupera pasajes relevantes, los ordena por relevancia y **siempre cita**.
"""

from __future__ import annotations

import json
import os

from context_map.domain.retrieval import buscar_contexto, formatear_resultados


def _proyecto(tmp_path) -> str:
    """Proyecto falso con nodos en el grafo y notas en el vault."""
    raiz = str(tmp_path)
    ctx = os.path.join(raiz, ".context-map")
    estado = os.path.join(ctx, "state")
    vault = os.path.join(ctx, "vault-Demo", "7.0-MANUAL")
    os.makedirs(estado, exist_ok=True)
    os.makedirs(vault, exist_ok=True)

    nodos = [
        {"id": "BASE.1", "type": "BASE", "title": "Topología en árbol del vault",
         "summary": "Cada nota cuelga de exactamente un padre; los índices usan sufijo de estado."},
        {"id": "RIESGO.2", "type": "RIESGO", "title": "Ruido de snapshots",
         "summary": "El historial crecía sin retención y ocupaba 54 MB por copias de texto."},
        {"id": "BASE.3", "type": "BASE", "title": "Servidor MCP",
         "summary": "Expone las herramientas de ctxmap a los agentes por stdio."},
    ]
    with open(os.path.join(estado, "graph.jsonl"), "w", encoding="utf-8") as f:
        for n in nodos:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")

    with open(os.path.join(vault, "BACKLOG.md"), "w", encoding="utf-8") as f:
        f.write("# BACKLOG\n\nPendiente: limpiar los TODO históricos del estado.\n")
    return raiz


def test_encuentra_nodos_con_cita_y_extracto(tmp_path) -> None:
    """La consulta recupera el nodo correcto, con cita `nodo:<id>` y extracto."""
    raiz = _proyecto(tmp_path)

    resultados = buscar_contexto(raiz, "topologia del vault", limite=3)

    assert resultados, "debe encontrar el nodo de topología"
    primero = resultados[0]
    assert primero["titulo"] == "Topología en árbol del vault"
    assert primero["tipo"] == "BASE"
    assert primero["cita"].startswith("nodo:")
    assert primero["extracto"], "debe traer un fragmento para leer sin abrir el fichero"


def test_encuentra_notas_del_vault_con_su_ruta(tmp_path) -> None:
    """Las notas del vault entran en el corpus y se citan por su ruta relativa."""
    raiz = _proyecto(tmp_path)

    resultados = buscar_contexto(raiz, "TODO historicos del estado", limite=5)

    notas = [r for r in resultados if r["tipo"] == "NOTA"]
    assert notas, f"debe encontrar la nota: {resultados}"
    assert "7.0-MANUAL" in notas[0]["cita"] or "BACKLOG" in notas[0]["cita"]
    assert os.path.isfile(os.path.join(raiz, notas[0]["cita"])), "la cita debe ser una ruta real"


def test_orden_por_relevancia(tmp_path) -> None:
    """El documento que repite el término puntúa más alto (BM25)."""
    raiz = _proyecto(tmp_path)
    resultados = buscar_contexto(raiz, "snapshots", limite=5)
    assert resultados[0]["titulo"] == "Ruido de snapshots"
    assert resultados[0]["puntaje"] >= (resultados[1]["puntaje"] if len(resultados) > 1 else 0)


def test_busqueda_sin_acentos(tmp_path) -> None:
    """Una consulta sin tildes encuentra texto con tildes."""
    raiz = _proyecto(tmp_path)
    resultados = buscar_contexto(raiz, "topologia arbol", limite=3)
    assert any("Topología" in r["titulo"] for r in resultados), resultados


def test_consulta_vacia_o_inexistente_no_falla(tmp_path) -> None:
    """Sin términos (o sin proyecto) devuelve lista vacía, sin excepción."""
    raiz = _proyecto(tmp_path)
    assert buscar_contexto(raiz, "") == []
    assert buscar_contexto(raiz, "de la y") == []  # solo stopwords
    assert buscar_contexto(str(tmp_path / "no-existe"), "algo") == []


def test_formato_legible_con_citas(tmp_path) -> None:
    """El formateador incluye título, cita y extracto para el agente."""
    raiz = _proyecto(tmp_path)
    lineas = formatear_resultados(buscar_contexto(raiz, "servidor mcp", limite=2))
    texto = "\n".join(lineas)
    assert "cita:" in texto and "Servidor MCP" in texto

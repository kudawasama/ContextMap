"""Embeddings opcionales (G3): búsqueda semántica con degradación a BM25.

Ninguna prueba requiere ``sentence-transformers``: cuando se necesita la capa
semántica se inyecta un **codificador falso** determinista, de modo que el test
sea local, rápido y repetible.
"""

from __future__ import annotations

import os
import unicodedata
from types import SimpleNamespace as NS

import pytest

from context_map.application.commands import wiki as cmd_wiki
from context_map.domain.knowledge import embeddings as emb
from context_map.domain.knowledge import wiki as kb
from context_map.presentation.vault.consolidated.conocimiento import sembrar_conocimiento

_VOCAB = (
    "memoria", "proyecto", "ayer", "ia", "recuperacion", "rag", "cocina", "pasta", "vector",
)


_PAGINAS_BASE = 3  # 2 resúmenes (Memoria viva, Cocina) + 1 entidad (Memoria viva)


def _norm(texto: str) -> str:
    """Minúsculas sin acentos (mismo criterio que el ranking léxico)."""
    descompuesto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


def _codificador_falso(textos: list[str]) -> list[list[float]]:
    """Codificador determinista tipo bolsa-de-palabras (sin red ni modelo)."""
    vectores: list[list[float]] = []
    for texto in textos:
        norm = _norm(texto)
        vectores.append([1.0 if palabra in norm else 0.0 for palabra in _VOCAB])
    return vectores


def _explotar(_textos: list[str]) -> list[list[float]]:
    """Codificador que siempre falla (para probar la degradación elegante)."""
    raise RuntimeError("modelo no disponible")


def _vault(tmp_path) -> str:
    """Crea un vault con el esqueleto PKM sembrado."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    sembrar_conocimiento(vdir)
    return vdir


def _vault_con_paginas(tmp_path) -> str:
    """Vault con dos temas bien distintos: 2 resúmenes + 1 entidad = 3 páginas."""
    vdir = _vault(tmp_path)
    kb.ingresar(
        vdir,
        "Memoria viva",
        "La IA olvida lo hablado ayer si no existe un disco duro de memoria del proyecto.",
        entidades="Memoria viva",
    )
    kb.ingresar(vdir, "Cocina", "Recetas de pastas italianas tradicionales.")
    return vdir


def test_sin_dependencias_degrada_a_bm25(tmp_path, monkeypatch) -> None:
    """Sin sentence-transformers la capa semántica devuelve vacío, sin errores."""
    monkeypatch.setattr(emb, "_spec_instalada", lambda _nombre: False)
    vdir = _vault_con_paginas(tmp_path)

    ok, motivo = emb.disponible()
    assert ok is False
    assert "uv pip install" in motivo, "El motivo debe ser accionable"

    assert emb.similitudes(vdir, "memoria del proyecto") == {}
    assert emb.buscar(vdir, "memoria del proyecto") == []

    # El ranking léxico sigue funcionando con normalidad (BM25 puro).
    resultados = kb.consultar(vdir, "pastas italianas")
    assert resultados and resultados[0]["titulo"] == "Cocina"


def test_indice_con_codificador_y_cache_reutilizada(tmp_path) -> None:
    """El índice se construye una vez y se reutiliza si la wiki no cambia."""
    vdir = _vault_con_paginas(tmp_path)

    indice = emb.construir_indice(vdir, codificador=_codificador_falso)
    assert len(indice["paginas"]) == _PAGINAS_BASE
    assert indice["huella"], "Debe registrar la huella del corpus"
    assert os.path.exists(emb.ruta_cache(vdir)), "Debe persistir la caché"

    # Si la huella no cambió, NO se vuelve a codificar (el falso explota).
    cacheado = emb.construir_indice(vdir, codificador=_explotar)
    assert cacheado["paginas"] == indice["paginas"]

    # Forzado: sí recalcula (y entonces el fallo se refleja, sin excepción).
    forzado = emb.construir_indice(vdir, forzar=True, codificador=_explotar)
    assert forzado["paginas"] == {}
    assert "falló" in forzado["motivo"]


def test_cache_se_invalida_al_cambiar_la_wiki(tmp_path) -> None:
    """Agregar una página invalida la huella y reindexa el corpus."""
    vdir = _vault_con_paginas(tmp_path)
    primero = emb.construir_indice(vdir, codificador=_codificador_falso)

    kb.ingresar(vdir, "Vectores", "Un vector denso por documento.")
    segundo = emb.construir_indice(vdir, codificador=_codificador_falso)

    assert len(primero["paginas"]) == _PAGINAS_BASE
    assert len(segundo["paginas"]) == _PAGINAS_BASE + 1
    assert segundo["huella"] != primero["huella"]


def test_estado_reporta_disponibilidad_y_cache(tmp_path, monkeypatch) -> None:
    """``estado`` resume la capa semántica para el diagnóstico del CLI."""
    monkeypatch.setattr(emb, "_spec_instalada", lambda _nombre: False)
    vdir = _vault_con_paginas(tmp_path)

    diag = emb.estado(vdir)
    assert diag["disponible"] is False
    assert diag["paginas_wiki"] == _PAGINAS_BASE
    assert diag["paginas_indexadas"] == 0
    assert diag["cache_al_dia"] is False
    assert diag["instalar"] == "uv pip install sentence-transformers"

    # Con el índice construido (codificador inyectado), la caché queda al día.
    emb.construir_indice(vdir, codificador=_codificador_falso)
    diag = emb.estado(vdir)
    assert diag["paginas_indexadas"] == _PAGINAS_BASE
    assert diag["cache_al_dia"] is True


def test_consultar_usa_semantica_para_parafrasis(tmp_path, monkeypatch) -> None:
    """Una paráfrasis sin solape léxico recupera la página correcta (G3)."""
    vdir = _vault_con_paginas(tmp_path)

    def _similitudes_falsas(_vault_dir: str, _pregunta: str, **_kwargs) -> dict[str, float]:
        ruta = next(r for r, t in kb._paginas(_vault_dir) if t == "Memoria viva")
        return {ruta: 0.9}

    monkeypatch.setattr(emb, "similitudes", _similitudes_falsas)

    resultados = kb.consultar(vdir, "amnesia entre sesiones de la IA")
    assert resultados, "La señal semántica debe recuperar la página"
    assert resultados[0]["titulo"] == "Memoria viva"
    assert "[[" in resultados[0]["cita"], "Debe conservar la cita/wikilink"


def test_consultar_sin_semantica_no_cambia_el_ranking(tmp_path, monkeypatch) -> None:
    """Sin señal semántica el resultado es idéntico al BM25 de siempre."""
    vdir = _vault_con_paginas(tmp_path)
    monkeypatch.setattr(emb, "similitudes", lambda *_a, **_k: {})

    resultados = kb.consultar(vdir, "pastas italianas")
    assert resultados[0]["titulo"] == "Cocina"


def test_cli_embeddings_sin_dependencias(tmp_path, monkeypatch, capsys) -> None:
    """``ctxmap wiki embeddings`` informa y no revienta cuando falta la librería."""
    monkeypatch.setattr(emb, "_spec_instalada", lambda _nombre: False)
    vdir = _vault_con_paginas(tmp_path)
    monkeypatch.setattr(cmd_wiki, "_resolver_vault", lambda _args: vdir)

    cmd_wiki.cmd_wiki(NS(wiki_cmd="embeddings", target=".", json=False, rebuild=False))
    salida = capsys.readouterr().out
    assert "NO disponible" in salida
    assert "uv pip install sentence-transformers" in salida

    cmd_wiki.cmd_wiki(NS(wiki_cmd="embeddings", target=".", json=False, rebuild=True))
    salida = capsys.readouterr().out
    assert "NO disponible" in salida


def test_similitudes_con_codificador_real_ordena_por_cercania(tmp_path) -> None:
    """El coseno ordena: la consulta afín supera a la página de otro tema."""
    vdir = _vault_con_paginas(tmp_path)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(emb, "_spec_instalada", lambda _nombre: True)
        mp.setattr(emb, "_codificador_por_defecto", lambda: _codificador_falso)
        sims = emb.similitudes(vdir, "memoria del proyecto")

    assert sims, "Debe haber similitudes positivas"
    mejor = max(sims, key=lambda ruta: sims[ruta])
    assert "memoria" in mejor.lower() and "cocina" not in mejor.lower()

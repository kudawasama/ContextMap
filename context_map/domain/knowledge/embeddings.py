"""Embeddings opcionales (búsqueda semántica) para la wiki del mundo CONOCIMIENTO.

Capa **100% opcional**: si ``sentence-transformers`` no está instalado, todo el
sistema sigue funcionando con el ranking BM25 de ``wiki.consultar``. Este módulo
existe para que una paráfrasis lejana ("¿cómo recuerda la IA lo hablado ayer?")
encuentre una página que usa otras palabras ("memoria viva del proyecto").

Principios (coherentes con el plan v2.7):

- **Cero dependencias base**: ``torch`` / ``sentence-transformers`` se detectan
  en tiempo de ejecución (``importlib.util.find_spec``). El CI hace
  ``uv sync --dev --all-extras``, así que meterlos como extra rompería el
  pipeline: aquí no hay extra, hay *opt-in* manual del usuario.
- **Cero red en ``build``**: el modelo se descarga únicamente cuando el usuario
  ejecuta ``ctxmap wiki embeddings --rebuild`` (acción explícita), nunca al
  generar el vault ni el brief.
- **Determinismo y caché**: el índice vectorial vive en
  ``.context-map/state/embeddings.json`` y solo se recalcula cuando cambia el
  contenido de las páginas (invalidación por *hash* SHA-256).
- **Degradación elegante**: cualquier fallo (librería ausente, modelo no
  descargable, error de cómputo) devuelve ``{}`` / ``[]`` y nunca revienta.

Instalación opcional::

    uv pip install sentence-transformers
    ctxmap wiki embeddings --rebuild
"""

from __future__ import annotations

import os
from typing import Any

import context_map.core.vectorial as vectorial

MODELO_DEFAULT = vectorial.MODELO_DEFAULT
ESTADO_RELATIVO = os.path.join("state", "embeddings.json")
PESO_SEMANTICO = 0.5
"""Peso de la señal semántica al fusionar con BM25 en ``wiki.consultar``."""

Codificador = vectorial.Codificador


def _spec_instalada(nombre: str) -> bool:
    """Indica si un módulo es importable en el entorno actual.

    Args:
        nombre (str): Nombre del módulo (p. ej. ``sentence_transformers``).

    Returns:
        bool: True si ``find_spec`` lo encuentra.
    """
    return vectorial._spec_instalada(nombre)


def disponible() -> tuple[bool, str]:
    """Indica si la búsqueda semántica está disponible y con qué modelo.

    Returns:
        tuple[bool, str]: ``(True, modelo)`` si ``sentence-transformers`` está
        instalado; ``(False, motivo)`` con un mensaje accionable si falta.
    """
    if not _spec_instalada("sentence_transformers"):
        return False, (
            "sentence-transformers no está instalado (opcional). "
            "Instálalo con `uv pip install sentence-transformers` y reconstruye "
            "el índice con `ctxmap wiki embeddings --rebuild`."
        )
    return True, MODELO_DEFAULT


def ruta_cache(vault_dir: str) -> str:
    """Ruta del índice vectorial cacheado (``.context-map/state/embeddings.json``).

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        str: Ruta absoluta del archivo de caché.
    """
    return os.path.join(os.path.dirname(vault_dir), ESTADO_RELATIVO)


def _paginas(vault_dir: str) -> list[tuple[str, str]]:
    """Páginas de la wiki como ``(ruta_absoluta, título)``.

    Usa ``wiki.listar_paginas`` (import diferido para evitar el ciclo de
    importación ``wiki`` → ``embeddings`` → ``wiki``).
    """
    from context_map.domain.knowledge import wiki as kb

    return [(p["ruta"], p["titulo"]) for p in kb.listar_paginas(vault_dir)]


def _texto_pagina(ruta: str, titulo: str) -> str:
    """Texto indexable de una página: su título seguido del contenido completo."""
    try:
        with open(ruta, encoding="utf-8") as f:
            return f"{titulo}\n{f.read()}"
    except OSError:
        return titulo


def _huella(documentos: list[tuple[str, str]]) -> str:
    """Huella SHA-256 del corpus indexado (clave de invalidación de la caché).

    Args:
        documentos (list[tuple[str, str]]): Pares ``(clave_relativa, texto)``.

    Returns:
        str: Digest hexadecimal; cadena vacía si no hay documentos.
    """
    return vectorial.hash_documentos(documentos)


def leer_cache(vault_dir: str) -> dict[str, Any]:
    """Lee el índice vectorial cacheado; ``{}`` si no existe o está corrupto."""
    return vectorial.leer_cache(ruta_cache(vault_dir))


def _escribir_cache(vault_dir: str, datos: dict[str, Any]) -> None:
    """Persiste el índice vectorial (best-effort: un fallo de disco no rompe)."""
    vectorial.escribir_cache(ruta_cache(vault_dir), datos)


def _codificador_por_defecto() -> Codificador | None:
    """Carga perezosa del modelo de ``sentence-transformers`` (delega en el núcleo).

    Returns:
        Codificador | None: Función ``textos → vectores`` normalizados, o None.
    """
    return vectorial.codificador_por_defecto()


def construir_indice(
    vault_dir: str,
    *,
    forzar: bool = False,
    codificador: Codificador | None = None,
) -> dict[str, Any]:
    """Construye (o reutiliza de caché) el índice vectorial de las páginas.

    Args:
        vault_dir (str): Directorio raíz del vault.
        forzar (bool): Ignorar la caché y recalcular (default False).
        codificador (Codificador | None): Codificador inyectable (tests). Si es
            None y las dependencias no están, devuelve un índice vacío con
            ``motivo``.

    Returns:
        dict[str, Any]: ``{modelo, huella, paginas: {clave: vector}, motivo}``.
        Nunca lanza excepción: ante error devuelve ``paginas`` vacío y ``motivo``.
    """
    paginas = _paginas(vault_dir)
    if not paginas:
        return {"modelo": "", "huella": "", "paginas": {}}

    documentos = [
        (os.path.relpath(ruta, vault_dir), _texto_pagina(ruta, titulo))
        for ruta, titulo in paginas
    ]

    # Los hooks locales (``disponible`` / ``_codificador_por_defecto``) se resuelven
    # aquí: son los que los tests parchean.
    if codificador is None:
        ok, motivo = disponible()
        if not ok:
            return {"modelo": "", "huella": _huella(documentos), "paginas": {}, "motivo": motivo}
        codificador = _codificador_por_defecto()
        if codificador is None:
            return {
                "modelo": "",
                "huella": _huella(documentos),
                "paginas": {},
                "motivo": "No se pudo cargar el modelo de embeddings (¿sin conexión?).",
            }

    return vectorial.construir_indice(
        documentos,
        ruta_cache=ruta_cache(vault_dir),
        forzar=forzar,
        codificador=codificador,
    )


def _coseno(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores (0.0 si alguno es nulo o no encaja)."""
    return vectorial.coseno(a, b)


def similitudes(
    vault_dir: str,
    pregunta: str,
    *,
    codificador: Codificador | None = None,
) -> dict[str, float]:
    """Similitud coseno de la consulta contra cada página de la wiki.

    Args:
        vault_dir (str): Directorio raíz del vault.
        pregunta (str): Texto de la consulta.
        codificador (Codificador | None): Codificador inyectable (tests).

    Returns:
        dict[str, float]: ``{ruta_absoluta: similitud}`` solo con similitudes
        positivas; ``{}`` si la capa semántica no está disponible.
    """
    if not (pregunta or "").strip():
        return {}

    indice = construir_indice(vault_dir, codificador=codificador)
    vectores: dict[str, list[float]] = indice.get("paginas") or {}
    if not vectores:
        return {}

    if codificador is None:
        codificador = _codificador_por_defecto()
        if codificador is None:
            return {}

    similitudes_clave = vectorial.similitudes(pregunta, indice, codificador=codificador)
    return {os.path.join(vault_dir, clave): sim for clave, sim in similitudes_clave.items()}


def buscar(
    vault_dir: str,
    pregunta: str,
    limite: int = 5,
    *,
    codificador: Codificador | None = None,
    umbral: float = 0.0,
) -> list[tuple[str, float]]:
    """Páginas ordenadas por similitud semántica descendente.

    Args:
        vault_dir (str): Directorio raíz del vault.
        pregunta (str): Texto de la consulta.
        limite (int): Máximo de resultados (default 5).
        codificador (Codificador | None): Codificador inyectable (tests).
        umbral (float): Similitud mínima para incluir un resultado (default 0.0).

    Returns:
        list[tuple[str, float]]: Pares ``(ruta_absoluta, similitud)``.
    """
    sims = similitudes(vault_dir, pregunta, codificador=codificador)
    ordenadas = sorted(sims.items(), key=lambda item: item[1], reverse=True)
    return [(ruta, sim) for ruta, sim in ordenadas if sim > umbral][:limite]


def estado(vault_dir: str) -> dict[str, Any]:
    """Diagnóstico de la capa semántica (para ``ctxmap wiki embeddings``).

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        dict[str, Any]: Disponibilidad, modelo, páginas indexadas y si la caché
        está al día respecto al contenido actual de la wiki.
    """
    ok, motivo = disponible()
    cache = leer_cache(vault_dir)
    documentos = [
        (os.path.relpath(ruta, vault_dir), _texto_pagina(ruta, titulo))
        for ruta, titulo in _paginas(vault_dir)
    ]
    huella = _huella(documentos)
    indexadas = len(cache.get("paginas") or {})
    return {
        "disponible": ok,
        "motivo": "" if ok else motivo,
        "modelo": MODELO_DEFAULT if ok else "",
        "paginas_wiki": len(documentos),
        "paginas_indexadas": indexadas,
        "cache_al_dia": bool(cache.get("huella")) and cache.get("huella") == huella,
        "ruta_cache": ruta_cache(vault_dir),
        "instalar": "" if ok else "uv pip install sentence-transformers",
    }

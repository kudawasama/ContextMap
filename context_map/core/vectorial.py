"""Índice vectorial opcional (genérico) con caché por hash — sin dependencias base.

Núcleo reutilizable por la wiki (``domain/knowledge/embeddings.py``, G3) y por la
búsqueda de contexto del proyecto (``domain/retrieval/busqueda.py``, P1.3).

Reglas (plan de revisión):
- **Cero dependencias base**: ``sentence-transformers`` se detecta en ejecución.
- **Nunca rompe**: cualquier fallo devuelve índice vacío + ``motivo``.
- **Caché por hash** del corpus: si los documentos no cambian, no se recodifica.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
from collections.abc import Callable
from typing import Any

MODELO_DEFAULT = "paraphrase-multilingual-MiniLM-L12-v2"

Codificador = Callable[[list[str]], list[list[float]]]
"""Hook inyectable: ``textos → vectores``."""


def _spec_instalada(nombre: str) -> bool:
    """True si el módulo es importable en este entorno."""
    try:
        return importlib.util.find_spec(nombre) is not None
    except (ImportError, ValueError):
        return False


def disponible() -> tuple[bool, str]:
    """Indica si la búsqueda semántica está disponible y con qué modelo.

    Returns:
        tuple[bool, str]: ``(True, modelo)`` si ``sentence-transformers`` está
        instalado; ``(False, motivo)`` con un mensaje accionable si falta.
    """
    if not _spec_instalada("sentence_transformers"):
        return False, (
            "sentence-transformers no está instalado (opcional). Instálalo con "
            "`uv pip install sentence-transformers` y reconstruye el índice con "
            "`ctxmap wiki embeddings --rebuild`."
        )
    return True, MODELO_DEFAULT


def codificador_por_defecto() -> Codificador | None:
    """Carga perezosa del modelo de ``sentence-transformers``.

    Returns:
        Codificador | None: Función ``textos → vectores`` normalizados, o None.
    """
    if not _spec_instalada("sentence_transformers"):
        return None
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

        modelo = SentenceTransformer(MODELO_DEFAULT)
    except Exception:  # noqa: BLE001 — sin modelo se sigue con BM25
        return None

    def _codificar(textos: list[str]) -> list[list[float]]:
        vectores = modelo.encode(textos, normalize_embeddings=True)
        return [[float(x) for x in v] for v in vectores]

    return _codificar


def hash_documentos(documentos: list[tuple[str, str]]) -> str:
    """Huella SHA-256 del corpus (clave de invalidación de la caché).

    Args:
        documentos (list[tuple[str, str]]): Pares ``(clave, texto)``.

    Returns:
        str: Digest hexadecimal; cadena vacía si no hay documentos.
    """
    if not documentos:
        return ""
    h = hashlib.sha256()
    for clave, texto in sorted(documentos):
        h.update(clave.encode("utf-8"))
        h.update(b"\x00")
        h.update(texto.encode("utf-8"))
        h.update(b"\x01")
    return h.hexdigest()


def leer_cache(ruta: str) -> dict[str, Any]:
    """Lee un índice vectorial cacheado; ``{}`` si no existe o está corrupto."""
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict) and isinstance(datos.get("paginas"), dict):
            return datos
    except Exception:  # noqa: BLE001 — una caché inválida se regenera
        pass
    return {}


def escribir_cache(ruta: str, datos: dict[str, Any]) -> None:
    """Persiste el índice vectorial (best-effort: un fallo de disco no rompe)."""
    try:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
    except OSError:
        pass


def construir_indice(
    documentos: list[tuple[str, str]],
    *,
    ruta_cache: str,
    forzar: bool = False,
    codificador: Codificador | None = None,
) -> dict[str, Any]:
    """Construye (o reutiliza de caché) el índice vectorial de unos documentos.

    Args:
        documentos (list[tuple[str, str]]): Pares ``(clave, texto)`` del corpus.
        ruta_cache (str): Fichero JSON donde cachear el índice.
        forzar (bool): Ignorar la caché y recalcular (default False).
        codificador (Codificador | None): Codificador inyectable. Si es None y las
            dependencias no están, devuelve índice vacío con ``motivo``.

    Returns:
        dict[str, Any]: ``{modelo, huella, paginas: {clave: vector}, motivo}``.
        Nunca lanza excepción.
    """
    if not documentos:
        return {"modelo": "", "huella": "", "paginas": {}}

    huella = hash_documentos(documentos)
    cache = leer_cache(ruta_cache)
    if not forzar and cache.get("huella") == huella and cache.get("paginas"):
        return cache

    if codificador is None:
        ok, motivo = disponible()
        if not ok:
            return {"modelo": "", "huella": huella, "paginas": {}, "motivo": motivo}
        codificador = codificador_por_defecto()
        if codificador is None:
            return {
                "modelo": "",
                "huella": huella,
                "paginas": {},
                "motivo": "No se pudo cargar el modelo de embeddings (¿sin conexión?).",
            }

    try:
        vectores = codificador([texto for _clave, texto in documentos])
        if len(vectores) != len(documentos):
            raise ValueError("El codificador devolvió un número de vectores incorrecto.")
        indexado = {
            clave: [round(float(x), 6) for x in vector]
            for (clave, _texto), vector in zip(documentos, vectores, strict=True)
        }
    except Exception as err:  # noqa: BLE001 — la semántica es best-effort
        return {
            "modelo": "",
            "huella": huella,
            "paginas": {},
            "motivo": f"El cálculo de embeddings falló: {err}",
        }

    datos: dict[str, Any] = {"modelo": MODELO_DEFAULT, "huella": huella, "paginas": indexado}
    escribir_cache(ruta_cache, datos)
    return datos


def coseno(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores (0.0 si alguno es nulo o no encaja)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    punto = sum(x * y for x, y in zip(a, b, strict=True))
    norma_a = math.sqrt(sum(x * x for x in a))
    norma_b = math.sqrt(sum(y * y for y in b))
    if norma_a == 0 or norma_b == 0:
        return 0.0
    return punto / (norma_a * norma_b)


def similitudes(
    pregunta: str,
    indice: dict[str, Any],
    *,
    codificador: Codificador | None = None,
) -> dict[str, float]:
    """Similitud coseno de la consulta contra cada documento del índice.

    Args:
        pregunta (str): Texto de la consulta.
        indice (dict[str, Any]): Índice devuelto por :func:`construir_indice`.
        codificador (Codificador | None): Codificador inyectable (tests).

    Returns:
        dict[str, float]: ``{clave: similitud}`` solo con similitudes positivas;
        ``{}`` si la capa semántica no está disponible.
    """
    if not (pregunta or "").strip():
        return {}
    vectores: dict[str, list[float]] = indice.get("paginas") or {}
    if not vectores:
        return {}

    if codificador is None:
        codificador = codificador_por_defecto()
        if codificador is None:
            return {}

    try:
        vector_consulta = codificador([pregunta])[0]
    except Exception:  # noqa: BLE001 — best-effort
        return {}

    resultado: dict[str, float] = {}
    for clave, vector in vectores.items():
        similitud = coseno(list(vector_consulta), list(vector))
        if similitud > 0:
            resultado[clave] = similitud
    return resultado

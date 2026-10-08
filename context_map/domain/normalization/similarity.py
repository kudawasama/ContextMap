"""Módulo de evaluación de similitud difusa y deduplicación semántica para ContextMap.

Proporciona algoritmos locales (Levenshtein + Jaccard n-gramas) sin dependencias
pesadas ni llamadas a APIs para fusionar notas de riesgo e ideas redundantes.
"""

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def distancia_levenshtein(s1: str, s2: str, limite: int | None = None) -> int:
    """Calcula la distancia de edición Levenshtein entre dos cadenas.

    Optimizado (plan de revisión P2.1): recorta el prefijo/sufijo común y admite
    un ``limite`` con **corte temprano** (si el mínimo de una fila lo supera, la
    distancia final también; devuelve ``limite + 1``). El resultado es idéntico
    al algoritmo clásico cuando no se corta.

    Args:
        s1 (str): Primera cadena.
        s2 (str): Segunda cadena.
        limite (int | None): Distancia máxima de interés (None = sin corte).

    Returns:
        int: Número de ediciones mínimas (o ``limite + 1`` si lo supera).
    """
    if s1 == s2:
        return 0
    if not s1:
        return len(s2)
    if not s2:
        return len(s1)

    # Prefijo y sufijo comunes no afectan a la distancia: recortarlos acorta el DP.
    inicio = 0
    corto = min(len(s1), len(s2))
    while inicio < corto and s1[inicio] == s2[inicio]:
        inicio += 1
    fin1, fin2 = len(s1), len(s2)
    while fin1 > inicio and fin2 > inicio and s1[fin1 - 1] == s2[fin2 - 1]:
        fin1 -= 1
        fin2 -= 1
    a, b = s1[inicio:fin1], s2[inicio:fin2]
    if not a:
        return len(b)
    if not b:
        return len(a)

    if limite is not None and abs(len(a) - len(b)) > limite:
        return limite + 1

    len_b = len(b)
    fila = list(range(len_b + 1))
    for i, ca in enumerate(a, 1):
        nueva = [i] + [0] * len_b
        mejor = i
        for j, cb in enumerate(b, 1):
            costo = 0 if ca == cb else 1
            arriba = fila[j] + 1
            izquierda = nueva[j - 1] + 1
            diagonal = fila[j - 1] + costo
            valor = arriba if arriba < izquierda else izquierda
            if diagonal < valor:
                valor = diagonal
            nueva[j] = valor
            if valor < mejor:
                mejor = valor
        if limite is not None and mejor > limite:
            return limite + 1
        fila = nueva

    distancia = fila[len_b]
    if limite is not None and distancia > limite:
        return limite + 1
    return distancia


def _obtener_ngramas(texto: str, n: int = 3) -> set[str]:
    """Genera el conjunto de n-gramas de caracteres para un texto."""
    texto_limpio = texto.lower().strip()
    if len(texto_limpio) < n:
        return {texto_limpio}
    return {texto_limpio[i : i + n] for i in range(len(texto_limpio) - n + 1)}


def similitud_jaccard_ngramas(s1: str, s2: str, n: int = 3) -> float:
    """Calcula el índice de similitud de Jaccard a nivel de n-gramas de caracteres.

    Args:
        s1: Primer texto.
        s2: Segundo texto.
        n: Tamaño del n-grama (default: 3).

    Returns:
        Valor flotante entre 0.0 (totalmente distintos) y 1.0 (idénticos).
    """
    if not s1 or not s2:
        return 0.0
    set1 = _obtener_ngramas(s1, n)
    set2 = _obtener_ngramas(s2, n)

    interseccion = len(set1.intersection(set2))
    union = len(set1.union(set2))

    if union == 0:
        return 0.0
    return interseccion / union


def _son_similares_normalizados(
    s1_norm: str,
    s2_norm: str,
    ngramas1: set[str] | None = None,
    ngramas2: set[str] | None = None,
    umbral: float = 0.8,
) -> bool:
    """Igual que :func:`son_textos_similares` pero con textos ya normalizados.

    Permite reutilizar los n-gramas precalculados en la deduplicación masiva
    (evita reconstruir conjuntos en cada comparación).

    Args:
        s1_norm (str): Primer texto (minúsculas, sin espacios extremos).
        s2_norm (str): Segundo texto (igual).
        ngramas1 (set[str] | None): N-gramas de ``s1_norm`` (opcional).
        ngramas2 (set[str] | None): N-gramas de ``s2_norm`` (opcional).
        umbral (float): Umbral de similitud.

    Returns:
        bool: True si se consideran similares.
    """
    if not s1_norm or not s2_norm:
        return False
    if s1_norm == s2_norm:
        return True

    set1 = ngramas1 if ngramas1 is not None else _obtener_ngramas(s1_norm)
    set2 = ngramas2 if ngramas2 is not None else _obtener_ngramas(s2_norm)
    union = len(set1 | set2)
    sim_jaccard = len(set1 & set2) / union if union else 0.0
    if sim_jaccard >= umbral:
        return True

    # Cota exacta: con sim_lev ≤ 1 la puntuación máxima es 0.6·jaccard + 0.4.
    # Si esa cota no alcanza el umbral, ningún Levenshtein lo salvaría.
    if 0.6 * sim_jaccard + 0.4 < umbral:
        return False

    max_len = max(len(s1_norm), len(s2_norm))
    if max_len == 0:
        return True

    # Distancia máxima admisible para llegar al umbral (Levenshtein acotado).
    necesario = (umbral - 0.6 * sim_jaccard) / 0.4
    tope = int((1.0 - necesario) * max_len + 1e-9)
    dist = distancia_levenshtein(s1_norm, s2_norm, limite=tope)
    if dist > tope:
        return False
    sim_lev = 1.0 - (dist / max_len)
    return (sim_jaccard * 0.6 + sim_lev * 0.4) >= umbral


def son_textos_similares(s1: str, s2: str, umbral: float = 0.8) -> bool:
    """Evalúa si dos textos son semánticamente similares utilizando Jaccard y Levenshtein.

    Args:
        s1: Primer texto.
        s2: Segundo texto.
        umbral: Umbral de similitud entre 0.0 y 1.0 (default: 0.8).

    Returns:
        True si los textos superan el umbral; False en caso contrario.
    """
    return _son_similares_normalizados(s1.strip().lower(), s2.strip().lower(), umbral=umbral)


def deduplicar_elementos_similares(
    elementos: list[T],
    obtener_texto_fn: Callable[[T], str],
    umbral: float = 0.8,
) -> list[T]:
    """Deduplica una lista de objetos reteniendo solo el primero de cada grupo de similares.

    Args:
        elementos: Lista de objetos a filtrar.
        obtener_texto_fn: Función para extraer la cadena de texto a comparar.
        umbral: Umbral de similitud difusa.

    Returns:
        Lista filtrada deduplicada.
    """
    unicos: list[tuple[T, str, set[str]]] = []

    for item in elementos:
        texto = obtener_texto_fn_safe(item, obtener_texto_fn).strip().lower()
        ngramas = _obtener_ngramas(texto)
        es_duplicado = False

        for _retenido, texto_retenido, ngramas_retenidos in unicos:
            if _son_similares_normalizados(
                texto, texto_retenido, ngramas, ngramas_retenidos, umbral=umbral
            ):
                es_duplicado = True
                break

        if not es_duplicado:
            unicos.append((item, texto, ngramas))

    return [item for item, _texto, _ngramas in unicos]


def obtener_texto_fn_safe(item: T, fn: Callable[[T], str]) -> str:
    """Invoca la función de extracción de texto de forma segura."""
    try:
        return fn(item)
    except Exception:
        return ""

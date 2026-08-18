"""Módulo de evaluación de similitud difusa y deduplicación semántica para ContextMap.

Proporciona algoritmos locales (Levenshtein + Jaccard n-gramas) sin dependencias
pesadas ni llamadas a APIs para fusionar notas de riesgo e ideas redundantes.
"""

from typing import List, Callable, TypeVar, Set, Tuple

T = TypeVar("T")


def distancia_levenshtein(s1: str, s2: str) -> int:
    """Calcula la distancia de edición Levenshtein entre dos cadenas.

    Args:
        s1: Primera cadena.
        s2: Segunda cadena.

    Returns:
        Número de ediciones mínimas requeridas.
    """
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)

    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)

    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            costo = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + costo)
        v0 = list(v1)

    return v1[len(s2)]


def _obtener_ngramas(texto: str, n: int = 3) -> Set[str]:
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


def son_textos_similares(s1: str, s2: str, umbral: float = 0.8) -> bool:
    """Evalúa si dos textos son semánticamente similares utilizando Jaccard y Levenshtein.

    Args:
        s1: Primer texto.
        s2: Segundo texto.
        umbral: Umbral de similitud entre 0.0 y 1.0 (default: 0.8).

    Returns:
        True si los textos superan el umbral; False en caso contrario.
    """
    if not s1 or not s2:
        return False

    s1_norm = s1.strip().lower()
    s2_norm = s2.strip().lower()

    if s1_norm == s2_norm:
        return True

    sim_jaccard = similitud_jaccard_ngramas(s1_norm, s2_norm)
    if sim_jaccard >= umbral:
        return True

    # Levenshtein relativo
    max_len = max(len(s1_norm), len(s2_norm))
    if max_len == 0:
        return True
    dist = distancia_levenshtein(s1_norm, s2_norm)
    sim_lev = 1.0 - (dist / max_len)

    return (sim_jaccard * 0.6 + sim_lev * 0.4) >= umbral


def deduplicar_elementos_similares(
    elementos: List[T],
    obtener_texto_fn: Callable[[T], str],
    umbral: float = 0.8,
) -> List[T]:
    """Deduplica una lista de objetos reteniendo solo el primero de cada grupo de similares.

    Args:
        elementos: Lista de objetos a filtrar.
        obtener_texto_fn: Función para extraer la cadena de texto a comparar.
        umbral: Umbral de similitud difusa.

    Returns:
        Lista filtrada deduplicada.
    """
    unicos: List[T] = []

    for item in elementos:
        texto_item = obtener_texto_fn(item)
        es_duplicado = False

        for retenido in unicos:
            texto_retenido = obtener_texto_fn_safe(retenido, obtener_texto_fn)
            if son_textos_similares(texto_item, texto_retenido, umbral=umbral):
                es_duplicado = True
                break

        if not es_duplicado:
            unicos.append(item)

    return unicos


def obtener_texto_fn_safe(item: T, fn: Callable[[T], str]) -> str:
    """Invoca la función de extracción de texto de forma segura."""
    try:
        return fn(item)
    except Exception:
        return ""

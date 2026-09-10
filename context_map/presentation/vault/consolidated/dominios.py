"""Dominios temáticos del proyecto (``.context-map/dominios.yaml``) y su
aplicación como tags ``grupo-<dominio>`` sobre los nodos del vault.
"""

from __future__ import annotations

import logging
import os

from context_map.core.models import Node

logger = logging.getLogger(__name__)


_DOMINIOS_CACHE: dict[str, dict[str, list[str]]] = {}


def _es_linea_descartable_dominios(limpia: str) -> bool:
    """True si la línea no aporta al parser de dominios (vacía, comentario, separador).

    Args:
        limpia (str): Línea sin espacios alrededor.

    Returns:
        bool: True si debe descartarse.
    """
    return not limpia or limpia.startswith("#") or limpia.startswith("---")


def _es_definicion_dominio(limpia: str) -> bool:
    """True si la línea define un dominio (``nombre:``, no un item ``- ...``).

    Args:
        limpia (str): Línea sin espacios alrededor.

    Returns:
        bool: True si es una definición de dominio.
    """
    return limpia.endswith(":") and not limpia.startswith("-")


def _es_item_dominio(limpia: str, nombre_actual: str | None) -> bool:
    """True si la línea es un item de palabra clave bajo un dominio activo.

    Args:
        limpia (str): Línea sin espacios alrededor.
        nombre_actual (str | None): Dominio activo actual.

    Returns:
        bool: True si es un item ``- valor`` y hay dominio activo.
    """
    return bool(limpia.startswith("- ") and nombre_actual)


def _parsear_dominios_simple(texto: str) -> dict[str, list[str]]:
    """Parser mínimo del formato de dominios.yaml (sin depender de pyyaml).

    Soporta el subconjunto que usamos: ``nombre:`` seguido de líneas
    ``  - palabra clave``. Comentarios (#) y ``---`` se ignoran.
    """
    dominios: dict[str, list[str]] = {}
    nombre_actual: str | None = None
    for linea in texto.splitlines():
        limpia = linea.strip()
        if _es_linea_descartable_dominios(limpia):
            continue
        if _es_definicion_dominio(limpia):
            nombre_actual = limpia[:-1].strip()
            dominios[nombre_actual] = []
        elif _es_item_dominio(limpia, nombre_actual):
            valor = limpia[2:].strip().strip('"').strip("'")
            if valor:
                dominios[nombre_actual].append(valor)
    return {k: v for k, v in dominios.items() if v}


def _cargar_dominios(texto: str) -> dict[str, list[str]]:
    """Carga los dominios desde el texto YAML, con fallback al parser mínimo.

    Intenta ``yaml.safe_load`` (el binario ``uv tool`` puede no incluir PyYAML);
    si no está disponible usa ``_parsear_dominios_simple``. En ambos casos las
    claves se normalizan a minúsculas.

    Args:
        texto (str): Contenido de ``dominios.yaml``.

    Returns:
        dict[str, list[str]]: Mapeo dominio -> palabras clave en minúsculas.
    """
    dominios: dict[str, list[str]] = {}
    try:
        import yaml  # noqa: PLC0415 — opcional; fallback si no está

        datos = yaml.safe_load(texto) or {}
        for nombre, claves in datos.items():
            if isinstance(claves, list):
                dominios[str(nombre)] = [str(c).lower() for c in claves]
    except ImportError:
        # El entorno del binario (uv tool) puede no tener pyyaml:
        # usamos el parser mínimo del formato.
        for nombre, claves in _parsear_dominios_simple(texto).items():
            dominios[nombre] = [c.lower() for c in claves]
    return dominios


def _leer_dominios(cwd: str | None = None) -> dict[str, list[str]]:
    """Lee los dominios temáticos del proyecto desde ``.context-map/dominios.yaml``.

    Cada dominio define palabras clave; una nota se etiqueta con
    ``grupo-<dominio>`` cuando su título/resumen las menciona. Son los
    GRUPOS REALES del contexto (configurables por proyecto).

    Args:
        cwd (str | None): Directorio del proyecto (default: os.getcwd()).

    Returns:
        dict[str, list[str]]: Mapeo dominio -> palabras clave.
    """
    base = cwd or os.getcwd()
    ruta = os.path.join(base, ".context-map", "dominios.yaml")
    if ruta in _DOMINIOS_CACHE:
        return _DOMINIOS_CACHE[ruta]
    dominios: dict[str, list[str]] = {}
    try:
        if os.path.isfile(ruta):
            with open(ruta, encoding="utf-8") as f:
                texto = f.read()
            dominios = _cargar_dominios(texto)
    except Exception as err:  # noqa: BLE001 — los dominios son opcionales
        logger.debug("dominios.yaml no legible: %s", err)
    _DOMINIOS_CACHE[ruta] = dominios
    return dominios


def _tags_dominio(n: Node, cwd: str | None = None) -> list[str]:
    """Devuelve los tags ``grupo-<dominio>`` que aplican al nodo.

    Args:
        n (Node): Nodo del mapa.
        cwd (str | None): Directorio del proyecto.

    Returns:
        list[str]: Etiquetas de dominio (ej. ``grupo-humanizacion``).
    """
    texto = f"{n.title or ''} {n.summary or ''}".lower()
    if not texto.strip():
        return []
    resultado: list[str] = []
    for nombre, claves in _leer_dominios(cwd).items():
        if any(c in texto for c in claves):
            resultado.append(f"grupo-{nombre}")
    return resultado


def _linea_tags_inline(n: Node, cwd: str | None = None) -> str:
    """Línea de etiquetas inline coloreadas para poner bajo el título de una nota.

    Devuelve algo como ``> #ideas #pendiente #DEVOPS`` (se pinta con el
    snippet CSS ``colored-tags``). Vacío si el nodo no tiene etiquetas útiles.

    Args:
        n (Node): Nodo del mapa.

    Returns:
        str: Línea de etiquetas o string vacío.
    """
    mapa_tipo = {
        "IDEA": "ideas",
        "RIESGO": "riesgo",
        "CAMBIO": "cambio",
        "CORRECCION": "correccion",
        "BASE": "base",
        "PRUEBA": "prueba",
        "FUTURO": "futuro",
    }
    etiquetas: list[str] = []
    tipo = getattr(n, "type", "") or ""
    estado = getattr(n, "status", "") or ""
    concepto = getattr(n, "concept", "") or ""

    if tipo in mapa_tipo:
        etiquetas.append(mapa_tipo[tipo])
    if estado in ("pendiente", "activo", "completado"):
        etiquetas.append(estado)
    if concepto:
        etiquetas.append(concepto)
    # Tags de dominio (grupos REALES del contexto, de dominios.yaml)
    etiquetas.extend(_tags_dominio(n, cwd))
    if not etiquetas:
        return ""
    return "> " + " ".join(f"#{e}" for e in etiquetas)

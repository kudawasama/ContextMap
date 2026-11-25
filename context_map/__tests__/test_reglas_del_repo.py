"""El catálogo de reglas del propio repo es válido y apunta a normas reales.

Contrato ejecutable de la capa B (reglas del proyecto como datos): el archivo
``references/reglas/reglas_registro.yaml`` es la fuente única de verdad de lo
que un agente debe hacer en ContextMap. Si una regla cita una norma que no
existe, o el archivo se corrompe, el brief mentiría y el agente se orientaría
mal; por eso estas comprobaciones son un test y no una convención.
"""

from __future__ import annotations

import os
import re
from collections import Counter

import pytest

from context_map.domain.reglas.reglas import (
    buscar_y_resumir,
    parsear_catalogo,
    resumen_catalogo,
)

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATALOGO = os.path.join(RAIZ, "references", "reglas", "reglas_registro.yaml")

#: Formato de ID de la convención Gobernanza.
ID_RE = re.compile(r"^REG-[A-Z]{3}-\d{3}$")
#: Campos obligatorios por regla (ver cabecera del YAML).
CAMPOS = ("id", "nombre", "categoria", "prioridad", "estado", "norma", "seccion")
PRIORIDADES = {"critica", "alta", "media"}
ESTADOS = {"implementada", "pendiente"}


def _reglas() -> list[dict]:
    """Carga las reglas del catálogo del repo.

    Returns:
        list[dict]: Reglas parseadas (vacía si el archivo no existe).
    """
    return parsear_catalogo(CATALOGO)


def test_el_catalogo_existe() -> None:
    """Sin catálogo, el brief no puede orientar a nadie."""
    assert os.path.isfile(CATALOGO), (
        "falta references/reglas/reglas_registro.yaml: el agente volvería a "
        "depender de la memoria del chat"
    )


def test_el_catalogo_tiene_reglas() -> None:
    """Un catálogo vacío pasaría todos los demás tests y no sirve de nada."""
    assert len(_reglas()) >= 10, "el catálogo debe cubrir ejecución, vault y arquitectura"


def test_cada_regla_tiene_los_campos_obligatorios() -> None:
    """Un campo vacío deja la regla sin norma que la respalde."""
    for regla in _reglas():
        for campo in CAMPOS:
            assert str(regla.get(campo, "")).strip(), f"{regla.get('id')}: falta '{campo}'"


def test_ids_unicos_y_con_formato() -> None:
    """IDs duplicados romperían el dedup del grafo; mal formados, el filtro."""
    ids = [str(r.get("id", "")) for r in _reglas()]
    for regla_id in ids:
        assert ID_RE.match(regla_id), f"id fuera de convención: {regla_id!r}"

    repetidos = [i for i, n in Counter(ids).items() if n > 1]
    assert not repetidos, f"ids repetidos: {repetidos}"


def test_la_categoria_es_el_prefijo_del_id() -> None:
    """La categoría agrupa en el brief; si no coincide, el resumen miente."""
    for regla in _reglas():
        prefijo = str(regla["id"]).rsplit("-", 1)[0]
        assert regla["categoria"] == prefijo, (
            f"{regla['id']}: categoria {regla['categoria']!r} != prefijo {prefijo!r}"
        )


def test_prioridad_y_estado_son_valores_conocidos() -> None:
    """Valores libres harían imposible ordenar o filtrar las reglas."""
    for regla in _reglas():
        assert regla["prioridad"] in PRIORIDADES, f"{regla['id']}: prioridad inválida"
        assert regla["estado"] in ESTADOS, f"{regla['id']}: estado inválido"


def test_cada_norma_existe_en_el_repo() -> None:
    """La regla sin norma escrita es un rumor: la norma debe ser un archivo real."""
    for regla in _reglas():
        ruta = os.path.join(RAIZ, str(regla["norma"]))
        assert os.path.isfile(ruta), f"{regla['id']}: norma inexistente {regla['norma']!r}"


def test_la_seccion_existe_dentro_de_la_norma() -> None:
    """`seccion` es el ancla legible: si no está en el archivo, no guía a nada.

    Compara solo el número de sección ("7. Reglas fijas…" → "7."), que es
    estable y no se rompe al reescribir un título.
    """
    for regla in _reglas():
        ruta = os.path.join(RAIZ, str(regla["norma"]))
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
        ancla = str(regla["seccion"]).split(" — ")[0].strip()
        numero = ancla.split(".")[0] + "." if ancla[:1].isdigit() else ancla
        assert numero in texto, (
            f"{regla['id']}: la sección {regla['seccion']!r} no aparece en {regla['norma']}"
        )


def test_el_resumen_y_la_busqueda_ven_el_catalogo() -> None:
    """El brief y el scan leen el catálogo por estas dos funciones."""
    resumen = resumen_catalogo(CATALOGO)
    assert resumen["total"] == len(_reglas())
    assert resumen["categorias"], "el brief debe poder agrupar por categoría"

    encontrado = buscar_y_resumir(RAIZ)
    assert encontrado["total"] == len(_reglas()), "buscar_y_resumir no encuentra el catálogo"


@pytest.mark.parametrize("categoria", ["REG-EJE", "REG-VLT", "REG-ARQ", "REG-DOC"])
def test_las_categorias_imprescindibles_estan_cubiertas(categoria: str) -> None:
    """Un catálogo sin ejecución o sin vault deja fuera lo que más se rompe."""
    assert any(r["categoria"] == categoria for r in _reglas()), f"falta la categoría {categoria}"


def test_el_resumen_cabe_en_una_linea() -> None:
    """`resumen` alimenta la línea de reglas del brief mínimo: debe ser corto."""
    for regla in _reglas():
        resumen = str(regla.get("resumen", "")).strip()
        assert resumen, f"{regla['id']}: falta 'resumen' (lo usa el brief mínimo)"
        assert len(resumen) <= 45, f"{regla['id']}: resumen de {len(resumen)} car. (máx. 45)"
        assert "\n" not in resumen

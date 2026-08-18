"""Generador de briefs para agentes de IA.

Construye un resumen ejecutivo en formato Markdown (`CONTEXT.md`) diseñado para que un agente
pueda comprender **qué es el proyecto, por qué existe, qué cumple**, sus riesgos y su estado
en menos de 30 segundos.
"""

from __future__ import annotations

import os
from typing import List

from context_map.core.models import Edge, Node
from context_map.presentation.briefs.extractors import (
    calcular_stats,
    chequear_frescura,
    detectar_version,
    extraer_pendientes_manuales,
    extraer_proposito,
    reglas_negocio,
    reglas_negocio as _reglas_negocio,
)
from context_map.presentation.briefs.sections import (
    aviso_frescura,
    comandos_utiles,
    como_trabajar_aqui,
    eficiencia_tokenizacion,
    estado_proyecto,
    footer,
    header,
    que_es_y_por_que_existe,
    resumen_ejecutivo,
    riesgos_criticos,
    tareas_pendientes,
)


def generar_brief(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    readiness_score: int = 0,
    output_path: str = ".context-map/CONTEXT.md",
    project_dir: str = ".",
) -> str:
    """Genera el brief ejecutivo `CONTEXT.md` para los agentes de IA.

    Args:
        project_name (str): Nombre del proyecto.
        nodes (List[Node]): Nodos del mapa conceptual.
        edges (List[Edge]): Aristas del mapa conceptual.
        readiness_score (int): Score de readiness del proyecto.
        output_path (str): Ruta de salida para el archivo de brief.
        project_dir (str): Directorio raíz del proyecto (para leer README.md y el vault).

    Returns:
        str: Contenido Markdown del brief generado.
    """
    stats = calcular_stats(nodes)
    proposito = extraer_proposito(project_name, project_dir)
    version = detectar_version(project_dir)
    pendientes_manuales = extraer_pendientes_manuales(project_name, project_dir)
    frescura = chequear_frescura(project_name, project_dir)
    reglas = reglas_negocio(project_dir)

    sec_list = [
        header(project_name),
        que_es_y_por_que_existe(project_name, proposito),
        resumen_ejecutivo(project_name, stats, readiness_score, version),
        estado_proyecto(stats),
        aviso_frescura(frescura),
        riesgos_criticos(nodes),
        tareas_pendientes(nodes, pendientes_manuales),
        como_trabajar_aqui(project_name),
        comandos_utiles(),
        footer(),
    ]

    if reglas:
        sec_list.insert(4, reglas)

    texto_temp = "\n\n".join([s for s in sec_list if s])
    sec_list.insert(4, eficiencia_tokenizacion(texto_temp))

    brief_text = "\n\n".join([s for s in sec_list if s])

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief_text)

    return brief_text


# Aliases para retrocompatibilidad con pruebas unitarias
_header = header
_que_es_y_por_que_existe = que_es_y_por_que_existe
_resumen_ejecutivo = resumen_ejecutivo
_estado_proyecto = estado_proyecto
_aviso_frescura = aviso_frescura
_riesgos_criticos = riesgos_criticos
_tareas_pendientes = tareas_pendientes
_como_trabajar_aqui = como_trabajar_aqui
_comandos_utiles = comandos_utiles
_footer = footer
_calcular_stats = calcular_stats
_extraer_proposito = extraer_proposito
_detectar_version = detectar_version
_extraer_pendientes_manuales = extraer_pendientes_manuales
_chequear_frescura = chequear_frescura
_reglas_negocio = reglas_negocio


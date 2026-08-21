"""Módulo de cálculo de Complejidad Ciclomática de McCabe vía AST para ContextMap.

Calcula la densidad lógica y el número de caminos independientes por función o método
para identificar zonas de alto riesgo de mantenibilidad y deuda técnica.
"""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricaFuncion:
    """Representa la métrica de complejidad ciclomática de una función o método."""

    nombre: str
    linea_inicio: int
    complejidad: int
    es_alta_complejidad: bool
    clasificacion: str = "baja"  # 'baja' (1-5), 'media' (6-10), 'alta' (11-20), 'critica' (>20)


# Alias para retrocompatibilidad con domain.analysis.complexity
MetricaComplejidadFuncion = MetricaFuncion


@dataclass
class MetricaComplejidadArchivo:
    """Resumen consolidado de complejidad de un archivo completo."""

    ruta_relativa: str
    complejidad_total: int
    max_complejidad_funcion: int
    funciones_complejas: list[MetricaFuncion] = field(default_factory=list)


class _CicloVisitor(ast.NodeVisitor):
    """Visita los nodos del AST de una función para calcular la complejidad de McCabe."""

    def __init__(self) -> None:
        self.complejidad = 1  # Base de 1 punto de complejidad

    def visit_If(self, node: ast.If) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # Cada operador 'and' u 'or' añade un camino de decisión adicional
        self.complejidad += max(1, len(node.values) - 1)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complejidad += 1
        self.generic_visit(node)


def _clasificar_complejidad(cc: int) -> str:
    """Clasifica el nivel de riesgo según el valor de complejidad de McCabe."""
    if cc > 20:
        return "critica"
    if cc > 10:
        return "alta"
    if cc > 5:
        return "media"
    return "baja"


def calcular_complejidad_ciclomatica(codigo_fuente: str, umbral_alto: int = 10) -> list[MetricaFuncion]:
    """Calcula la complejidad ciclomática de McCabe para cada función en el código fuente.

    Args:
        codigo_fuente: String con el código Python a analizar.
        umbral_alto: Umbral a partir del cual se considera alta complejidad (default: 10).

    Returns:
        Lista de MetricaFuncion con el nombre, línea, complejidad, clasificación y estado de riesgo.
    """
    if not codigo_fuente or not codigo_fuente.strip():
        return []

    try:
        tree = ast.parse(codigo_fuente)
    except SyntaxError:
        return []

    resultados: list[MetricaFuncion] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _CicloVisitor()
            visitor.visit(node)
            comp = visitor.complejidad
            clasif = _clasificar_complejidad(comp)
            resultados.append(
                MetricaFuncion(
                    nombre=node.name,
                    linea_inicio=node.lineno,
                    complejidad=comp,
                    es_alta_complejidad=comp >= umbral_alto,
                    clasificacion=clasif,
                )
            )

    return resultados


def calcular_complejidad_archivo(ruta_archivo: str, ruta_base: str = ".") -> MetricaComplejidadArchivo | None:
    """Calcula la complejidad ciclomática de las funciones en un archivo Python en disco.

    Args:
        ruta_archivo: Ruta completa al archivo Python.
        ruta_base: Ruta base del proyecto para calcular ruta relativa.

    Returns:
        MetricaComplejidadArchivo con el resumen si es analizable, o None en error.
    """
    if not os.path.exists(ruta_archivo) or not ruta_archivo.endswith(".py"):
        return None

    try:
        with open(ruta_archivo, encoding="utf-8", errors="ignore") as f:
            code = f.read()
    except Exception as err:
        logger.debug("No se pudo leer el archivo %s: %s", ruta_archivo, err)
        return None

    try:
        ruta_rel = os.path.relpath(ruta_archivo, ruta_base) if os.path.isabs(ruta_archivo) else ruta_archivo
    except ValueError:
        ruta_rel = ruta_archivo

    funciones = calcular_complejidad_ciclomatica(code, umbral_alto=6)

    if not funciones:
        return MetricaComplejidadArchivo(
            ruta_relativa=ruta_rel,
            complejidad_total=1,
            max_complejidad_funcion=1,
        )

    max_cc = max(f.complejidad for f in funciones)
    complejas = [f for f in funciones if f.complejidad >= 6]

    return MetricaComplejidadArchivo(
        ruta_relativa=ruta_rel,
        complejidad_total=sum(f.complejidad for f in funciones),
        max_complejidad_funcion=max_cc,
        funciones_complejas=complejas,
    )


def analizar_archivo_ciclomatico(file_path: Path, umbral_alto: int = 10) -> list[MetricaFuncion]:
    """Analiza un archivo Python en disco y retorna sus métricas ciclomáticas.

    Args:
        file_path: Ruta al archivo .py.
        umbral_alto: Umbral de complejidad.

    Returns:
        Lista de métricas ciclomáticas por función.
    """
    if not file_path.is_file() or file_path.suffix != ".py":
        return []

    try:
        contenido = file_path.read_text(encoding="utf-8", errors="ignore")
        return calcular_complejidad_ciclomatica(contenido, umbral_alto=umbral_alto)
    except Exception:
        return []

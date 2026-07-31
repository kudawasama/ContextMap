"""Analizador de complejidad ciclomática avanzada para ContextMap.


Estima métricas de complejidad ciclomática de McCabe (puntos de decisión,
ramificaciones `if`, `for`, `while`, `try`, `except`) en funciones y clases.
"""

from __future__ import annotations

import ast
import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class MetricaComplejidadFuncion:
    """Métrica individual de complejidad de una función o método."""

    nombre: str
    linea_inicio: int
    complejidad: int
    clasificacion: str  # 'baja' (1-5), 'media' (6-10), 'alta' (11-20), 'critica' (>20)


@dataclass
class MetricaComplejidadArchivo:
    """Resumen de complejidad de un archivo completo."""

    ruta_relativa: str
    complejidad_total: int
    max_complejidad_funcion: int
    funciones_complejas: list[MetricaComplejidadFuncion] = field(default_factory=list)


class _McCabeVisitor(ast.NodeVisitor):
    """Visitador AST para contar puntos de decisión en una función."""

    def __init__(self) -> None:
        self.complejidad = 1

    def visit_If(self, node: ast.If) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self.complejidad += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.complejidad += len(node.values) - 1
        self.generic_visit(node)


def calcular_complejidad_archivo(ruta_archivo: str, ruta_base: str = ".") -> MetricaComplejidadArchivo | None:
    """Calcula la complejidad ciclomática de las funciones en un archivo Python.

    Args:
        ruta_archivo (str): Ruta completa al archivo Python.
        ruta_base (str): Ruta base del proyecto para calcular ruta relativa.

    Returns:
        Optional[MetricaComplejidadArchivo]: Métricas del archivo si es analizable.
    """
    if not os.path.exists(ruta_archivo) or not ruta_archivo.endswith(".py"):
        return None

    try:
        with open(ruta_archivo, encoding="utf-8", errors="ignore") as f:
            code = f.read()

        tree = ast.parse(code, filename=ruta_archivo)
    except Exception as err:
        logger.debug("No se pudo analizar AST de %s: %s", ruta_archivo, err)
        return None

    try:
        ruta_rel = os.path.relpath(ruta_archivo, ruta_base) if os.path.isabs(ruta_archivo) else ruta_archivo
    except ValueError:
        ruta_rel = ruta_archivo
    funciones: list[MetricaComplejidadFuncion] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _McCabeVisitor()
            visitor.visit(node)
            cc = visitor.complejidad
            clasif = "baja"
            if cc > 20:
                clasif = "critica"
            elif cc > 10:
                clasif = "alta"
            elif cc > 5:
                clasif = "media"

            funciones.append(
                MetricaComplejidadFuncion(
                    nombre=node.name,
                    linea_inicio=node.lineno,
                    complejidad=cc,
                    clasificacion=clasif,
                )
            )

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

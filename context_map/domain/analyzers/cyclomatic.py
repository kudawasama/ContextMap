"""Módulo de cálculo de Complejidad Ciclomática de McCabe vía AST para ContextMap.

Calcula la densidad lógica y el número de caminos independientes por función o método
para identificar zonas de alto riesgo de mantenibilidad.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class MetricaFuncion:
    """Representa la métrica de complejidad ciclomática de una función o método."""

    nombre: str
    linea_inicio: int
    complejidad: int
    es_alta_complejidad: bool


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


def calcular_complejidad_ciclomatica(codigo_fuente: str, umbral_alto: int = 10) -> List[MetricaFuncion]:
    """Calcula la complejidad ciclomática de McCabe para cada función en el código fuente.

    Args:
        codigo_fuente: String con el código Python a analizar.
        umbral_alto: Umbral a partir del cual se considera alta complejidad (default: 10).

    Returns:
        Lista de MetricaFuncion con el nombre, línea, complejidad y si excede el umbral.
    """
    if not codigo_fuente or not codigo_fuente.strip():
        return []

    try:
        tree = ast.parse(codigo_fuente)
    except SyntaxError:
        return []

    resultados: List[MetricaFuncion] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            visitor = _CicloVisitor()
            visitor.visit(node)
            comp = visitor.complejidad
            resultados.append(
                MetricaFuncion(
                    nombre=node.name,
                    linea_inicio=node.lineno,
                    complejidad=comp,
                    es_alta_complejidad=comp >= umbral_alto,
                )
            )

    return resultados


def analizar_archivo_ciclomatico(file_path: Path, umbral_alto: int = 10) -> List[MetricaFuncion]:
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

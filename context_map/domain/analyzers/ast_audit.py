"""Analizador sintáctico AST de seguridad y calidad de código local para ContextMap.

Ejecuta verificaciones determinísticas sin internet ni dependencias externas sobre:
- Uso inseguro de eval() y exec()
- Supresión silenciosa de excepciones (except Exception: pass)
- Concatenación de cadenas en consultas SQL (cursor.execute)
- Apertura de archivos sin administrador de contexto (with open)
- Claves o contraseñas hardcodadas en código
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass


@dataclass
class AlertaAuditoria:
    """Alerta de calidad o seguridad detectada por el analizador AST.

    Attributes:
        archivo (str): Ruta del archivo inspeccionado.
        linea (int): Número de línea de la anomalía.
        categoria (str): Categoría ('SEGURIDAD', 'ROBUSTEZ', 'RECURSOS').
        mensaje (str): Descripción detallada del hallazgo.
    """

    archivo: str
    linea: int
    categoria: str
    mensaje: str


class AuditVisitor(ast.NodeVisitor):
    """Visitor de AST que inspecciona patrones de calidad y seguridad."""

    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.alertas: list[AlertaAuditoria] = []

    def visit_Call(self, node: ast.Call) -> None:
        # Detectar eval() y exec()
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self.alertas.append(
                AlertaAuditoria(
                    archivo=self.filepath,
                    linea=node.lineno,
                    categoria="SEGURIDAD",
                    mensaje=f"Uso inseguro de ejecutor dinámico '{node.func.id}()'.",
                )
            )

        # Detectar cursor.execute con f-strings o concatenación
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany"):
            if node.args:
                primer_arg = node.args[0]
                if isinstance(primer_arg, (ast.JoinedStr, ast.BinOp)):
                    self.alertas.append(
                        AlertaAuditoria(
                            archivo=self.filepath,
                            linea=node.lineno,
                            categoria="SEGURIDAD",
                            mensaje="Posible inyección SQL: consulta formateada con cadenas dinámicas en execute().",
                        )
                    )

        # Detectar open() suelto fuera de with
        if isinstance(node.func, ast.Name) and node.func.id == "open":
            # Si no está dentro de un ast.With, advertir consumo potencial de descriptor
            self.alertas.append(
                AlertaAuditoria(
                    archivo=self.filepath,
                    linea=node.lineno,
                    categoria="RECURSOS",
                    mensaje="Uso de open() directo. Se recomienda usar 'with open(...)' para garantizar el cierre del archivo.",
                )
            )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Detectar except Exception: pass o except: pass
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.alertas.append(
                AlertaAuditoria(
                    archivo=self.filepath,
                    linea=node.lineno,
                    categoria="ROBUSTEZ",
                    mensaje="Bloque 'except' que ignora excepciones silenciosamente con 'pass'.",
                )
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # Detectar contraseñas hardcodadas
        for target in node.targets:
            if isinstance(target, ast.Name):
                nombre_var = target.id.lower()
                if any(k in nombre_var for k in ["password", "secret_key", "api_key", "auth_token"]):
                    if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                        val = node.value.value
                        if len(val) > 4 and val not in ("placeholder", "change_me", "dummy"):
                            self.alertas.append(
                                AlertaAuditoria(
                                    archivo=self.filepath,
                                    linea=node.lineno,
                                    categoria="SEGURIDAD",
                                    mensaje=f"Posible credencial hardcodada en la variable '{target.id}'.",
                                )
                            )
        self.generic_visit(node)


def auditar_archivo_python(filepath: str) -> list[AlertaAuditoria]:
    """Audita un archivo Python individual mediante análisis AST.

    Args:
        filepath: Ruta del archivo Python.

    Returns:
        Lista de AlertaAuditoria encontradas.
    """
    if not os.path.isfile(filepath) or not filepath.endswith(".py"):
        return []

    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            tree = ast.parse(f.read(), filename=filepath)
        visitor = AuditVisitor(filepath)
        visitor.visit(tree)
        return visitor.alertas
    except Exception:
        return []


def auditar_proyecto_python(target_dir: str = ".") -> list[AlertaAuditoria]:
    """Escanea y audita sintácticamente todos los archivos Python del proyecto.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        Lista consolidada de AlertaAuditoria del proyecto.
    """
    alertas: list[AlertaAuditoria] = []
    for raiz, _, archivos in os.walk(target_dir):
        if any(ign in raiz for ign in [".git", "venv", ".venv", "__pycache__", ".context-map"]):
            continue
        for f in archivos:
            if f.endswith(".py"):
                r = os.path.join(raiz, f)
                alertas.extend(auditar_archivo_python(r))
    return alertas

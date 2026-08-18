"""Módulo de inferencia sintáctica de propósito AST para ContextMap.

Infiere la intención y resumen de archivos Python carentes de docstrings
analizando librerías importadas, tipos de retorno, decoradores y estructuras sintácticas.
"""

import ast
from pathlib import Path
from typing import List, Optional, Set


class ASTSummaryExtractor:
    """Extractor de síntesis basada en la estructura sintáctica del árbol AST."""

    _MAPPING_LIBRERIAS = {
        "fastapi": "API REST con framework FastAPI",
        "flask": "Aplicación web / endpoint Flask",
        "django": "Componente o vista del framework Django",
        "requests": "Cliente HTTP / cliente de API externa",
        "httpx": "Cliente HTTP asíncrono / cliente de servicio web",
        "pandas": "Procesamiento y análisis de datos estadísticos",
        "polars": "Procesamiento de datos de alto rendimiento con Polars",
        "numpy": "Cálculo numérico y operaciones matriciales",
        "pytest": "Suite o utilidades de pruebas automatizadas",
        "unittest": "Pruebas unitarias de framework estándar",
        "sqlalchemy": "Persistencia de datos y modelos ORM SQLAlchemy",
        "sqlite3": "Persistencia local en base de datos SQLite",
        "torch": "Modelo o pipeline de Deep Learning con PyTorch",
        "transformers": "Modelo o inferencia de lenguaje / Transformers",
        "argparse": "Interfaz de línea de comandos (CLI)",
        "click": "Comandos e interfaz CLI con Click",
    }

    def __init__(self, code_text: str) -> None:
        """Inicializa el extractor con el código fuente en texto.

        Args:
            code_text: Cadena de texto con el código Python a analizar.
        """
        self.code_text = code_text
        self.imports: Set[str] = set()
        self.funciones: List[str] = []
        self.clases: List[str] = []
        self.docstring_modulo: Optional[str] = None
        self._analizar_ast()

    def _analizar_ast(self) -> None:
        """Recorre el árbol AST para extraer componentes clave."""
        if not self.code_text or not self.code_text.strip():
            return

        try:
            tree = ast.parse(self.code_text)
        except SyntaxError:
            return

        self.docstring_modulo = ast.get_docstring(tree)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.imports.add(node.module.split(".")[0])
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.funciones.append(node.name)
            elif isinstance(node, ast.ClassDef):
                self.clases.append(node.name)

    def inferir_resumen(self) -> str:
        """Infiere una descripción sintetizada y humanizada del propósito del archivo.

        Returns:
            String con el resumen sintáctico inferido.
        """
        # 1. Si existe docstring formal de módulo, priorizarlo
        if self.docstring_modulo:
            primera_linea = self.docstring_modulo.strip().split("\n")[0]
            if len(primera_linea) > 10:
                return primera_linea

        # 2. Inferencia basada en librerías importadas
        roles_detectados: List[str] = []
        for lib, desc in self._MAPPING_LIBRERIAS.items():
            if lib in self.imports:
                roles_detectados.append(desc)

        componentes: List[str] = []
        if self.clases:
            componentes.append(f"clases ({', '.join(self.clases[:3])})")
        if self.funciones:
            componentes.append(f"funciones ({', '.join(self.funciones[:3])})")

        partes_resumen: List[str] = []

        if roles_detectados:
            partes_resumen.append(f"Módulo enfocado en {', '.join(roles_detectados[:2])}.")

        if componentes:
            partes_resumen.append(f"Define {', '.join(componentes)}.")

        if partes_resumen:
            return " ".join(partes_resumen)

        return "Módulo Python con lógica funcional del proyecto."


def inferir_resumen_archivo(file_path: Path) -> str:
    """Función de utilidad para inferir el resumen de un archivo .py en disco.

    Args:
        file_path: Ruta al archivo .py.

    Returns:
        String con el resumen sintetizado.
    """
    if not file_path.is_file() or file_path.suffix != ".py":
        return ""

    try:
        contenido = file_path.read_text(encoding="utf-8", errors="ignore")
        extractor = ASTSummaryExtractor(contenido)
        return extractor.inferir_resumen()
    except Exception:
        return "Módulo Python del proyecto."

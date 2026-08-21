"""Módulo de extracción de conceptos de negocio por frecuencia de términos (TF-IDF local).

Identifica los términos de dominio dominantes del proyecto a partir de nombres de clases,
módulos y funciones sin requerir servicios en la nube.
"""

import re
from collections import Counter
from pathlib import Path


class DomainConceptExtractor:
    """Extractor local de conceptos de negocio dominantes."""

    _PALABRAS_RESERVADAS = {
        "def", "class", "import", "from", "return", "self", "none", "true", "false",
        "init", "str", "int", "dict", "list", "bool", "float", "path", "file", "node",
        "data", "test", "main", "get", "set", "update", "delete", "create", "run",
    }

    def __init__(self) -> None:
        self.contador_terminos: Counter[str] = Counter()

    def registrar_texto(self, texto: str) -> None:
        """Registra e indexa un texto para el recuento de términos de dominio.

        Args:
            texto: Cadena de texto a procesar (nombres de clases, funciones, módulos).
        """
        if not texto:
            return

        # Separar camelCase y snake_case
        palabras = re.findall(r"[A-Za-z][a-z0-9]+|[A-Z]+(?=[A-Z][a-z0-9]|\b)", texto)

        for p in palabras:
            p_lower = p.lower()
            if len(p_lower) >= 4 and p_lower not in self._PALABRAS_RESERVADAS:
                self.contador_terminos[p_lower.upper()] += 1

    def obtener_conceptos_dominantes(self, top_n: int = 5) -> list[str]:
        """Recupera los N conceptos de negocio más relevantes identificados.

        Args:
            top_n: Cantidad de conceptos principales a retornar.

        Returns:
            Lista de cadenas de texto con los conceptos en mayúsculas.
        """
        return [termino for termino, _ in self.contador_terminos.most_common(top_n)]


def extraer_conceptos_proyecto(project_dir: Path, top_n: int = 5) -> list[str]:
    """Extrae los conceptos de negocio dominantes de un directorio de proyecto.

    Args:
        project_dir: Ruta raíz del proyecto.
        top_n: Número de conceptos a retornar.

    Returns:
        Lista de conceptos dominantes.
    """
    extractor = DomainConceptExtractor()

    for path in Path(project_dir).rglob("*.py"):
        if any(part.startswith(".") or part in ("venv", "build", "dist") for part in path.parts):
            continue
        extractor.registrar_texto(path.stem)
        try:
            contenido = path.read_text(encoding="utf-8", errors="ignore")
            # Extraer nombres de clases y funciones
            for match in re.finditer(r"(?:class|def)\s+([A-Za-z_][A-Za-z0-9_]*)", contenido):
                extractor.registrar_texto(match.group(1))
        except Exception:
            pass

    return extractor.obtener_conceptos_dominantes(top_n=top_n)

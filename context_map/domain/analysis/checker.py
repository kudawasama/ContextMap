from __future__ import annotations

"""Analizador de readiness para Context Map.

Evalúa qué tan preparado está un proyecto para que un agente de IA trabaje en él,
analizando indicadores de documentación, tests, configuración y CI/CD.
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class SenalReadiness:
    """Una señal o indicador individual de readiness del proyecto.

    Attributes:
        nombre (str): Nombre de la señal.
        peso (int): Peso de la señal en la evaluación (1-10).
        presente (bool): Indica si la señal está presente en el repositorio.
        detalle (str): Descripción detallada del indicador.
    """

    nombre: str
    peso: int
    presente: bool
    detalle: str = ""


@dataclass
class ResultadoReadiness:
    """Resultado del análisis completo de readiness del proyecto.

    Attributes:
        ruta_raiz (str): Ruta raíz del proyecto analizado.
        senales (List[SenalReadiness]): Lista de señales evaluadas.
        score (int): Puntaje global calculado (0-100).
        veredicto (str): Veredicto final ('ready', 'partial', 'not-ready').
        gaps (List[str]): Lista de elementos o señales faltantes.
        sugerencias (List[str]): Lista de recomendaciones de mejora.
    """

    ruta_raiz: str
    senales: List[SenalReadiness] = field(default_factory=list)
    score: int = 0
    veredicto: str = "unknown"
    gaps: List[str] = field(default_factory=list)
    sugerencias: List[str] = field(default_factory=list)


def _verificar_archivo(ruta: str, nombres: List[str]) -> bool:
    """Verifica si existe al menos uno de los archivos indicados en la ruta raíz.

    Args:
        ruta (str): Ruta del directorio base.
        nombres (List[str]): Lista de nombres de archivos a buscar.

    Returns:
        bool: True si existe al menos un archivo, False de lo contrario.
    """
    for nombre in nombres:
        if os.path.exists(os.path.join(ruta, nombre)):
            return True
    return False


def _verificar_directorio(ruta: str, nombres: List[str]) -> bool:
    """Verifica si existe al menos uno de los directorios indicados.

    Args:
        ruta (str): Ruta del directorio base.
        nombres (List[str]): Lista de nombres de carpetas a buscar.

    Returns:
        bool: True si existe alguna carpeta, False de lo contrario.
    """
    for nombre in nombres:
        if os.path.isdir(os.path.join(ruta, nombre)):
            return True
    return False


def analizar_readiness(ruta_raiz: str) -> ResultadoReadiness:
    """Ejecuta la auditoría de readiness del proyecto en la ruta especificada.

    Args:
        ruta_raiz (str): Ruta al directorio raíz del proyecto.

    Returns:
        ResultadoReadiness: Objeto con el puntaje, señales y recomendaciones.
    """
    resultado = ResultadoReadiness(ruta_raiz=ruta_raiz)

    senales = [
        SenalReadiness(
            nombre="README",
            peso=10,
            presente=_verificar_archivo(ruta_raiz, ["README.md", "README.rst", "README.txt"]),
            detalle="Archivo de documentación principal",
        ),
        SenalReadiness(
            nombre="CHANGELOG",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["CHANGELOG.md", "CHANGES.md", "HISTORY.md"]),
            detalle="Historial de cambios",
        ),
        SenalReadiness(
            nombre="LICENSE",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["LICENSE", "LICENSE.md", "LICENSE.txt"]),
            detalle="Licencia del proyecto",
        ),
        SenalReadiness(
            nombre="pyproject.toml/setup.py",
            peso=8,
            presente=_verificar_archivo(ruta_raiz, ["pyproject.toml", "setup.py", "setup.cfg"]),
            detalle="Configuración de paquete Python",
        ),
        SenalReadiness(
            nombre="requirements.txt",
            peso=6,
            presente=_verificar_archivo(ruta_raiz, ["requirements.txt", "requirements-dev.txt"]),
            detalle="Dependencias del proyecto",
        ),
        SenalReadiness(
            nombre=".gitignore",
            peso=4,
            presente=_verificar_archivo(ruta_raiz, [".gitignore"]),
            detalle="Archivos ignorados por git",
        ),
        SenalReadiness(
            nombre="Tests",
            peso=9,
            presente=_verificar_directorio(ruta_raiz, ["tests", "test", "__tests__"]),
            detalle="Directorio de pruebas",
        ),
        SenalReadiness(
            nombre="pytest.ini/conftest",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["pytest.ini", "conftest.py", "tox.ini"]),
            detalle="Configuración de testing",
        ),
        SenalReadiness(
            nombre="CI/CD",
            peso=7,
            presente=_verificar_directorio(ruta_raiz, [".github", ".gitlab-ci.yml", ".circleci"]),
            detalle="Integración continua",
        ),
        SenalReadiness(
            nombre="AGENTS.md/CLAUDE.md",
            peso=6,
            presente=_verificar_archivo(ruta_raiz, ["AGENTS.md", "CLAUDE.md", "CURSOR.md"]),
            detalle="Instrucciones para agentes de IA",
        ),
        SenalReadiness(
            nombre="Makefile/Justfile",
            peso=4,
            presente=_verificar_archivo(ruta_raiz, ["Makefile", "Justfile"]),
            detalle="Comandos comunes del proyecto",
        ),
    ]

    resultado.senales = senales

    peso_total = sum(s.peso for s in senales)
    peso_presente = sum(s.peso for s in senales if s.presente)
    resultado.score = int((peso_presente / peso_total) * 100) if peso_total > 0 else 0

    resultado.gaps = [s.nombre for s in senales if not s.presente]

    if not any(s.nombre == "README" and s.presente for s in senales):
        resultado.sugerencias.append("Crear un README.md con descripción del proyecto")
    if not any(s.nombre == "Tests" and s.presente for s in senales):
        resultado.sugerencias.append("Agregar directorio de tests")
    if not any(s.nombre == "CI/CD" and s.presente for s in senales):
        resultado.sugerencias.append("Configurar CI/CD (GitHub Actions)")
    if not any(s.nombre == "AGENTS.md/CLAUDE.md" and s.presente for s in senales):
        resultado.sugerencias.append("Crear AGENTS.md con instrucciones para agentes")

    if resultado.score >= 80:
        resultado.veredicto = "ready"
    elif resultado.score >= 50:
        resultado.veredicto = "partial"
    else:
        resultado.veredicto = "not-ready"

    return resultado


def formatear_readiness(resultado: ResultadoReadiness) -> str:
    """Formatea el resultado del análisis de readiness como Markdown legible.

    Args:
        resultado (ResultadoReadiness): Resultado del análisis.

    Returns:
        str: Reporte formateado en Markdown.
    """
    lineas = [
        "# Readiness Report",
        "",
        f"**Proyecto**: {os.path.basename(resultado.ruta_raiz)}",
        f"**Score**: {resultado.score}/100",
        f"**Veredicto**: {resultado.veredicto}",
        "",
        "## Señales",
        "",
    ]

    for s in resultado.senales:
        icono = "[OK]" if s.presente else "[X]"
        lineas.append(f"- {icono} {s.nombre} (peso: {s.peso})")
        if s.detalle and not s.presente:
            lineas.append(f"  - _{s.detalle}_")

    if resultado.gaps:
        lineas.extend(["", "## Faltante", ""])
        for gap in resultado.gaps:
            lineas.append(f"- {gap}")

    if resultado.sugerencias:
        lineas.extend(["", "## Sugerencias", ""])
        for sug in resultado.sugerencias:
            lineas.append(f"- {sug}")

    return "\n".join(lineas)

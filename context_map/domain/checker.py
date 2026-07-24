"""Analizador de readiness para Context Map Generator.

Evalúa qué tan listo está un proyecto para que un agente trabaje en él.
"""

from __future__ import annotations

import os
from typing import List, Dict
from dataclasses import dataclass, field


@dataclass
class SenalReadiness:
    """Una señal de readiness del proyecto."""
    nombre: str
    peso: int  # 1-10
    presente: bool
    detalle: str = ""


@dataclass
class ResultadoReadiness:
    """Resultado del análisis de readiness."""
    ruta_raiz: str
    senales: List[SenalReadiness] = field(default_factory=list)
    score: int = 0
    veredicto: str = "unknown"  # ready, not-ready, partial
    gaps: List[str] = field(default_factory=list)
    sugerencias: List[str] = field(default_factory=list)


def _verificar_archivo(ruta: str, nombres: List[str]) -> bool:
    """Verifica si existe alguno de los archivos."""
    for nombre in nombres:
        if os.path.exists(os.path.join(ruta, nombre)):
            return True
    return False


def _verificar_directorio(ruta: str, nombres: List[str]) -> bool:
    """Verifica si existe alguno de los directorios."""
    for nombre in nombres:
        if os.path.isdir(os.path.join(ruta, nombre)):
            return True
    return False


def analizar_readiness(ruta_raiz: str) -> ResultadoReadiness:
    """Analiza qué tan listo está un proyecto.

    Returns:
        ResultadoReadiness con score, gaps y sugerencias
    """
    resultado = ResultadoReadiness(ruta_raiz=ruta_raiz)

    # Señales de readiness con pesos
    senales = [
        # Documentación (peso 10)
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

        # Configuración (peso 8)
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

        # Testing (peso 9)
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

        # CI/CD (peso 7)
        SenalReadiness(
            nombre="CI/CD",
            peso=7,
            presente=_verificar_directorio(ruta_raiz, [".github", ".gitlab-ci.yml", ".circleci"]),
            detalle="Integración continua",
        ),

        # Instrucciones para agentes (peso 6)
        SenalReadiness(
            nombre="AGENTS.md/CLAUDE.md",
            peso=6,
            presente=_verificar_archivo(ruta_raiz, ["AGENTS.md", "CLAUDE.md", "CURSOR.md"]),
            detalle="Instrucciones para agentes de IA",
        ),

        # Makefile/justfile (peso 4)
        SenalReadiness(
            nombre="Makefile/Justfile",
            peso=4,
            presente=_verificar_archivo(ruta_raiz, ["Makefile", "Justfile"]),
            detalle="Comandos comunes del proyecto",
        ),
    ]

    resultado.senales = senales

    # Calcular score
    peso_total = sum(s.peso for s in senales)
    peso_presente = sum(s.peso for s in senales if s.presente)
    resultado.score = int((peso_presente / peso_total) * 100) if peso_total > 0 else 0

    # Identificar gaps
    resultado.gaps = [s.nombre for s in senales if not s.presente]

    # Generar sugerencias
    if not any(s.nombre == "README" and s.presente for s in senales):
        resultado.sugerencias.append("Crear un README.md con descripción del proyecto")
    if not any(s.nombre == "Tests" and s.presente for s in senales):
        resultado.sugerencias.append("Agregar directorio de tests")
    if not any(s.nombre == "CI/CD" and s.presente for s in senales):
        resultado.sugerencias.append("Configurar CI/CD (GitHub Actions)")
    if not any(s.nombre == "AGENTS.md/CLAUDE.md" and s.presente for s in senales):
        resultado.sugerencias.append("Crear AGENTS.md con instrucciones para agentes")

    # Veredicto
    if resultado.score >= 80:
        resultado.veredicto = "ready"
    elif resultado.score >= 50:
        resultado.veredicto = "partial"
    else:
        resultado.veredicto = "not-ready"

    return resultado


def formatear_readiness(resultado: ResultadoReadiness) -> str:
    """Formatea el resultado como texto legible."""
    lineas = [
        f"# Readiness Report",
        f"",
        f"**Proyecto**: {os.path.basename(resultado.ruta_raiz)}",
        f"**Score**: {resultado.score}/100",
        f"**Veredicto**: {resultado.veredicto}",
        f"",
        f"## Señales",
        f"",
    ]

    for s in resultado.senales:
        icono = "✅" if s.presente else "❌"
        lineas.append(f"- {icono} {s.nombre} (peso: {s.peso})")
        if s.detalle and not s.presente:
            lineas.append(f"  - _{s.detalle}_")

    if resultado.gaps:
        lineas.extend([
            f"",
            f"## Faltante",
            f"",
        ])
        for gap in resultado.gaps:
            lineas.append(f"- {gap}")

    if resultado.sugerencias:
        lineas.extend([
            f"",
            f"## Sugerencias",
            f"",
        ])
        for sug in resultado.sugerencias:
            lineas.append(f"- {sug}")

    return "\n".join(lineas)

"""Dataclasses de modelos para el análisis de readiness y salud del proyecto."""

from __future__ import annotations

from dataclasses import dataclass, field


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
    senales: list[SenalReadiness] = field(default_factory=list)
    score: int = 0
    veredicto: str = "unknown"
    gaps: list[str] = field(default_factory=list)
    sugerencias: list[str] = field(default_factory=list)
    frescura: dict[str, object] = field(default_factory=dict)
    cobertura_memoria: dict[str, int] = field(default_factory=dict)
    nombre_fragmentado: str = ""

"""Analizador de readiness para Context Map.

Fachada modularizada que re-exporta evaluadores, modelos y formateadores
de análisis de readiness de proyecto.
"""

from __future__ import annotations

from context_map.domain.analysis.models import ResultadoReadiness, SenalReadiness
from context_map.domain.analysis.reporting import formatear_readiness as _formatear_readiness_base
from context_map.domain.analysis.signals import (
    analizar_readiness,
    cobertura_memoria_viva as _cobertura_memoria_viva,
    contar_eventos_events_jsonl as _contar_eventos_events_jsonl,
    ejecutar_git as _ejecutar_git,
    inconsistencia_nombre as _inconsistencia_nombre,
    salud_vault as _salud_vault,
    sesiones_posteriores as _sesiones_posteriores,
    timestamp_build as _timestamp_build,
    ultima_actividad as _ultima_actividad,
    verificar_archivo as _verificar_archivo,
    verificar_directorio as _verificar_directorio,
)
from context_map.infrastructure.integrations.hermes import leer_sesiones


def formatear_readiness(resultado: ResultadoReadiness) -> str:
    """Formatea el resultado del análisis de readiness como Markdown legible."""
    return _formatear_readiness_base(resultado, salud_vault_fn=_salud_vault)


__all__ = [
    "SenalReadiness",
    "ResultadoReadiness",
    "analizar_readiness",
    "formatear_readiness",
    "leer_sesiones",
    "_verificar_archivo",
    "_verificar_directorio",
    "_salud_vault",
    "_ejecutar_git",
    "_timestamp_build",
    "_ultima_actividad",
    "_sesiones_posteriores",
    "_contar_eventos_events_jsonl",
    "_cobertura_memoria_viva",
    "_inconsistencia_nombre",
]

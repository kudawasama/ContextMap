"""Submódulo de generación de briefs del sistema."""

from context_map.presentation.briefs.brief import generar_brief
from context_map.presentation.briefs.agents import generar_instrucciones_agentes

__all__ = ["generar_brief", "generar_instrucciones_agentes"]

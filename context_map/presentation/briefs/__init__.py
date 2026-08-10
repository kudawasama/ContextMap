"""Submódulo de generación de briefs del sistema."""

from __future__ import annotations

from context_map.presentation.briefs.agents import generar_instrucciones_agentes
from context_map.presentation.briefs.brief import generar_brief
from context_map.presentation.briefs.skill import generar_skill_contextmap

__all__ = ["generar_brief", "generar_instrucciones_agentes", "generar_skill_contextmap"]

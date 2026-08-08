"""Adaptación del ecosistema agéntico del proyecto (dominio).

Detecta el stack técnico y los IDEs/agentes presentes, y genera o
actualiza las reglas de gobernanza específicas para cada herramienta.
"""

from __future__ import annotations

from context_map.domain.ecosystem.adaptador import adaptar_ecosistema
from context_map.domain.ecosystem.detector import (
    EcosistemaInfo,
    IDEInfo,
    StackInfo,
    detectar_ecosistema,
    detectar_ide,
    detectar_stack,
)

__all__ = [
    "EcosistemaInfo",
    "IDEInfo",
    "StackInfo",
    "adaptar_ecosistema",
    "detectar_ecosistema",
    "detectar_ide",
    "detectar_stack",
]

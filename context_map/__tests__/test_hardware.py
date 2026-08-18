"""Pruebas unitarias para el módulo context_map.domain.health.hardware."""

import pytest
from context_map.domain.health.hardware import evaluar_hardware_pc, EspecificacionesHardware


def test_evaluar_hardware_pc() -> None:
    """Verifica que el diagnóstico de hardware retorne un objeto EspecificacionesHardware válido."""
    hw = evaluar_hardware_pc()
    assert isinstance(hw, EspecificacionesHardware)
    assert hw.ram_total_gb > 0
    assert hw.cpu_cores >= 1
    assert hw.mensaje_diagnostico != ""

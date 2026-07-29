"""Capa de Dominio de context_map.

Re-exporta símbolos desde sus submódulos correspondientes:
- `analysis`: Análisis de readiness.
- `health`: Chequeos de salud (doctor).
- `reporting`: Reportes periódicos.
- `scanning`: Escáner de código.
- `synchronization`: Sincronización incremental del mapa.
"""

from context_map.domain.analysis import (
    analizar_readiness,
    formatear_readiness,
    ResultadoReadiness,
    SenalReadiness,
)
from context_map.domain.health import (
    run as run_doctor,
    DoctorReport,
    DoctorCheck,
)
from context_map.domain.reporting import (
    generar_semanal,
    guardar_reporte,
)
from context_map.domain.scanning import (
    escanear_y_generar_eventos,
    guardar_eventos_escaneados,
)
from context_map.domain.synchronization import (
    sync_incremental,
)

__all__ = [
    "analizar_readiness",
    "formatear_readiness",
    "ResultadoReadiness",
    "SenalReadiness",
    "run_doctor",
    "DoctorReport",
    "DoctorCheck",
    "generar_semanal",
    "guardar_reporte",
    "escanear_y_generar_eventos",
    "guardar_eventos_escaneados",
    "sync_incremental",
]

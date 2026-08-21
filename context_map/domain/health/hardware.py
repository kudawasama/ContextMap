"""Módulo de evaluación de hardware y recomendación de modelos ligeros para ContextMap.

Detecta la memoria RAM total y libre del PC para recomendar modelos de Ollama de bajo
consumo de memoria y prevenir bloqueos del sistema.
"""

import ctypes
import os
import sys
from dataclasses import dataclass


@dataclass
class EspecificacionesHardware:
    """Representa el diagnóstico de capacidad de hardware del PC."""

    ram_total_gb: float
    ram_libre_gb: float
    cpu_cores: int
    es_apto_para_ollama: bool
    modelo_recomendado: str
    modelos_compatibles: list[str]
    mensaje_diagnostico: str


def obtener_memoria_ram_windows() -> tuple[float, float]:
    """Obtiene la memoria RAM total y disponible en Windows usando ctypes."""
    try:
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_gb = round(stat.ullTotalPhys / (1024**3), 2)
            avail_gb = round(stat.ullAvailPhys / (1024**3), 2)
            return total_gb, avail_gb
    except Exception:
        pass
    return 8.0, 4.0  # Fallback seguro


def evaluar_hardware_pc() -> EspecificacionesHardware:
    """Audita los recursos del PC y determina qué modelo ligero de Ollama se adapta mejor.

    Returns:
        EspecificacionesHardware con la RAM, aptitud y modelo recomendado.
    """
    cpu_cores = os.cpu_count() or 4

    if sys.platform == "win32":
        total_ram, free_ram = obtener_memoria_ram_windows()
    else:
        try:
            total_ram = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024**3), 2)
            free_ram = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES") / (1024**3), 2)
        except Exception:
            total_ram, free_ram = 8.0, 4.0

    # Límite mínimo de seguridad: 3.5 GB RAM disponible
    if free_ram < 3.5:
        return EspecificacionesHardware(
            ram_total_gb=total_ram,
            ram_libre_gb=free_ram,
            cpu_cores=cpu_cores,
            es_apto_para_ollama=False,
            modelo_recomendado="ninguno",
            modelos_compatibles=[],
            mensaje_diagnostico=(
                f"⚠️ RAM disponible insuficiente ({free_ram} GB libres). "
                "Se requiere al menos 3.5 GB libres para ejecutar Ollama local sin congelar el PC. "
                "ContextMap utilizará el enriquecedor sintáctico AST offline (gratis, instantáneo y sin RAM)."
            ),
        )

    # Selección de modelos ultraligeros por capacidad
    if free_ram < 7.0:
        modelo_rec = "qwen2.5-coder:1.5b"
        compatibles = ["qwen2.5-coder:1.5b", "qwen2.5-coder:0.5b", "llama3.2:1b"]
        msg = f"✅ PC con RAM ajustada ({free_ram} GB libres). Se recomienda el modelo ultraligero '{modelo_rec}' (~1.2 GB RAM)."
    elif free_ram < 14.0:
        modelo_rec = "qwen2.5-coder:7b"
        compatibles = ["qwen2.5-coder:7b", "qwen2.5-coder:1.5b", "llama3.2:3b"]
        msg = f"✅ PC con capacidad media ({free_ram} GB libres). Se recomienda el modelo equilibrado '{modelo_rec}' (~4.7 GB RAM)."
    else:
        modelo_rec = "qwen2.5-coder:14b"
        compatibles = ["qwen2.5-coder:14b", "qwen2.5-coder:7b", "deepseek-coder:6.7b"]
        msg = f"🚀 PC de alto rendimiento ({free_ram} GB libres). Se recomienda el modelo avanzado '{modelo_rec}'."

    return EspecificacionesHardware(
        ram_total_gb=total_ram,
        ram_libre_gb=free_ram,
        cpu_cores=cpu_cores,
        es_apto_para_ollama=True,
        modelo_recomendado=modelo_rec,
        modelos_compatibles=compatibles,
        mensaje_diagnostico=msg,
    )

"""Submódulo de verificación de salud y diagnóstico del sistema."""

from __future__ import annotations

from context_map.domain.health.doctor import (
    DoctorCheck,
    DoctorReport,
    check_git_available,
    check_update_dir,
    check_vault_default,
    run,
)

run_doctor = run

__all__ = [
    "run",
    "run_doctor",
    "DoctorReport",
    "DoctorCheck",
    "check_git_available",
    "check_update_dir",
    "check_vault_default",
]

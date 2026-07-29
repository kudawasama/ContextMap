"""Submódulo de verificación de salud y diagnóstico del sistema."""

from context_map.domain.health.doctor import (
    run,
    DoctorReport,
    DoctorCheck,
    check_git_available,
    check_update_dir,
    check_vault_default,
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

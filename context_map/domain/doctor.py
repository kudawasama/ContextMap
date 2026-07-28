"""Domain: Doctor.

Diagnostica el entorno de ContextMap y aplica reparaciones cuando es posible.
Cada chequeo debe ser:
  - deterministico
  - sin efectos secundarios beyond de su reparacion
  - aislado de otros modulos
"""
from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class DoctorCheck:
    """Resultado de un chequeo individual."""

    name: str
    status: str = "OK"  # OK | WARN | FAIL
    message: str = ""
    fix_applied: bool = False
    fix_message: str = ""


@dataclass
class DoctorReport:
    """Agregado de resultados."""

    checks: List[DoctorCheck] = field(default_factory=list)

    def add(self, check: DoctorCheck) -> None:
        self.checks.append(check)

    @property
    def failed(self) -> List[DoctorCheck]:
        return [c for c in self.checks if c.status == "FAIL"]

    @property
    def warnings(self) -> List[DoctorCheck]:
        return [c for c in self.checks if c.status == "WARN"]

    @property
    def ok(self) -> bool:
        return len(self.failed) == 0


def _safe_rmtree(path: str) -> None:
    """Borra directorios de forma multiplataforma, con verificación posterior."""
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        # Windows puede retener archivos (antivirus, handles abiertos)
        if os.path.isdir(path):
            for attempt in range(3):
                shutil.rmtree(path, ignore_errors=True)
                if not os.path.isdir(path):
                    break
                # fallback: cmd rd
                try:
                    subprocess.run(
                        ["cmd", "/c", "rd", "/s", "/q", path],
                        capture_output=True, timeout=10,
                    )
                except Exception:
                    pass
                if not os.path.isdir(path):
                    break


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando capturando stdout/stderr para diagnóstico."""
    return subprocess.run(cmd, capture_output=True, text=True)


def check_update_dir(report: DoctorReport) -> None:
    """Chequea el directorio de actualizacion de ctxmap.

    Caso que detecta:
      - Existe ~/.context-map-update pero no es repo git valido
    Repara:
      - Borra el directorio corrupto para permitir un update limpio posterior.
    """
    update_dir = os.path.join(os.path.expanduser("~"), ".context-map-update")
    check = DoctorCheck(name="update_dir")

    if not os.path.exists(update_dir):
        check.status = "OK"
        check.message = "~/.context-map-update no existe, sin anomalias."
        report.add(check)
        return

    is_git = _run(["git", "-C", update_dir, "rev-parse", "--is-inside-work-tree"])
    if is_git.returncode == 0 and is_git.stdout.strip() == "true":
        check.status = "OK"
        check.message = "~/.context-map-update es un repo git valido."
        report.add(check)
        return

    check.status = "FAIL"
    check.message = (
        "~/.context-map-update existe pero no es un repo git valido. "
        "Esto suele romper 'ctxmap update' en Windows."
    )

    try:
        _safe_rmtree(update_dir)
        check.fix_applied = True
        check.fix_message = "Se elimino ~/.context-map-update para reparar."
    except Exception as exc:  # pragma: no cover - defensive
        check.fix_message = f"No se pudo eliminar el directorio: {exc}"

    report.add(check)


def check_git_available(report: DoctorReport) -> None:
    """Verifica que git este disponible en PATH."""
    git_ok = _run(["git", "--version"])
    check = DoctorCheck(name="git_cli")

    if git_ok.returncode == 0:
        check.status = "OK"
        check.message = git_ok.stdout.strip()
    else:
        check.status = "FAIL"
        check.message = (
            "Git no esta disponible en PATH. "
            "Sin git, 'update' e 'import-git' no funcionan."
        )

    report.add(check)


def check_vault_default(report: DoctorReport) -> None:
    """Revisa si existe el vault por defecto o con nombre de proyecto."""
    cwd = os.getcwd()
    context_dir = os.path.join(cwd, ".context-map")
    check = DoctorCheck(name="vault_default")

    # Buscar cualquier vault (vault, vault-Nombre, vault-*)
    vaults = []
    if os.path.isdir(context_dir):
        vaults = [
            d for d in os.listdir(context_dir)
            if os.path.isdir(os.path.join(context_dir, d))
            and d.startswith("vault")
        ]

    if vaults:
        check.status = "OK"
        vaults_str = ", ".join(vaults)
        check.message = (
            f"Vault(s) encontrado(s): {vaults_str} "
            f"en {context_dir}"
        )
    else:
        check.status = "WARN"
        check.message = (
            f"No se encontro vault en {context_dir}/vault*. "
            "Ejecuta 'ctxmap build --project ...' para generarlo."
        )

    report.add(check)


# Orden define prioridad de ejecucion y visualizacion
CHECKS = [
    check_git_available,
    check_update_dir,
    check_vault_default,
]


def run(cwd: str = "") -> DoctorReport:
    """Ejecuta todos los chequeos y devuelve el reporte consolidado."""
    if cwd:
        os.chdir(cwd)

    report = DoctorReport()
    for fn in CHECKS:
        fn(report)
    return report

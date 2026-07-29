from __future__ import annotations

"""Diagnóstico y salud del entorno de ContextMap.

Proporciona chequeos determinísticos sobre dependencias de sistema (Git),
directorios temporales de actualización y estado de vaults generados.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List


@dataclass
class DoctorCheck:
    """Resultado individual de una verificación de salud.

    Attributes:
        name (str): Nombre del chequeo.
        status (str): Estado del chequeo ('OK', 'WARN', 'FAIL').
        message (str): Mensaje explicativo del estado.
        fix_applied (bool): True si se aplicó una reparación automática.
        fix_message (str): Detalles de la solución aplicada.
    """

    name: str
    status: str = "OK"
    message: str = ""
    fix_applied: bool = False
    fix_message: str = ""


@dataclass
class DoctorReport:
    """Reporte consolidado de salud del sistema.

    Attributes:
        checks (List[DoctorCheck]): Lista de chequeos ejecutados.
    """

    checks: List[DoctorCheck] = field(default_factory=list)

    def add(self, check: DoctorCheck) -> None:
        """Agrega un resultado de chequeo al reporte.

        Args:
            check (DoctorCheck): Chequeo a agregar.
        """
        self.checks.append(check)

    @property
    def failed(self) -> List[DoctorCheck]:
        """Obtiene los chequeos con estado FAIL.

        Returns:
            List[DoctorCheck]: Lista de fallos.
        """
        return [c for c in self.checks if c.status == "FAIL"]

    @property
    def warnings(self) -> List[DoctorCheck]:
        """Obtiene los chequeos con estado WARN.

        Returns:
            List[DoctorCheck]: Lista de advertencias.
        """
        return [c for c in self.checks if c.status == "WARN"]

    @property
    def ok(self) -> bool:
        """Indica si el sistema está completamente libre de fallos.

        Returns:
            bool: True si no existen fallos, False de lo contrario.
        """
        return len(self.failed) == 0


def _safe_rmtree(path: str) -> None:
    """Elimina directorios con tolerancia a bloqueos de sistema en Windows.

    Args:
        path (str): Ruta del directorio a borrar.
    """
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
        if os.path.isdir(path):
            for _ in range(3):
                shutil.rmtree(path, ignore_errors=True)
                if not os.path.isdir(path):
                    break
                try:
                    subprocess.run(
                        ["cmd", "/c", "rd", "/s", "/q", path],
                        capture_output=True,
                        timeout=10,
                    )
                except Exception:
                    pass
                if not os.path.isdir(path):
                    break


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando de sistema en subprocess capturando stdout y stderr.

    Args:
        cmd (list[str]): Comando y sus argumentos.

    Returns:
        subprocess.CompletedProcess[str]: Resultado de la ejecución.
    """
    return subprocess.run(cmd, capture_output=True, text=True)


def check_update_dir(report: DoctorReport) -> None:
    """Verifica el directorio temporal de actualización `~/.context-map-update`.

    Args:
        report (DoctorReport): Reporte donde se adjuntará el resultado.
    """
    update_dir = os.path.join(os.path.expanduser("~"), ".context-map-update")
    check = DoctorCheck(name="update_dir")

    if not os.path.exists(update_dir):
        check.status = "OK"
        check.message = "~/.context-map-update no existe, sin anomalías."
        report.add(check)
        return

    is_git = _run(["git", "-C", update_dir, "rev-parse", "--is-inside-work-tree"])
    if is_git.returncode == 0 and is_git.stdout.strip() == "true":
        check.status = "OK"
        check.message = "~/.context-map-update es un repo git válido."
        report.add(check)
        return

    check.status = "FAIL"
    check.message = (
        "~/.context-map-update existe pero no es un repo git válido."
    )

    try:
        _safe_rmtree(update_dir)
        check.fix_applied = True
        check.fix_message = "Se eliminó ~/.context-map-update para reparar."
    except Exception as exc:
        check.fix_message = f"No se pudo eliminar el directorio: {exc}"

    report.add(check)


def check_git_available(report: DoctorReport) -> None:
    """Verifica que el ejecutable `git` esté disponible en el PATH.

    Args:
        report (DoctorReport): Reporte de salida.
    """
    git_ok = _run(["git", "--version"])
    check = DoctorCheck(name="git_cli")

    if git_ok.returncode == 0:
        check.status = "OK"
        check.message = git_ok.stdout.strip()
    else:
        check.status = "FAIL"
        check.message = "Git no está disponible en el PATH."

    report.add(check)


def check_vault_default(report: DoctorReport) -> None:
    """Verifica la existencia del vault predeterminado en `.context-map/`.

    Args:
        report (DoctorReport): Reporte de salida.
    """
    cwd = os.getcwd()
    context_dir = os.path.join(cwd, ".context-map")
    check = DoctorCheck(name="vault_default")

    vaults = []
    if os.path.isdir(context_dir):
        vaults = [
            d for d in os.listdir(context_dir)
            if os.path.isdir(os.path.join(context_dir, d)) and d.startswith("vault")
        ]

    if vaults:
        check.status = "OK"
        vaults_str = ", ".join(vaults)
        check.message = f"Vault(s) encontrado(s): {vaults_str} en {context_dir}"
    else:
        check.status = "WARN"
        check.message = f"No se encontró vault en {context_dir}/vault*."

    report.add(check)


CHECKS = [
    check_git_available,
    check_update_dir,
    check_vault_default,
]


def run(cwd: str = "") -> DoctorReport:
    """Ejecuta todos los chequeos de diagnóstico y retorna el reporte consolidado.

    Args:
        cwd (str): Directorio de trabajo opcional para la ejecución.

    Returns:
        DoctorReport: Reporte consolidado de salud.
    """
    if cwd:
        os.chdir(cwd)

    report = DoctorReport()
    for fn in CHECKS:
        fn(report)
    return report

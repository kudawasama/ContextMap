"""Diagnóstico, salud y auto-reparación (Self-Healing) del entorno de ContextMap.

Proporciona chequeos determinísticos sobre dependencias de sistema (Git),
consistencia de vaults, preservación de notas manuales y auto-reparación.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field

from context_map.presentation.briefs.extractors import vault_nombre
from context_map.presentation.vault.preservar import ZONAS_MANUALES

logger = logging.getLogger(__name__)


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

    checks: list[DoctorCheck] = field(default_factory=list)

    def add(self, check: DoctorCheck) -> None:
        """Agrega un resultado de chequeo al reporte.

        Args:
            check (DoctorCheck): Chequeo a agregar.
        """
        self.checks.append(check)

    @property
    def failed(self) -> list[DoctorCheck]:
        """Obtiene los chequeos con estado FAIL."""
        return [c for c in self.checks if c.status == "FAIL"]

    @property
    def warnings(self) -> list[DoctorCheck]:
        """Obtiene los chequeos con estado WARN."""
        return [c for c in self.checks if c.status == "WARN"]

    @property
    def ok(self) -> bool:
        """Indica si el sistema está completamente libre de fallos."""
        return len(self.failed) == 0


def _safe_rmtree(path: str) -> None:
    """Elimina directorios con tolerancia a bloqueos de sistema en Windows."""
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
                except Exception as err:
                    logger.debug("No se pudo forzar borrado de %s: %s", path, err)
                if not os.path.isdir(path):
                    break


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando de sistema en subprocess capturando stdout y stderr."""
    return subprocess.run(cmd, capture_output=True, text=True)


def check_update_dir(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica el directorio temporal de actualización `~/.context-map-update`."""
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
    check.message = "~/.context-map-update existe pero no es un repo git válido."

    if fix:
        try:
            _safe_rmtree(update_dir)
            check.fix_applied = True
            check.fix_message = "Se eliminó ~/.context-map-update corrupto para reparar."
            check.status = "OK"
        except Exception as exc:
            logger.warning("No se pudo eliminar ~/.context-map-update: %s", exc)
            check.fix_message = f"No se pudo eliminar el directorio: {exc}"

    report.add(check)


def check_git_available(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica que el ejecutable `git` esté disponible en el PATH."""
    git_ok = _run(["git", "--version"])
    check = DoctorCheck(name="git_cli")

    if git_ok.returncode == 0:
        check.status = "OK"
        check.message = git_ok.stdout.strip()
    else:
        check.status = "FAIL"
        check.message = "Git no está disponible en el PATH."

    report.add(check)


def check_vault_default(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica la existencia y salud de vaults en `.context-map/`."""
    context_dir = os.path.join(project_dir, ".context-map")
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


def check_project_name_consistency(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica la consistencia entre el nombre del repo, vault y CONTEXT.md."""
    check = DoctorCheck(name="name_consistency")
    context_dir = os.path.join(project_dir, ".context-map")

    if not os.path.isdir(context_dir):
        check.status = "OK"
        check.message = "Sin directorio .context-map/ aún."
        report.add(check)
        return

    repo_name = os.path.basename(os.path.abspath(project_dir))
    expected_vault = vault_nombre(repo_name)
    vpath = os.path.join(context_dir, expected_vault)

    vaults = [
        d for d in os.listdir(context_dir)
        if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
    ]

    inconsistente = False
    if len(vaults) > 1 or (len(vaults) == 1 and vaults[0] != expected_vault):
        inconsistente = True

    if not inconsistente:
        check.status = "OK"
        check.message = f"Nombre del proyecto único y consistente: '{repo_name}' ({expected_vault})."
        report.add(check)
        return

    check.status = "WARN"
    check.message = f"Vaults inconsistentes o duplicados ({', '.join(vaults)} vs esperado '{expected_vault}')."

    if fix:
        legacy_dir = os.path.join(context_dir, "_legacy")
        os.makedirs(legacy_dir, exist_ok=True)
        reparaciones = []
        for v in vaults:
            if v != expected_vault:
                src = os.path.join(context_dir, v)
                dst = os.path.join(legacy_dir, v)
                try:
                    if os.path.exists(dst):
                        _safe_rmtree(dst)
                    shutil.move(src, dst)
                    reparaciones.append(f"Movido vault desalineado '{v}' a '_legacy/{v}'")
                except Exception as e:
                    reparaciones.append(f"No se pudo mover '{v}': {e}")
        if reparaciones:
            check.fix_applied = True
            check.fix_message = "; ".join(reparaciones)
            check.status = "OK"

    report.add(check)


def check_manual_notes_preservation(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica que las notas en zonas manuales tengan 'preserve: true' en su frontmatter."""
    check = DoctorCheck(name="manual_notes_preservation")
    context_dir = os.path.join(project_dir, ".context-map")

    if not os.path.isdir(context_dir):
        check.status = "OK"
        check.message = "Sin directorio .context-map/ aún."
        report.add(check)
        return

    notas_sin_preserve = []
    for raiz, _, archivos in os.walk(context_dir):
        es_manual = any(z in raiz.replace("\\", "/") for z in ZONAS_MANUALES)
        if not es_manual:
            continue
        for fname in archivos:
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(raiz, fname)
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                if "preserve: true" not in content and "preserve:true" not in content:
                    notas_sin_preserve.append(fpath)
            except Exception:
                continue

    if not notas_sin_preserve:
        check.status = "OK"
        check.message = "Todas las notas manuales tienen 'preserve: true' activo."
        report.add(check)
        return

    check.status = "WARN"
    check.message = f"{len(notas_sin_preserve)} nota(s) manual(es) sin 'preserve: true'."

    if fix:
        reparadas = 0
        for fpath in notas_sin_preserve:
            try:
                with open(fpath, encoding="utf-8") as f:
                    content = f.read()
                if content.startswith("---"):
                    new_content = content.replace("---", "---\npreserve: true", 1)
                else:
                    new_content = f"---\npreserve: true\n---\n\n{content}"
                with open(fpath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                reparadas += 1
            except Exception:
                continue
        check.fix_applied = True
        check.fix_message = f"Inyectado 'preserve: true' en {reparadas} nota(s) manual(es)."
        check.status = "OK"

    report.add(check)


CHECKS = [
    check_git_available,
    check_update_dir,
    check_vault_default,
    check_project_name_consistency,
    check_manual_notes_preservation,
]


def run(cwd: str = "", fix: bool = False) -> DoctorReport:
    """Ejecuta los chequeos de diagnóstico y retorna el reporte consolidado.

    Args:
        cwd (str): Directorio de trabajo opcional para la ejecución.
        fix (bool): Si es True, aplica auto-reparaciones automáticas.

    Returns:
        DoctorReport: Reporte consolidado de salud.
    """
    project_dir = cwd or "."
    report = DoctorReport()
    for fn in CHECKS:
        fn(report, fix=fix, project_dir=project_dir)
    return report


def diagnosticar_salud(project_dir: str = ".") -> DoctorReport:
    """Diagnostica la salud del proyecto sin modificar archivos."""
    return run(cwd=project_dir, fix=False)


def reparar_salud(project_dir: str = ".") -> DoctorReport:
    """Diagnostica y auto-repara (Self-Healing) las anomalías encontradas."""
    return run(cwd=project_dir, fix=True)

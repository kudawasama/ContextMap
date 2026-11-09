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

from context_map.core.storage.store import (
    SNAPSHOT_KEEP_DEFAULT,
    _listar_snapshots,
    purgar_snapshots,
)
from context_map.core.storage.vault_index import abrir_indice, indexar_vault
from context_map.domain.ecosystem.adaptador import revisar_reglas_agente
from context_map.infrastructure.version_check import hay_actualizacion, version_local
from context_map.presentation.briefs.extractors import vault_nombre
from context_map.presentation.vault.preservar import ZONAS_MANUALES
from context_map.presentation.vault.topologia import analizar_topologia

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


def check_history(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica el tamaño del historial de snapshots y ofrece poda.

    Regresión del incidente 2026-10-13: el historial acumuló 148 GB sin que nada
    avisara hasta que el disco quedó al 100 % y fallaron servicios del sistema.

    Args:
        report (DoctorReport): Reporte donde registrar el chequeo.
        fix (bool): Si es True aplica la poda/archivado con los valores por defecto.
        project_dir (str): Directorio del proyecto a diagnosticar.
    """
    hist = os.path.join(project_dir, ".context-map", "maps", "HISTORY")
    rutas = _listar_snapshots(hist)

    if not rutas:
        report.add(DoctorCheck("history", "OK", "Sin snapshots en maps/HISTORY"))
        return

    bytes_totales = 0
    for ruta in rutas:
        try:
            bytes_totales += os.path.getsize(ruta)
        except OSError:
            continue
    total_mb = round(bytes_totales / (1024 * 1024), 2)

    umbral = SNAPSHOT_KEEP_DEFAULT * 5
    if len(rutas) > umbral:
        mensaje = (
            f"{len(rutas)} snapshots / {total_mb} MB — por encima del umbral "
            f"({umbral}). Ejecuta `ctxmap history prune`."
        )
        if fix:
            res = purgar_snapshots(hist)
            report.add(
                DoctorCheck(
                    "history",
                    "OK",
                    mensaje,
                    fix_applied=True,
                    fix_message=(
                        f"{res['archivados']} archivados · {res['eliminados']} eliminados · "
                        f"{res['conservados']} conservados"
                    ),
                )
            )
            return
        report.add(DoctorCheck("history", "WARN", mensaje))
        return

    report.add(DoctorCheck("history", "OK", f"{len(rutas)} snapshots / {total_mb} MB"))


# --- Nuevos chequeos (plan doctor & autocorrección) -------------------------


def check_update_available(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="update_available")
    try:
        local = version_local()
        hay, _l, remota = hay_actualizacion()
    except Exception as exc:  # noqa: BLE001
        check.status = "OK"
        check.message = f"No se pudo verificar actualizaciones: {exc}"
        report.add(check)
        return
    if hay:
        check.status = "WARN"
        check.message = f"Actualización disponible: v{remota} (tienes {local})."
    else:
        check.status = "OK"
        check.message = f"ContextMap al día (v{local})."
    report.add(check)


def check_mcp_deps(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="mcp_deps")
    try:
        import importlib.metadata as md

        mcp_v = md.version("mcp")
        pydantic_v = md.version("pydantic")
    except Exception:
        check.status = "OK"
        check.message = "Extra [mcp] no instalado; no aplica."
        report.add(check)
        return
    try:
        mayor, menor = (int(x) for x in pydantic_v.split(".")[:2])
    except ValueError:
        mayor, menor = 0, 0
    if (mayor, menor) < (2, 13):
        check.status = "FAIL"
        check.message = (
            f"pydantic {pydantic_v} < 2.13: el servidor MCP no importa. "
            "Instala `ctxmap-ai[mcp]`."
        )
    else:
        check.status = "OK"
        check.message = f"mcp {mcp_v}, pydantic {pydantic_v} (OK)."
    report.add(check)


def check_vault_index(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="vault_index")
    context_dir = os.path.join(project_dir, ".context-map")
    if not os.path.isdir(context_dir):
        check.status = "OK"
        check.message = "Sin directorio .context-map/ aún."
        report.add(check)
        return

    repo_name = os.path.basename(os.path.abspath(project_dir))
    expected_vault = vault_nombre(repo_name)
    vault_path = os.path.join(context_dir, expected_vault)
    if not os.path.isdir(vault_path):
        vaults = [
            d for d in os.listdir(context_dir)
            if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
        ]
        if not vaults:
            check.status = "OK"
            check.message = "Sin vault aún."
            report.add(check)
            return
        vault_path = os.path.join(context_dir, vaults[0])

    db_path = os.path.join(context_dir, "state", "vault_index.db")
    if not os.path.isfile(db_path):
        check.status = "WARN"
        check.message = "Índice FTS5 ausente. Ejecuta `ctxmap build`."
        if fix:
            try:
                conn = abrir_indice(db_path)
                try:
                    n = indexar_vault(conn, vault_path)
                finally:
                    conn.close()
                check.fix_applied = True
                check.fix_message = f"Reindexadas {n} notas."
                check.status = "OK"
            except Exception as exc:  # noqa: BLE001
                check.fix_message = f"No se pudo reindexar: {exc}"
        report.add(check)
        return

    try:
        newest_md = 0.0
        for root, _d, files in os.walk(vault_path):
            for fn in files:
                if fn.lower().endswith(".md"):
                    newest_md = max(newest_md, os.path.getmtime(os.path.join(root, fn)))
        db_mtime = os.path.getmtime(db_path)
    except OSError as exc:
        check.status = "WARN"
        check.message = f"No se pudo verificar frescura del índice: {exc}"
        report.add(check)
        return

    if newest_md > db_mtime:
        check.status = "WARN"
        check.message = "Índice FTS5 desactualizado (vault más nuevo)."
        if fix:
            try:
                conn = abrir_indice(db_path)
                try:
                    n = indexar_vault(conn, vault_path)
                finally:
                    conn.close()
                check.fix_applied = True
                check.fix_message = f"Reindexadas {n} notas."
                check.status = "OK"
            except Exception as exc:  # noqa: BLE001
                check.fix_message = f"No se pudo reindexar: {exc}"
    else:
        check.status = "OK"
        check.message = "Índice FTS5 presente y al día."
    report.add(check)


def check_context_freshness(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="context_freshness")
    try:
        from context_map.domain.analysis import analizar_readiness

        resultado = analizar_readiness(project_dir)
        frescura = getattr(resultado, "frescura", {}) or {}
        aviso = frescura.get("aviso") if isinstance(frescura, dict) else None
    except Exception as exc:  # noqa: BLE001
        check.status = "OK"
        check.message = f"No se pudo evaluar frescura: {exc}"
        report.add(check)
        return
    if aviso:
        check.status = "WARN"
        check.message = str(aviso)
    else:
        check.status = "OK"
        check.message = "Contexto al día (sin actividad posterior al último build)."
    report.add(check)


def check_skill_collisions(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="skill_collisions")
    import glob as _glob

    home = os.path.expanduser("~")
    raices: list[str] = []
    for r in (
        os.path.join(home, ".agents", "skills"),
        os.path.join(project_dir, ".agents", "skills"),
        os.path.join(home, ".claude", "skills"),
        os.path.join(home, ".pi", "agent", "npm", "node_modules"),
        os.path.join(project_dir, "node_modules"),
    ):
        if os.path.isdir(r):
            raices.append(r)

    skills: dict[str, list[str]] = {}

    def _parse_name(path: str) -> str | None:
        try:
            with open(path, encoding="utf-8") as f:
                texto = f.read(2048)
        except OSError:
            return None
        if not texto.startswith("---"):
            return None
        for line in texto.splitlines()[1:]:
            if line.strip() == "---":
                break
            if ":" in line:
                k, v = line.split(":", 1)
                if k.strip().lower() == "name":
                    return v.strip().strip('"').strip("'")
        return None

    def _escanear(raiz: str, profundidad: int = 0) -> None:
        if profundidad > 4:
            return
        try:
            with os.scandir(raiz) as it:
                for entry in it:
                    if entry.is_symlink():
                        continue
                    if entry.is_dir(follow_symlinks=False):
                        _escanear(entry.path, profundidad + 1)
                    elif entry.name == "SKILL.md":
                        name = _parse_name(entry.path)
                        if name:
                            skills.setdefault(name, []).append(entry.path)
        except (OSError, PermissionError):
            return

    for r in raices:
        _escanear(r)

    # Raíces de paquetes npm acotadas: solo */*/skills
    for patron in (
        os.path.join(home, ".pi", "agent", "npm", "node_modules", "*", "*", "skills"),
        os.path.join(project_dir, "node_modules", "@*", "*", "skills"),
    ):
        for skills_dir in _glob.glob(patron):
            if os.path.isdir(skills_dir):
                _escanear(skills_dir, 0)

    colisiones = {n: ps for n, ps in skills.items() if len(ps) > 1}
    if colisiones:
        detalle = "; ".join(f"{n}: {', '.join(ps)}" for n, ps in colisiones.items())
        check.status = "WARN"
        check.message = (
            f"Skill duplicada detectada (el agente usa la primera descubierta): "
            f"{detalle}"
        )
    else:
        check.status = "OK"
        check.message = "Sin colisiones de skills entre orígenes."
    report.add(check)


def check_generated_rules(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="generated_rules")
    try:
        resultado = revisar_reglas_agente(
            os.path.basename(os.path.abspath(project_dir)),
            target_dir=project_dir,
            dry_run=True,
        )
    except TypeError:
        # dry_run no soportado aún: degradar a solo diagnóstico del manifiesto
        resultado = None
    except Exception as exc:  # noqa: BLE001
        check.status = "OK"
        check.message = f"No se pudo revisar reglas generadas: {exc}"
        report.add(check)
        return

    if resultado is None:
        check.status = "OK"
        check.message = "Manifiesto de reglas no disponible."
        report.add(check)
        return

    actualizados = resultado.get("actualizados", [])
    respetados = resultado.get("respetados", [])
    if actualizados or respetados:
        check.status = "WARN"
        partes = []
        if actualizados:
            partes.append(f"{len(actualizados)} desactualizada(s): {', '.join(actualizados)}")
        if respetados:
            partes.append(f"{len(respetados)} editada(s) manualmente: {', '.join(respetados)}")
        check.message = "; ".join(partes) + ". Ejecuta `ctxmap adapt`."
        if fix and actualizados:
            try:
                revisar_reglas_agente(
                    os.path.basename(os.path.abspath(project_dir)),
                    target_dir=project_dir,
                )
                check.fix_applied = True
                check.fix_message = "Reglas gestionadas actualizadas."
                check.status = "OK"
            except Exception as exc:  # noqa: BLE001
                check.fix_message = f"No se pudo actualizar: {exc}"
    else:
        check.status = "OK"
        check.message = "Reglas agénticas gestionadas al día."
    report.add(check)


def check_topologia(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    check = DoctorCheck(name="topologia")
    context_dir = os.path.join(project_dir, ".context-map")
    vaults = []
    if os.path.isdir(context_dir):
        vaults = [
            d for d in os.listdir(context_dir)
            if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
        ]
    if not vaults:
        check.status = "OK"
        check.message = "Sin vault aún."
        report.add(check)
        return
    vault_path = os.path.join(context_dir, sorted(vaults)[0])
    resultado = analizar_topologia(vault_path)
    if resultado.ok:
        check.status = "OK"
        check.message = f"Topología OK ({resultado.archivos} notas)."
    else:
        check.status = "WARN"
        check.message = f"{len(resultado.errores)} violación(es): {resultado.errores[0]}"
    report.add(check)


CHECKS = [
    check_git_available,
    check_update_dir,
    check_vault_default,
    check_project_name_consistency,
    check_manual_notes_preservation,
    check_history,
    check_update_available,
    check_mcp_deps,
    check_vault_index,
    check_context_freshness,
    check_skill_collisions,
    check_generated_rules,
    check_topologia,
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

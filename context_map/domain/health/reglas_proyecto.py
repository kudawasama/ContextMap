"""Chequeos de las reglas de conducta que se pueden medir.

El catálogo (`references/reglas/reglas_registro.yaml`) declara 71 reglas; no
todas son medibles —«responder en español técnico» no lo comprueba un test—,
pero otras muchas sí y quedaban marcadas como ``manual`` por comodidad. Este
módulo convierte en puerta dura las cuatro que se pueden medir **sin ruido
permanente**:

* ``commits_convencionales`` (``REG-DOC-003``): asunto del commit con
  Conventional Commits. Los *merge commits* de git y de GitHub se descartan:
  no los escribe una persona.
* ``changelog_commit`` (``REG-DOC-004``): el commit de la punta que toca código
  debe tocar también ``CHANGELOG.md``. Se mira **solo la punta** a propósito:
  la deuda de commits viejos no es accionable hoy y una regla que nunca puede
  ponerse en verde deja de ser una regla.
* ``diario_del_dia`` (``REG-MEM-002``): si hoy hay trabajo (commits de hoy), el
  diario del vault debe tener la nota de hoy.
* ``secretos_versionados`` (``REG-SEG-001``): ningún secreto en archivos
  rastreados por git. Nunca se imprime el valor, solo la ruta y qué patrón.

Todos son ``WARN``: informan y, con ``--strict-warn``, cortan el cierre de
sesión. Ninguno modifica archivos (``fix`` se ignora): son contenido ajeno.
"""

from __future__ import annotations

import os
import re
import subprocess
from datetime import date
from typing import Optional

from context_map.domain.health.doctor import DoctorCheck, DoctorReport

#: Asunto de commit con Conventional Commits (en español, pero el tipo es fijo).
PATRON_COMMIT = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|perf|build|ci|style|revert)"
    r"(\([a-z0-9_.-]+\))?!?: \S"
)

#: Cuántos commits recientes se revisan en la convención de asuntos.
VENTANA_COMMITS = 50

#: Extensiones que nunca contienen un secreto útil de escanear.
BINARIOS = (
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".gz", ".whl",
    ".pyc", ".db", ".sqlite", ".woff", ".woff2", ".ttf", ".mp3", ".mp4",
)

#: Tamaño máximo por archivo (un secreto no vive en un log de 50 MB).
MAX_BYTES = 400_000

#: Patrones de secreto. Se informa del **nombre**, nunca del valor.
PATRONES_SECRETO = {
    "clave de AWS": re.compile(r"AKIA[0-9A-Z]{16}"),
    "token de GitHub": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "clave privada": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "token de Slack": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "clave API asignada": re.compile(
        r"(?i)\b(api[_-]?key|secret[_-]?key|password|passwd|access[_-]?token)\b"
        r"\s*[:=]\s*['\"][^'\"]{16,}['\"]"
    ),
}

#: Marcadores de valor de mentira (tests, ejemplos, documentación).
MARCADORES_FALSO = (
    "example", "ejemplo", "fake", "dummy", "placeholder", "redacted",
    "xxxxxxxx", "changeme", "tu-token", "your-token", "akiosfodnn7",
)


def _git(project_dir: str, *args: str) -> Optional[str]:
    """Ejecuta git en el proyecto y devuelve la salida (``None`` si falla).

    Args:
        project_dir (str): Raíz del proyecto.
        *args (str): Argumentos de git.

    Returns:
        Optional[str]: Salida estándar, o ``None`` si git no está o el
        proyecto no es un repositorio.
    """
    try:
        resultado = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if resultado.returncode != 0:
        return None
    return resultado.stdout


def _es_convencional(asunto: str) -> bool:
    """¿El asunto del commit sigue Conventional Commits?"""
    return bool(PATRON_COMMIT.match(asunto.strip()))


def _es_merge(asunto: str) -> bool:
    """¿Es un merge que git o GitHub escriben solos?"""
    limpio = asunto.strip().lower()
    return limpio.startswith(("merge ", "merge pull request", "revert \"merge"))


def check_commits_convencionales(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Revisa la convención de los asuntos de los últimos commits.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (el historial no se reescribe).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="commits_convencionales")
    salida = _git(project_dir, "log", "--no-merges", f"-{VENTANA_COMMITS}", "--format=%s")
    if salida is None:
        check.status = "OK"
        check.message = "Sin historial de git que revisar."
        report.add(check)
        return

    asuntos = [linea for linea in salida.splitlines() if linea.strip()]
    malos = [a for a in asuntos if not _es_merge(a) and not _es_convencional(a)]
    if malos:
        check.status = "WARN"
        ejemplo = "; ".join(f"«{a[:48]}»" for a in malos[:3])
        check.message = (
            f"{len(malos)} de {len(asuntos)} commit(s) sin Conventional Commits: {ejemplo}"
        )
    else:
        check.status = "OK"
        check.message = f"{len(asuntos)} commit(s) con Conventional Commits."
    report.add(check)


def _archivos_del_commit(project_dir: str, revision: str) -> Optional[list[str]]:
    """Lista los archivos que toca un commit (``None`` si no se puede leer)."""
    salida = _git(project_dir, "show", "--name-only", "--format=", revision)
    if salida is None:
        return None
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def _toca_codigo(archivos: list[str]) -> bool:
    """¿El commit toca código de la aplicación (no solo docs o tests)?"""
    for ruta in archivos:
        if "/__tests__/" in ruta or ruta.startswith("tests/"):
            continue
        if ruta.endswith(".py") and "/" in ruta:
            return True
    return False


def check_changelog_commit(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """El commit de la punta que cambia código debe registrar el cambio.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (no se reescriben commits).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="changelog_commit")
    asunto = _git(project_dir, "log", "-1", "--format=%s")
    if asunto is None:
        check.status = "OK"
        check.message = "Sin historial de git que revisar."
        report.add(check)
        return

    archivos = _archivos_del_commit(project_dir, "HEAD")
    if archivos is None:
        check.status = "OK"
        check.message = "No se pudo leer el commit de la punta."
        report.add(check)
        return

    if _toca_codigo(archivos) and "CHANGELOG.md" not in archivos:
        check.status = "WARN"
        check.message = (
            f"El último commit cambia código sin tocar CHANGELOG.md: «{asunto.strip()[:60]}». "
            "Registra el cambio antes de seguir (REG-DOC-004)."
        )
    else:
        check.status = "OK"
        check.message = "El último commit deja el CHANGELOG al día."
    report.add(check)


def _vault_activo(project_dir: str) -> Optional[str]:
    """Ruta del vault del proyecto, o ``None`` si no hay vault."""
    context_dir = os.path.join(project_dir, ".context-map")
    if not os.path.isdir(context_dir):
        return None
    vaults = sorted(
        d for d in os.listdir(context_dir)
        if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
    )
    return os.path.join(context_dir, vaults[0]) if vaults else None


def check_diario_del_dia(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Si hoy se ha trabajado, el diario debe tener la nota de hoy.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (el diario lo escribe una persona).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="diario_del_dia")
    vault = _vault_activo(project_dir)
    if vault is None:
        check.status = "OK"
        check.message = "Sin vault: no hay diario que exigir."
        report.add(check)
        return

    hoy = date.today().isoformat()
    salida = _git(project_dir, "log", "--no-merges", "--since", f"{hoy} 00:00", "--format=%h")
    commits_hoy = len([c for c in (salida or "").splitlines() if c.strip()])
    if commits_hoy == 0:
        check.status = "OK"
        check.message = "Sin actividad hoy: no hay nada que registrar."
        report.add(check)
        return

    diario = os.path.join(vault, "7.0-MANUAL", "Diario", f"{hoy}.md")
    if os.path.isfile(diario):
        check.status = "OK"
        check.message = f"Diario del día presente ({commits_hoy} commit(s) de hoy)."
    else:
        check.status = "WARN"
        check.message = (
            f"{commits_hoy} commit(s) hoy y el diario no tiene la nota {hoy}.md "
            "(REG-MEM-002)."
        )
    report.add(check)


def _es_falso_positivo(ruta: str, linea: str) -> bool:
    """¿La coincidencia es un valor de mentira (test, ejemplo, doc)?"""
    ruta_normal = ruta.replace("\\", "/").lower()
    if "/__tests__/" in ruta_normal or "/tests/" in ruta_normal:
        return True
    if os.path.basename(ruta_normal).startswith(("test_", "conftest")):
        return True
    minuscula = linea.lower()
    return any(marcador in minuscula for marcador in MARCADORES_FALSO)


def check_secretos_versionados(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Busca secretos en los archivos rastreados por git.

    Nunca imprime el valor encontrado: solo la ruta y el tipo de patrón. Un
    reporte de salud que copia el secreto al log lo propaga.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (rotar el secreto es una decisión humana).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="secretos_versionados")
    rastreados = _git(project_dir, "ls-files")
    if rastreados is None:
        check.status = "OK"
        check.message = "Sin repositorio git: no hay archivos rastreados."
        report.add(check)
        return

    archivos = [a for a in rastreados.splitlines() if a.strip()]
    hallazgos: list[str] = []
    for ruta in archivos:
        if ruta.lower().endswith(BINARIOS):
            continue
        absoluta = os.path.join(project_dir, ruta)
        try:
            if os.path.getsize(absoluta) > MAX_BYTES:
                continue
            with open(absoluta, encoding="utf-8", errors="ignore") as fh:
                for numero, linea in enumerate(fh, 1):
                    for nombre, patron in PATRONES_SECRETO.items():
                        if not patron.search(linea):
                            continue
                        if _es_falso_positivo(ruta, linea):
                            continue
                        hallazgos.append(f"{ruta}:{numero} ({nombre})")
        except OSError:
            continue

    if hallazgos:
        check.status = "WARN"
        ejemplo = ", ".join(hallazgos[:3])
        extra = f" y {len(hallazgos) - 3} más" if len(hallazgos) > 3 else ""
        check.message = (
            f"{len(hallazgos)} posible(s) secreto(s) versionado(s): {ejemplo}{extra}. "
            "Rótalos y sácalos del historial (REG-SEG-001)."
        )
    else:
        check.status = "OK"
        check.message = f"Sin secretos en {len(archivos)} archivo(s) rastreado(s)."
    report.add(check)


#: Chequeos de conducta que este módulo aporta al doctor.
CHECKS_CONDUCTA = (
    check_commits_convencionales,
    check_changelog_commit,
    check_diario_del_dia,
    check_secretos_versionados,
)

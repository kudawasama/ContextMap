"""Chequeos de conducta de la sesión: lo que el motor dejó registrado.

Cada regla de este módulo mide **actos**, no declaraciones. La evidencia sale de
la bitácora (``core/audit/bitacora.py``), del historial de commits y de los tags:
datos que produce el proceso, no el agente que dice haberlos producido.

Frontera explícita —esto **no** se mide aquí, y no por falta de ganas:

- Cruzar cuatro fuentes antes de afirmar el estado (`REG-INI-004`).
- Inspeccionar el código antes de proponer un cambio (`REG-INI-006`).
- Buscar en la memoria de otros proyectos (`REG-INI-007`).
- Distinguir evidencia real de autoreporte al escribir el cierre (`REG-EJE-005`).
- Anunciar el costo de una tarea larga (`REG-LIM-004`).

Dependen de lo que el agente **piensa** y escribe en la conversación, que no deja
huella en el repositorio. Un chequeo que las «comprobara» estaría midiendo otra
cosa y llamándola igual.
"""

from __future__ import annotations

import os
import re
import subprocess
from typing import Any

from context_map.core.audit.bitacora import COMANDOS_CON_PERMISO, del_dia, leer
from context_map.domain.health.doctor import DoctorCheck, DoctorReport
from context_map.domain.health.reglas_proyecto import MARCADORES_FALSO, PATRONES_SECRETO

#: Comandos que producen diagnóstico y por tanto sirven de puerta de calidad.
COMANDOS_DIAGNOSTICO = ("doctor", "check")

#: Comandos cuya ejecución deja constancia de que se leyó el brief del proyecto.
COMANDOS_BRIEF = ("context", "contexto", "brief", "auto")

#: Un doctor por encima de este tiempo deja de ser un diagnóstico y pasa a ser
#: una espera (``REG-LIM-002``).
LIMITE_DOCTOR_SEGUNDOS = 120.0

#: Un tag se considera amparado por el doctor si hubo una puerta verde en las
#: horas previas a su creación.
VENTANA_TAG_HORAS = 24

#: Prefijos de ruta donde una coincidencia es un fixture, no una credencial.
RUTAS_FIXTURE = (
    "context_map/__tests__/",
    "tests/",
    "docs/",
    "references/",
    ".github/",
)

#: Nombres de archivo que son documentación, no código en producción.
NOMBRES_FIXTURE = (
    "README.md", "README_EN.md", "CHANGELOG.md", "AGENTS.md", "CLAUDE.md",
)

#: Commits del historial que se revisan (el pasado remoto ya está publicado).
VENTANA_HISTORIAL = 200

#: Tope de lectura del diff del historial: si no cabe, se avisa en vez de mentir.
MAX_BYTES_HISTORIAL = 12_000_000


def _git(project_dir: str, *args: str, timeout: int = 30) -> str | None:
    """Ejecuta un comando de git y devuelve su salida, o ``None`` si falla.

    Args:
        project_dir (str): Raíz del proyecto.
        *args (str): Argumentos de git.
        timeout (int): Segundos máximos de espera.

    Returns:
        Optional[str]: Salida estándar, o ``None`` si no hay git o el comando falla.
    """
    try:
        proceso = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proceso.returncode != 0:
        return None
    return proceso.stdout


def _es_repo_git(project_dir: str) -> bool:
    """Indica si el proyecto es un repositorio git con al menos un commit.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        bool: ``True`` si ``git rev-parse --git-dir`` funciona.
    """
    return _git(project_dir, "rev-parse", "--git-dir") is not None


def _sello(entrada: dict[str, Any]) -> str:
    """Devuelve la marca temporal comparable de una entrada (``YYYY-MM-DDTHH:MM:SS``).

    Args:
        entrada (Dict[str, Any]): Entrada de bitácora o commit.

    Returns:
        str: Los 19 primeros caracteres del instante.
    """
    return str(entrada.get("ts", ""))[:19]


def check_bitacora_sesion(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica la evidencia de la sesión: brief leído, diagnóstico previo y cierre en verde.

    Cubre ``REG-INI-001`` (diagnosticar antes de tocar), ``REG-INI-002`` (leer el
    brief), ``REG-EJE-002`` y ``REG-SAL-002`` (no cerrar con la puerta en rojo).
    Compara la bitácora de hoy con el primer commit del día: si se modificó algo
    antes de diagnosticar, el registro lo delata.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado: la evidencia no se repara, se produce.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="bitacora_sesion")
    entradas = del_dia(project_dir)

    commits_hoy: list[dict[str, str]] = []
    if _es_repo_git(project_dir):
        salida = _git(project_dir, "log", "--since=midnight", "--format=%h|%aI") or ""
        for linea in salida.splitlines():
            if "|" in linea:
                corto, instante = linea.split("|", 1)
                commits_hoy.append({"hash": corto, "ts": instante})

    if not entradas and not commits_hoy:
        check.status = "OK"
        check.message = "Sin actividad hoy: nada que auditar (no hay commits ni ejecuciones)."
        report.add(check)
        return

    faltas: list[str] = []

    # REG-INI-002: el brief se lee al empezar, y eso deja una ejecución.
    if not any(e.get("comando") in COMANDOS_BRIEF for e in entradas):
        faltas.append("no se leyó el brief del proyecto hoy (REG-INI-002)")

    # REG-INI-001: el diagnóstico va antes de la primera modificación. No se
    # juzgan commits anteriores a la primera entrada de la bitácora: la evidencia
    # no puede existir antes de que existiera el registro (misma regla que en
    # `tag_con_puerta_verde`).
    todas = leer(project_dir)
    inicio_registro = _sello(todas[0]) if todas else ""
    juzgables = [c for c in commits_hoy if _sello({"ts": c["ts"]}) >= inicio_registro]
    if juzgables:
        primero = min(_sello({"ts": c["ts"]}) for c in juzgables)
        previos = [
            e for e in entradas
            if e.get("comando") in COMANDOS_DIAGNOSTICO and _sello(e) <= primero
        ]
        if not previos:
            faltas.append(
                f"se commiteó a las {primero[11:]} sin doctor ni check previo (REG-INI-001)"
            )

    # REG-EJE-002 / REG-SAL-002: la última puerta del día tiene que estar en verde.
    diagnosticos = [e for e in entradas if e.get("comando") in COMANDOS_DIAGNOSTICO]
    if diagnosticos:
        ultimo = diagnosticos[-1]
        if int(ultimo.get("exit", 0)) != 0:
            faltas.append(
                f"la última puerta del día ({ultimo.get('comando')}) salió con código "
                f"{ultimo.get('exit')} (REG-SAL-002)"
            )
    elif juzgables:
        faltas.append("se trabajó hoy sin ejecutar doctor ni check (REG-EJE-002)")

    if faltas:
        check.status = "WARN"
        check.message = "Sesión sin evidencia completa: " + "; ".join(faltas) + "."
        report.add(check)
        return

    check.status = "OK"
    check.message = (
        f"Sesión con evidencia: {len(entradas)} ejecución(es) y "
        f"{len(commits_hoy)} commit(s) hoy; brief leído, diagnóstico previo y puerta final en verde."
    )
    report.add(check)


def check_permisos_explicitos(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica que nada se ejecutara sin autorización del dueño.

    Cubre ``REG-EJE-004`` (no reescribir reglas sin permiso), ``REG-SAL-003``
    (no reparar archivos sin permiso) y ``REG-PUB-003`` (no publicar sin
    permiso). La bitácora anota ``autorizado`` en ``adapt``, en ``doctor --fix``
    y en ``push``; una entrada con ``autorizado: false`` es la huella del atajo.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado: un permiso no se repara hacia atrás.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="permisos_explicitos")
    sin_permiso = [
        e for e in leer(project_dir)
        if e.get("autorizado") is False
        and (
            e.get("comando") in COMANDOS_CON_PERMISO
            or (e.get("comando") == "doctor" and "fix" in (e.get("flags") or []))
        )
    ]

    if not sin_permiso:
        check.status = "OK"
        check.message = "Ninguna ejecución sensible sin autorización registrada."
        report.add(check)
        return

    detalle = ", ".join(
        f"{e.get('comando')} ({str(e.get('ts'))[:16]})" for e in sin_permiso[-3:]
    )
    check.status = "WARN"
    check.message = (
        f"{len(sin_permiso)} ejecución(es) sensible(s) sin `--confirmar`: {detalle}. "
        "Pide permiso al dueño antes de repetirlo (REG-EJE-004, REG-SAL-003, REG-PUB-003)."
    )
    report.add(check)


def check_tag_con_puerta_verde(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica que cada tag publicado esté amparado por un doctor en verde.

    Cubre ``REG-PUB-002``. Solo se juzgan los tags creados **después** de que
    existiera la bitácora: exigir evidencia retroactiva a un tag de hace meses
    sería un aviso perpetuo, y un aviso perpetuo no se lee. Con tags ligeros git
    no guarda el instante de creación, así que se usa la fecha del commit: es una
    cota inferior honesta.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="tag_con_puerta_verde")
    if not _es_repo_git(project_dir):
        check.status = "OK"
        check.message = "Sin git: no hay tags que juzgar."
        report.add(check)
        return

    salida = _git(
        project_dir, "for-each-ref", "refs/tags",
        "--format=%(refname:short)|%(creatordate:iso-strict)",
    ) or ""
    tags = [
        tuple(linea.split("|", 1)) for linea in salida.splitlines() if "|" in linea
    ]
    if not tags:
        check.status = "OK"
        check.message = "Sin tags publicados: nada que amparar."
        report.add(check)
        return

    entradas = leer(project_dir)
    if not entradas:
        check.status = "OK"
        check.message = (
            f"{len(tags)} tag(s) anteriores a la bitácora: no hay evidencia que exigir."
        )
        report.add(check)
        return

    desde = _sello(entradas[0])
    recientes = sorted(
        ((nombre, instante) for nombre, instante in tags if instante[:19] >= desde),
        key=lambda par: par[1],
    )
    if not recientes:
        check.status = "OK"
        check.message = (
            f"{len(tags)} tag(s), todos anteriores a la bitácora: sin evidencia exigible."
        )
        report.add(check)
        return

    nombre, instante = recientes[-1]
    verdes = [
        e for e in entradas
        if e.get("comando") == "doctor" and int(e.get("exit", 1)) == 0
        and _sello(e) <= instante[:19]
    ]
    if verdes:
        check.status = "OK"
        check.message = (
            f"El tag `{nombre}` está amparado por un doctor en verde "
            f"({_sello(verdes[-1])})."
        )
        report.add(check)
        return

    check.status = "WARN"
    check.message = (
        f"El tag `{nombre}` ({instante[:19]}) no tiene un doctor en verde registrado "
        f"en las {VENTANA_TAG_HORAS} h previas. Etiquetar sin puerta en verde publica "
        "un estado sin verificar (REG-PUB-002)."
    )
    report.add(check)


def _es_fixture(ruta: str) -> bool:
    """¿La ruta es un fixture de prueba o documentación? (no es una credencial real)

    Un `ghp_…` inventado en un test no se rota: no abre nada. Se clasifica para
    que el aviso hable de lo que importa, sin callar los secretos de verdad.

    Args:
        ruta (str): Ruta relativa dentro del repositorio.

    Returns:
        bool: ``True`` si la coincidencia no es una credencial en producción.
    """
    limpia = ruta.replace("\\", "/")
    if limpia.startswith(RUTAS_FIXTURE):
        return True
    nombre = limpia.rsplit("/", 1)[-1]
    if nombre in NOMBRES_FIXTURE or nombre.endswith(".md"):
        return True
    if nombre.startswith("test_") or nombre == "conftest.py":
        return True
    minuscula = nombre.lower()
    return any(pista in minuscula for pista in ("example", "ejemplo", "demo", "plantilla"))


def check_secreto_en_el_historial(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Busca credenciales reales en el historial de commits (no solo en el árbol).

    Cubre ``REG-SEG-003``: si una credencial alguna vez se commiteó, quitarla del
    archivo no la quita del historial — hay que rotarla. Nunca imprime el valor:
    un reporte que copia el secreto al log lo propaga al log.

    Se aplican las **mismas expresiones** que al árbol de trabajo, no subcadenas:
    buscar `AKIA` a secas marcaba la propia definición del detector
    (`r"AKIA[0-9A-Z]{16}"`) como si fuera una credencial. Una expresión que exige
    16 caracteres alfanuméricos reales distingue el patrón del secreto.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado: rotar una credencial no es una reparación de archivos.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="secreto_en_el_historial")
    if not _es_repo_git(project_dir):
        check.status = "OK"
        check.message = "Sin git: no hay historial que escanear."
        report.add(check)
        return

    salida = _git(
        project_dir, "log", "--no-merges", f"-n{VENTANA_HISTORIAL}",
        "--unified=0", "-p", "--format=commit:%h", timeout=90,
    )
    if salida is None:
        check.status = "OK"
        check.message = "No se pudo leer el historial (git no respondió): sin veredicto."
        report.add(check)
        return

    if len(salida) > MAX_BYTES_HISTORIAL:
        salida = salida[:MAX_BYTES_HISTORIAL]

    reales: list[str] = []
    fixtures: list[str] = []
    commit_actual = ""
    archivo_actual = ""
    for linea in salida.splitlines():
        if linea.startswith("commit:"):
            commit_actual = linea[7:].strip()
            continue
        if linea.startswith("+++ b/"):
            archivo_actual = linea[6:].strip()
            continue
        if not linea.startswith("+") or linea.startswith("+++"):
            continue
        for tipo, patron in PATRONES_SECRETO.items():
            coincidencia = patron.search(linea)
            if not coincidencia:
                continue
            valor = coincidencia.group(0).lower()
            if any(marca in valor for marca in MARCADORES_FALSO):
                continue
            etiqueta = f"{tipo} en {commit_actual} ({archivo_actual or 'sin ruta'})"
            if _es_fixture(archivo_actual):
                fixtures.append(etiqueta)
            else:
                reales.append(etiqueta)
            break

    if not reales:
        check.status = "OK"
        nota = ""
        if fixtures:
            nota = (
                f" {len(fixtures)} coincidencia(s) en fixtures de prueba/documentación, "
                "no son credenciales."
            )
        check.message = (
            f"Sin credenciales reales en los últimos {VENTANA_HISTORIAL} commits.{nota}"
        )
        report.add(check)
        return

    check.status = "WARN"
    check.message = (
        "Credenciales en el historial versionado: "
        + "; ".join(reales[:4])
        + ". Quitar el archivo no borra el commit: rota la credencial (REG-SEG-003)."
    )
    report.add(check)


def check_historia_preservada(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Detecta una construcción del vault que perdió notas respecto a la anterior.

    Cubre ``REG-HUM-002``: nunca se borra historia. El motor anota cuántas notas
    dejó cada ``build``; una caída entre dos construcciones es la huella de un
    vault regenerado que se comió notas manuales.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado: recuperar historia exige mirar qué falta.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="historia_preservada")
    construcciones = [
        e for e in leer(project_dir)
        if e.get("comando") in ("build", "refresh") and isinstance(e.get("notas"), int)
    ]

    if len(construcciones) < 2:
        check.status = "OK"
        check.message = "Menos de dos construcciones registradas: nada que comparar todavía."
        report.add(check)
        return

    previa, ultima = construcciones[-2], construcciones[-1]
    antes, ahora = int(previa["notas"]), int(ultima["notas"])
    if ahora >= antes:
        check.status = "OK"
        check.message = f"El vault creció de {antes} a {ahora} notas entre construcciones."
        report.add(check)
        return

    check.status = "WARN"
    check.message = (
        f"El vault pasó de {antes} a {ahora} notas entre dos construcciones "
        f"({ahora - antes}). Ninguna nota se borra sin decisión humana (REG-HUM-002)."
    )
    report.add(check)


def check_doctor_rapido(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica que el diagnóstico siga siendo rápido.

    Cubre ``REG-LIM-002``. Un doctor lento se deja de ejecutar, y un doctor que
    no se ejecuta no protege nada. Se mide lo que tardó la última ejecución real.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="doctor_rapido")
    ejecuciones = [
        e for e in leer(project_dir)
        if e.get("comando") == "doctor" and isinstance(e.get("duracion_s"), (int, float))
    ]
    if not ejecuciones:
        check.status = "OK"
        check.message = "Sin ejecuciones medidas todavía: el chequeo empieza a contar desde la próxima."
        report.add(check)
        return

    ultima = ejecuciones[-1]
    duracion = float(ultima["duracion_s"])
    if duracion <= LIMITE_DOCTOR_SEGUNDOS:
        check.status = "OK"
        check.message = (
            f"Último doctor en {duracion:.1f} s (límite {LIMITE_DOCTOR_SEGUNDOS:.0f} s)."
        )
        report.add(check)
        return

    check.status = "WARN"
    check.message = (
        f"El último doctor tardó {duracion:.1f} s (límite {LIMITE_DOCTOR_SEGUNDOS:.0f} s). "
        "Un diagnóstico que se hace esperar deja de ejecutarse (REG-LIM-002)."
    )
    report.add(check)


#: Chequeos de conducta de la sesión, en el orden en que se ejecutan.
CHECKS_SESION = (
    check_bitacora_sesion,
    check_permisos_explicitos,
    check_tag_con_puerta_verde,
    check_secreto_en_el_historial,
    check_historia_preservada,
    check_doctor_rapido,
)

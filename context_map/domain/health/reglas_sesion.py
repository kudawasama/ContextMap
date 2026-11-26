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

`REG-DOC-007` sí entra, y por una rendija concreta: una decisión guardada en la
memoria personal **sin** el campo ``contexto`` no explica su porqué. Se mide lo
que el registro guarda, no la conversación que lo originó.

Dependen de lo que el agente **piensa** y escribe en la conversación, que no deja
huella en el repositorio. Un chequeo que las «comprobara» estaría midiendo otra
cosa y llamándola igual.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
from datetime import datetime
from typing import Any

from context_map.core.audit.bitacora import (
    CODIGO_RECHAZO,
    COMANDOS_CON_PERMISO,
    del_dia,
    leer,
)
from context_map.core.audit.lecturas import hay_registro, primera_lectura, rutas_leidas
from context_map.domain.health.reglas_vault import _vault_activo
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

#: Expresiones equivalentes en sintaxis POSIX, para que las entienda `git -G`.
#: Git no acepta `(?i)` en línea y una expresión inválida aborta la búsqueda; el
#: filtro fino se hace igualmente en Python con ``PATRONES_SECRETO``.
HUELLAS_GIT = (
    "AKIA[0-9A-Z]{16}",
    "gh[pousr]_[A-Za-z0-9]{20,}",
    "-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "xox[baprs]-[A-Za-z0-9-]{10,}",
    "(api[_-]?key|secret[_-]?key|password|passwd|access[_-]?token)[[:space:]]*[:=][[:space:]]*"
    "['\"][^'\"]{16,}['\"]",
)

#: Ventana de reintento cuando el historial es demasiado lento (unidad de red).
VENTANA_CORTA = 50

#: Commits sospechosos a los que se les mira el diff (cada uno cuesta una lectura).
MAX_COMMITS_ESCANEO = 8


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
        fallos = ultimo.get("fallos")
        # Con `--strict-warn` la puerta sale con 1 también cuando solo hay
        # avisos: la bandera más estricta parecería un fallo. El número de FAIL
        # es el que distingue «avisó» de «falló».
        if fallos is not None:
            roja = int(fallos) > 0
        else:
            roja = int(ultimo.get("exit", 0)) != 0
        if roja:
            detalle = f"{fallos} fallo(s)" if fallos is not None else f"código {ultimo.get('exit')}"
            faltas.append(
                f"la última puerta del día ({ultimo.get('comando')}) salió con "
                f"{detalle} (REG-SAL-002)"
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
    sensibles = [
        e for e in leer(project_dir)
        if e.get("autorizado") is False
        and (
            e.get("comando") in COMANDOS_CON_PERMISO
            or (e.get("comando") == "doctor" and "fix" in (e.get("flags") or []))
        )
    ]
    # Una tarea que se detuvo sin `--confirmar` no ejecutó nada: la puerta hizo su
    # trabajo. Contarla como falta sería castigar al que obedeció.
    sin_permiso = [e for e in sensibles if e.get("exit") != CODIGO_RECHAZO]
    detenidas = len(sensibles) - len(sin_permiso)

    if not sin_permiso:
        check.status = "OK"
        check.message = "Ninguna ejecución sensible sin autorización registrada."
        if detenidas:
            check.message += (
                f" {detenidas} tarea(s) cara(s) se detuvieron sin `--confirmar` "
                "(REG-LIM-004): se anunciaron y no se ejecutaron."
            )
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


def _commits_sospechosos(project_dir: str) -> list[str] | None:
    """Commits recientes que podrían contener una credencial, en **una** llamada.

    Se usa ``git log -G`` —pickaxe con expresión regular— en vez de volcar el
    diff con ``-p``: serializar 200 diffs en una unidad de red agota el tiempo de
    espera. Y se lanza **una** búsqueda con la alternancia de todas las
    expresiones, no cinco: cada llamada recorre el historial entero, así que
    cinco expresiones costaban cinco veces lo mismo.

    Si el historial es demasiado lento, se reintenta con una ventana corta antes
    de rendirse: un chequeo que nunca responde no protege nada.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Optional[List[str]]: Hashes cortos, o ``None`` si git no respondió.
    """
    alternancia = "|".join(f"({p})" for p in HUELLAS_GIT)
    for ventana, espera in ((VENTANA_HISTORIAL, 45), (VENTANA_CORTA, 20)):
        salida = _git(
            project_dir, "log", "--no-merges", f"-n{ventana}", "--regexp-ignore-case",
            f"-G{alternancia}", "--format=%h", timeout=espera,
        )
        if salida is not None:
            return [c.strip() for c in salida.splitlines() if c.strip()][:MAX_COMMITS_ESCANEO]
    return None


def _lineas_añadidas(project_dir: str, commit: str) -> dict[str, list[str]]:
    """Líneas añadidas por un commit, agrupadas por archivo.

    Args:
        project_dir (str): Raíz del proyecto.
        commit (str): Hash del commit.

    Returns:
        Dict[str, List[str]]: Archivo → líneas añadidas.
    """
    salida = _git(
        project_dir, "show", "--no-merges", "--unified=0", "--format=", commit,
        timeout=30,
    )
    if not salida:
        return {}
    por_archivo: dict[str, list[str]] = {}
    actual = ""
    for linea in salida.splitlines():
        if linea.startswith("+++ b/"):
            actual = linea[6:].strip()
        elif linea.startswith("+") and not linea.startswith("+++") and actual:
            por_archivo.setdefault(actual, []).append(linea)
    return por_archivo


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

    reales: list[str] = []
    fixtures: list[str] = []
    sin_veredicto: list[str] = []

    commits = _commits_sospechosos(project_dir)
    if commits is None:
        sin_veredicto.append("el historial")

    for commit in commits or []:
        for archivo, lineas in _lineas_añadidas(project_dir, commit).items():
            for linea in lineas:
                for tipo, patron in PATRONES_SECRETO.items():
                    coincidencia = patron.search(linea)
                    if not coincidencia:
                        continue
                    if any(m in coincidencia.group(0).lower() for m in MARCADORES_FALSO):
                        continue
                    etiqueta = f"{tipo} en {commit} ({archivo})"
                    if _es_fixture(archivo):
                        fixtures.append(etiqueta)
                    else:
                        reales.append(etiqueta)
                    break

    if reales:
        check.status = "WARN"
        check.message = (
            "Credenciales en el historial versionado: "
            + "; ".join(reales[:4])
            + ". Quitar el archivo no borra el commit: rota la credencial (REG-SEG-003)."
        )
        report.add(check)
        return

    nota = ""
    if fixtures:
        nota += (
            f" {len(fixtures)} coincidencia(s) en fixtures de prueba/documentación, "
            "no son credenciales."
        )
    if sin_veredicto:
        nota += (
            f" Sin veredicto para {', '.join(sin_veredicto)}: git no respondió a tiempo "
            "(historial grande sobre una unidad de red). Se declara el hueco en vez de "
            "fingir que se revisó."
        )
    check.status = "OK"
    check.message = (
        f"Sin credenciales reales en los últimos {VENTANA_HISTORIAL} commits." + nota
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

def _nombres_del_proyecto(project_dir: str) -> tuple[str, ...]:
    """Variantes del nombre de la carpeta, para encontrar el proyecto en la BD.

    La memoria personal guarda nombres escritos a mano (``EE RR`` convive con
    ``EE_RR``), así que se prueban las variantes razonables en vez de exigir una
    coincidencia exacta que dejaría el chequeo mudo.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Tuple[str, ...]: Nombres candidatos, sin repetir.
    """
    base = os.path.basename(os.path.abspath(project_dir)) or "."
    variantes = {
        base,
        base.replace("_", " "),
        base.replace(" ", "_"),
        base.replace("-", " "),
        base.replace(" ", "-"),
    }
    return tuple(sorted(v for v in variantes if v))


def check_decisiones_con_porque(
    report: DoctorReport, fix: bool = False, project_dir: str = ".",
) -> None:
    """Comprueba que las decisiones registradas declaren su porqué (``REG-DOC-007``).

    Una decisión sin ``contexto`` es un titular: dice qué se hizo y no por qué.
    Dentro de un año, el titular no permite revisar la decisión, que es el único
    motivo para haberla guardado.

    El alcance es honesto y acotado: mira el registro de decisiones de la memoria
    personal (``ctxmap personal add --tipo decision --contexto "..."``), que es
    donde el motor guarda decisiones con un campo para el porqué. No juzga si la
    decisión era relevante ni si se escribió en el vault — eso es criterio, no
    dato. Si el proyecto no tiene decisiones registradas, no hay nada que auditar
    y se dice así en vez de fingir un verde.

    Una decisión guardada con un ``--proyecto`` que la BD no conoce queda sin
    dueño (``proyecto_id`` nulo) y no aparece en ninguna consulta por proyecto:
    se pierde del mapa. Eso lo delata ``ctxmap personal repair``, no esta regla.

    Args:
        report (DoctorReport): Informe donde se anota el resultado.
        fix (bool): Ignorado: el porqué no se rellena solo sin inventarlo.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="decisiones_con_porque")
    try:
        from context_map.core.personal.bd import resolver_ruta_bd

        ruta = resolver_ruta_bd()
    except Exception as err:  # pragma: no cover - import defensivo
        check.status = "OK"
        check.message = f"Sin memoria personal disponible ({err}): nada que auditar."
        report.add(check)
        return

    if not os.path.isfile(ruta):
        check.status = "OK"
        check.message = "Sin Base de Datos personal: no hay decisiones que auditar."
        report.add(check)
        return

    nombres = _nombres_del_proyecto(project_dir)
    marcas = ", ".join("?" for _ in nombres)
    try:
        conexion = sqlite3.connect(f"file:{ruta}?mode=ro", uri=True)
        try:
            total = conexion.execute(
                "SELECT COUNT(*) FROM decisiones d "
                "JOIN proyectos p ON p.id = d.proyecto_id "
                f"WHERE p.nombre IN ({marcas})",
                nombres,
            ).fetchone()[0]
            sin_porque = conexion.execute(
                "SELECT COUNT(*) FROM decisiones d "
                "JOIN proyectos p ON p.id = d.proyecto_id "
                f"WHERE p.nombre IN ({marcas}) "
                "AND TRIM(COALESCE(d.contexto, '')) = ''",
                nombres,
            ).fetchone()[0]
        finally:
            conexion.close()
    except sqlite3.Error as err:
        check.status = "OK"
        check.message = f"No se pudo leer la memoria personal ({err}): sin veredicto."
        report.add(check)
        return

    if total == 0:
        check.status = "OK"
        check.message = "Sin decisiones registradas en este proyecto: nada que auditar."
        report.add(check)
        return

    if sin_porque:
        check.status = "WARN"
        check.message = (
            f"{sin_porque} de {total} decisión(es) guardadas sin el porqué. "
            "Rehacerlas con `ctxmap personal add --tipo decision --contexto \"...\"` "
            "o completar el contexto (REG-DOC-007)."
        )
        report.add(check)
        return

    check.status = "OK"
    check.message = f"Las {total} decisión(es) registradas explican su porqué."
    report.add(check)


# ── lecturas_previas: INI-006 ─────────────────────────────────────────────

#: Extensiones de código: lo que se toca sin leer es código, no documentación.
EXTENSIONES_CODIGO = frozenset({
    ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".rb", ".php",
    ".cs", ".c", ".h", ".cpp", ".kt", ".swift", ".sql", ".sh", ".ps1", ".vue",
    ".svelte", ".mjs", ".cjs",
})

#: Estados de ``git show --name-status`` que implican que el archivo existía antes.
ESTADOS_EXISTENTES = ("M", "R", "C", "T")


def _archivos_del_commit(project_dir: str) -> list[tuple[str, str]]:
    """Archivos del último commit con su estado de cambio.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        List[Tuple[str, str]]: Pares ``(estado, ruta)``; vacío si no hay git.
    """
    salida = _git(project_dir, "show", "--name-status", "--format=", "-M", "HEAD")
    if not salida:
        return []
    pares: list[tuple[str, str]] = []
    for linea in salida.splitlines():
        partes = linea.strip().split("	")
        if len(partes) < 2:
            continue
        estado = partes[0][:1]
        ruta = partes[-1]
        pares.append((estado, ruta))
    return pares


def check_lecturas_previas(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Verifica que el último commit no tocara código que nunca se leyó (INI-006).

    La regla es conducta —nadie puede demostrar que el agente leyó por dentro—
    pero **sí queda huella** de qué archivos abrió cuando el harness tiene hooks.
    El chequeo cruza esa huella con el último commit.

    Lo que se declara fuera de alcance, en vez de fingir cobertura:

    * Sin registro de lecturas (hook no instalado, o chat manual) no hay
      evidencia que juzgar: se dice, no se pone un verde silencioso.
    * Un archivo **nuevo** en el commit no se juzga: no se podía leer lo que no
      existía todavía.
    * Los commits anteriores a la primera lectura no se juzgan: nada se mira
      hacia atrás.

    Args:
        report (DoctorReport): Reporte donde registrar el chequeo.
        fix (bool): Ignorado: un aviso de conducta no se repara escribiendo.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="lecturas_previas")

    if not hay_registro(project_dir):
        check.status = "OK"
        check.message = (
            "Sin registro de lecturas (hook `ctxmap hook lectura --instalar` no "
            "instalado): INI-006 no se puede juzgar en este proyecto, y se declara "
            "el hueco en vez de fingir cobertura."
        )
        report.add(check)
        return

    inicio = primera_lectura(project_dir)
    fecha_commit = _git(project_dir, "log", "-1", "--format=%cI", "HEAD")
    if not fecha_commit or not inicio:
        check.status = "OK"
        check.message = "Sin commit o sin lecturas fechadas: no hay nada que cruzar."
        report.add(check)
        return
    if fecha_commit.replace(" ", "T")[:19] < inicio[:19]:
        check.status = "OK"
        check.message = (
            "El último commit es anterior a la primera lectura registrada: "
            "nada se juzga hacia atrás."
        )
        report.add(check)
        return

    leidas = rutas_leidas(project_dir)
    tocados = [
        ruta for estado, ruta in _archivos_del_commit(project_dir)
        if estado in ESTADOS_EXISTENTES
        and os.path.splitext(ruta)[1].lower() in EXTENSIONES_CODIGO
    ]
    sin_leer = sorted(
        ruta for ruta in tocados
        if os.path.normcase(ruta).replace("\\", "/").replace(os.sep, "/").lower() not in leidas
    )

    if not tocados:
        check.status = "OK"
        check.message = (
            "El último commit no toca código existente (solo archivos nuevos, "
            "borrados o documentación): no hay nada que cruzar."
        )
        report.add(check)
        return

    if not sin_leer:
        check.status = "OK"
        check.message = (
            f"Los {len(tocados)} archivo(s) de código del último commit están "
            "en el registro de lecturas."
        )
        report.add(check)
        return

    check.status = "WARN"
    muestra = ", ".join(sin_leer[:3])
    extra = "" if len(sin_leer) <= 3 else f" (+{len(sin_leer) - 3} más)"
    check.message = (
        f"{len(sin_leer)} archivo(s) de código tocados en el último commit sin "
        f"lectura registrada: {muestra}{extra} — REG-INI-006. No es una acusación: "
        "si el hook no estaba activo, la huella no existe."
    )
    report.add(check)


# ── memoria_consultada: INI-007 ───────────────────────────────────────────

#: Comandos que consultan la memoria de todos los proyectos.
COMANDOS_MEMORIA = ("personal",)

#: Días hacia atrás que se consideran «esta sesión de trabajo».
VENTANA_MEMORIA_DIAS = 7


def _dentro_de_la_ventana(ts: str, dias: int = VENTANA_MEMORIA_DIAS) -> bool:
    """Indica si una marca de tiempo cae dentro de la ventana reciente.

    Args:
        ts (str): Marca ISO 8601 de la bitácora.
        dias (int): Días hacia atrás.

    Returns:
        bool: ``True`` si es reciente; una fecha ilegible no se juzga.
    """
    try:
        momento = datetime.fromisoformat(str(ts).replace("Z", ""))
    except ValueError:
        return False
    return (datetime.now() - momento).days <= dias


def check_memoria_consultada(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Verifica que se consulte la memoria multi-proyecto donde no hay memoria propia (INI-007).

    La regla pide buscar en la memoria global «cuando falte contexto histórico».
    Ese «cuando» no se puede juzgar en abstracto, pero sí hay un caso en el que
    falta **siempre**: un proyecto **sin vault propio** no tiene memoria local
    que leer, así que la única fuente es la BD personal. Ahí el chequeo exige
    haberla consultado en la ventana de la sesión.

    Lo que se declara fuera de alcance, en vez de fingir cobertura:

    * Un proyecto **con** vault tiene memoria propia: la regla no aplica y se
      dice, en lugar de apuntarse un verde por no mirar.
    * Sin sesiones en la ventana no hay conducta que juzgar.
    * No se registra ni se imprime la consulta: la bitácora anota el comando,
      nunca su texto.

    Args:
        report (DoctorReport): Reporte donde registrar el chequeo.
        fix (bool): Ignorado: no se repara escribiendo.
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="memoria_consultada")

    if _vault_activo(project_dir):
        check.status = "OK"
        check.message = (
            "El proyecto tiene vault propio: la memoria multi-proyecto no es la "
            "única fuente, así que INI-007 no aplica aquí."
        )
        report.add(check)
        return

    recientes = [
        entrada for entrada in leer(project_dir)
        if _dentro_de_la_ventana(entrada.get("ts", ""))
    ]
    if not recientes:
        check.status = "OK"
        check.message = (
            f"Sin sesiones registradas en los últimos {VENTANA_MEMORIA_DIAS} días: "
            "no hay conducta que juzgar."
        )
        report.add(check)
        return

    if any(entrada.get("comando") in COMANDOS_MEMORIA for entrada in recientes):
        check.status = "OK"
        check.message = (
            "Se consultó la memoria multi-proyecto en esta ventana de trabajo."
        )
        report.add(check)
        return

    check.status = "WARN"
    check.message = (
        f"{len(recientes)} ejecución(es) en {VENTANA_MEMORIA_DIAS} día(s) en un "
        "proyecto sin vault propio, sin una sola consulta a la memoria global — "
        "REG-INI-007. Prueba: `ctxmap personal query \"términos\" --limite 5`."
    )
    report.add(check)


CHECKS_SESION = (
    check_bitacora_sesion,
    check_permisos_explicitos,
    check_tag_con_puerta_verde,
    check_secreto_en_el_historial,
    check_historia_preservada,
    check_doctor_rapido,
    check_decisiones_con_porque,
    check_lecturas_previas,
    check_memoria_consultada,
)

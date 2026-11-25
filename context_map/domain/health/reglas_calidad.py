"""Chequeos de calidad del repositorio (higiene, arquitectura y documentación).

Convierte en puerta dura las reglas del catálogo que describen el **estado del
repo** —no lo que el agente hizo en una sesión— y que hasta ahora estaban en
``manual`` por comodidad:

* ``version_documentada`` (``REG-PUB-001``): la versión de ``pyproject.toml``
  aparece en el ``CHANGELOG``.
* ``derivados_fuera_de_git`` (``REG-LIM-003``): ni vault ni estado en el índice.
* ``raiz_limpia`` (``REG-ARQ-002``): la raíz solo lleva lo declarado.
* ``capas_respetadas`` (``REG-ARQ-001`` + ``REG-ARQ-003``): las cinco capas
  existen y los imports no suben de capa. Tiene **tope de no regresión**: la
  deuda actual está congelada y una violación nueva rompe la puerta.
* ``modulos_con_test`` (``REG-ARQ-004``): todo submódulo de ``domain/`` aparece
  en algún test.
* ``docstrings_y_tipos`` (``REG-DOC-002``): módulos con docstring y un suelo de
  anotaciones que no se degrada.
* ``idioma_de_la_documentacion`` (``REG-DOC-001``): los documentos del repo están
  en español (salvo los que declaran ser traducción).

Todos son ``WARN`` y ninguno escribe archivos.
"""

from __future__ import annotations

import ast
import io
import os
import re
from typing import Optional

from context_map.domain.health.doctor import DoctorCheck, DoctorReport

#: Capas de la arquitectura, de dentro hacia fuera.
CAPAS = ("core", "domain", "application", "infrastructure", "presentation")

#: Qué capa puede importar a cuál (lo de dentro nunca mira hacia fuera).
PERMITIDO: dict[str, set[str]] = {
    "core": set(),
    "domain": {"core"},
    "application": {"core", "domain"},
    "infrastructure": {"core", "domain"},
    "presentation": {"core", "domain"},
}

#: Tope de no regresión de imports cruzados, medido el 2026-11-25.
#: **Bájalo cuando refactorices**: una violación nueva rompe la puerta, y el
#: número solo puede mejorar. Congelar la deuda es el único modo de no empeorar
#: sin parar el trabajo.
MAX_IMPORTS_CRUZADOS = 53

#: Suelo de anotaciones de tipo (15 % actual; por encima del 20 % se avisa).
TOPE_SIN_TIPOS = 0.20

#: Ratio de palabras inglesas a partir del cual un documento no está en español.
TOPE_INGLES = 0.10

#: Palabras que delatan prosa inglesa (frecuentes y sin ambigüedad en español).
PALABRAS_INGLESAS = (
    "the", "and", "should", "which", "with the", "from the", "you can",
    "this is", "there is", "make sure", "in order to",
)

#: Archivos de la raíz que la norma permite (ver `AGENTS.md` §1.1).
RAIZ_PERMITIDA = frozenset({
    "README.md", "README_EN.md", "README_TECNICO.md", "LICENSE",
    "pyproject.toml", "AGENTS.md", "CLAUDE.md", "CHANGELOG.md",
    ".gitignore", ".pre-commit-hooks.yaml", "Makefile", "mkdocs.yml",
    "CODE_OF_CONDUCT.md", "CONTRIBUTING.md", "action.yml", "uv.lock",
})

#: Lo que nunca puede estar versionado (estado, índices, bases y vault).
DERIVADOS = re.compile(
    r"(^\.context-map/(vault-|state|history|chats|raw))|"
    r"(\.db$)|(\.sqlite3?$)|(\bfts5_)|(/\.context-map/)",
    re.IGNORECASE,
)

#: Archivos que declaran ser traducción al inglés.
TRADUCCIONES = re.compile(r"(_EN|_en|\.en)\.md$")


def _texto(ruta: str, limite: int = 400_000) -> str:
    """Lee un archivo de texto sin reventar con binarios ni gigantes."""
    try:
        if os.path.getsize(ruta) > limite:
            return ""
        with open(ruta, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _version_declarada(project_dir: str) -> Optional[str]:
    """Versión de ``pyproject.toml`` (``None`` si no hay proyecto Python)."""
    texto = _texto(os.path.join(project_dir, "pyproject.toml"))
    encontrado = re.search(r'^version\s*=\s*"([^"]+)"', texto, re.MULTILINE)
    return encontrado.group(1) if encontrado else None


#: Carpetas que nunca se escanean: entornos, dependencias y artefactos.
CARPETAS_IGNORADAS = frozenset({
    ".git", "node_modules", "__pycache__", "site-packages", "dist", "build",
    ".tox", ".nox", ".mypy_cache", ".pytest_cache", ".ruff_cache",
})


def _es_carpeta_ignorada(nombre: str) -> bool:
    """¿La carpeta es un entorno, una dependencia o un artefacto?

    El nombre del entorno no es fijo: hay proyectos con ``.venv_drive_slow`` o
    ``venv-local``. Se descarta por prefijo y por sufijo, no por lista cerrada:
    escanear las dependencias instaladas convierte cualquier chequeo en ruido.
    """
    minuscula = nombre.lower()
    return (
        minuscula in CARPETAS_IGNORADAS
        or minuscula.startswith((".venv", "venv", "virtualenv"))
        or minuscula.endswith((".egg-info", "-info"))
    )


def check_version_documentada(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """La versión del paquete debe estar anunciada en el CHANGELOG.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (el anuncio lo escribe una persona).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="version_documentada")
    version = _version_declarada(project_dir)
    if version is None:
        check.status = "OK"
        check.message = "Sin pyproject.toml: no hay versión que anunciar."
        report.add(check)
        return

    changelog = _texto(os.path.join(project_dir, "CHANGELOG.md"))
    if not changelog:
        check.status = "WARN"
        check.message = f"No hay CHANGELOG.md y la versión declarada es {version} (REG-PUB-001)."
        report.add(check)
        return

    if re.search(rf"\[?{re.escape(version)}\]?|v{re.escape(version)}", changelog):
        check.status = "OK"
        check.message = f"La versión {version} está anunciada en el CHANGELOG."
    else:
        check.status = "WARN"
        check.message = (
            f"La versión {version} de pyproject.toml no aparece en CHANGELOG.md "
            "(REG-PUB-001)."
        )
    report.add(check)


def check_derivados_fuera_de_git(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """El vault regenerable y el estado no se versionan.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (sacarlo del índice es decisión del dueño).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="derivados_fuera_de_git")
    try:
        import subprocess

        salida = subprocess.run(
            ["git", "ls-files"], cwd=project_dir, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        salida = None

    if salida is None or salida.returncode != 0:
        check.status = "OK"
        check.message = "Sin repositorio git: no hay índice que revisar."
        report.add(check)
        return

    rastreados = [a for a in salida.stdout.splitlines() if a.strip()]
    derivados = [a for a in rastreados if DERIVADOS.search(a.replace("\\", "/"))]
    if derivados:
        check.status = "WARN"
        check.message = (
            f"{len(derivados)} archivo(s) derivado(s) versionado(s): "
            f"{', '.join(derivados[:3])}. El vault se regenera; el estado se pierde "
            "en cada build (REG-LIM-003)."
        )
    else:
        check.status = "OK"
        check.message = f"Nada derivado en el índice ({len(rastreados)} archivo(s))."
    report.add(check)


def check_raiz_limpia(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """La raíz solo lleva los archivos que la norma declara.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (mover archivos es una decisión).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="raiz_limpia")
    try:
        entradas = os.listdir(project_dir)
    except OSError:
        check.status = "OK"
        check.message = "No se pudo leer la raíz."
        report.add(check)
        return

    sueltos = sorted(
        nombre for nombre in entradas
        if os.path.isfile(os.path.join(project_dir, nombre)) and nombre not in RAIZ_PERMITIDA
    )
    if sueltos:
        check.status = "WARN"
        check.message = (
            f"{len(sueltos)} archivo(s) fuera de la raíz declarada: "
            f"{', '.join(sueltos[:4])}. Muévelos a su capa o decláralos en la norma "
            "(REG-ARQ-002)."
        )
    else:
        check.status = "OK"
        check.message = "Raíz limpia: solo los archivos declarados en la norma."
    report.add(check)


def _imports_cruzados(project_dir: str) -> list[str]:
    """Lista los imports que suben de capa (``capa -> capa``)."""
    violaciones: list[str] = []
    for capa in CAPAS:
        carpeta = os.path.join(project_dir, "context_map", capa)
        if not os.path.isdir(carpeta):
            continue
        for base, _dirs, archivos in os.walk(carpeta):
            if "__pycache__" in base:
                continue
            for archivo in archivos:
                if not archivo.endswith(".py"):
                    continue
                ruta = os.path.join(base, archivo)
                try:
                    arbol = ast.parse(_texto(ruta))
                except SyntaxError:
                    continue
                for nodo in ast.walk(arbol):
                    modulos: list[str] = []
                    if isinstance(nodo, ast.ImportFrom) and nodo.module:
                        modulos = [nodo.module]
                    elif isinstance(nodo, ast.Import):
                        modulos = [alias.name for alias in nodo.names]
                    for modulo in modulos:
                        partes = modulo.split(".")
                        if len(partes) < 2 or partes[0] != "context_map":
                            continue
                        destino = partes[1]
                        if destino in CAPAS and destino != capa and destino not in PERMITIDO[capa]:
                            relativa = os.path.relpath(ruta, project_dir).replace("\\", "/")
                            violaciones.append(f"{relativa}:{nodo.lineno} {capa}->{destino}")
    return violaciones


def check_capas_respetadas(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Las capas existen y nadie importa hacia fuera sin tope nuevo.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (refactorizar capas es trabajo humano).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="capas_respetadas")
    paquete = os.path.join(project_dir, "context_map")
    if not os.path.isdir(paquete):
        check.status = "OK"
        check.message = "Sin paquete `context_map/`: no hay capas que revisar."
        report.add(check)
        return

    ausentes = [capa for capa in CAPAS if not os.path.isdir(os.path.join(paquete, capa))]
    violaciones = _imports_cruzados(project_dir)

    if ausentes:
        check.status = "WARN"
        check.message = f"Falta(n) la(s) capa(s) {', '.join(ausentes)} (REG-ARQ-001)."
    elif len(violaciones) > MAX_IMPORTS_CRUZADOS:
        check.status = "WARN"
        nuevas = violaciones[MAX_IMPORTS_CRUZADOS:]
        check.message = (
            f"{len(violaciones)} import(s) que suben de capa, tope {MAX_IMPORTS_CRUZADOS}: "
            f"{', '.join(nuevas[:3])}. La deuda vieja está congelada; esta es nueva "
            "(REG-ARQ-003)."
        )
    else:
        check.status = "OK"
        check.message = (
            f"Cinco capas presentes; {len(violaciones)} import(s) cruzado(s), "
            f"dentro del tope de no regresión ({MAX_IMPORTS_CRUZADOS})."
        )
    report.add(check)


def check_modulos_con_test(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Cada submódulo de ``domain/`` aparece en algún test.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (escribir tests es trabajo humano).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="modulos_con_test")
    dominio = os.path.join(project_dir, "context_map", "domain")
    tests = os.path.join(project_dir, "context_map", "__tests__")
    if not os.path.isdir(dominio) or not os.path.isdir(tests):
        check.status = "OK"
        check.message = "Sin `domain/` o sin suite: no aplica."
        report.add(check)
        return

    fuentes = "\n".join(
        _texto(os.path.join(tests, archivo))
        for archivo in os.listdir(tests)
        if archivo.startswith("test_") and archivo.endswith(".py")
    )
    submodulos = sorted(
        nombre for nombre in os.listdir(dominio)
        if os.path.isdir(os.path.join(dominio, nombre)) and nombre != "__pycache__"
    )
    sin_test = [
        nombre for nombre in submodulos
        if not re.search(rf"\b{re.escape(nombre)}\b", fuentes)
    ]
    if sin_test:
        check.status = "WARN"
        check.message = (
            f"{len(sin_test)} de {len(submodulos)} submódulo(s) de domain/ sin test "
            f"que los nombre: {', '.join(sin_test[:4])} (REG-ARQ-004)."
        )
    else:
        check.status = "OK"
        check.message = f"Los {len(submodulos)} submódulos de domain/ aparecen en la suite."
    report.add(check)


def check_docstrings_y_tipos(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Módulos con docstring y un suelo de anotaciones que no se degrada.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (documentar a mano es el trabajo).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="docstrings_y_tipos")
    paquete = os.path.join(project_dir, "context_map")
    if not os.path.isdir(paquete):
        check.status = "OK"
        check.message = "Sin paquete `context_map/`: no aplica."
        report.add(check)
        return

    sin_docstring: list[str] = []
    total = 0
    sin_tipos = 0
    for base, _dirs, archivos in os.walk(paquete):
        if "__pycache__" in base:
            continue
        for archivo in archivos:
            if not archivo.endswith(".py") or archivo == "__init__.py":
                continue
            ruta = os.path.join(base, archivo)
            es_test = "__tests__" in ruta.replace("\\", "/")
            try:
                arbol = ast.parse(_texto(ruta))
            except SyntaxError:
                continue
            if not es_test and not ast.get_docstring(arbol):
                sin_docstring.append(
                    os.path.relpath(ruta, project_dir).replace("\\", "/")
                )
            for nodo in ast.walk(arbol):
                if not isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                total += 1
                argumentos = list(nodo.args.args[1:]) + list(nodo.args.kwonlyargs)
                if nodo.returns is None or any(a.annotation is None for a in argumentos):
                    sin_tipos += 1

    ratio = sin_tipos / total if total else 0.0
    if sin_docstring:
        check.status = "WARN"
        check.message = (
            f"{len(sin_docstring)} módulo(s) sin docstring: "
            f"{', '.join(sin_docstring[:3])} (REG-DOC-002)."
        )
    elif ratio > TOPE_SIN_TIPOS:
        check.status = "WARN"
        check.message = (
            f"{sin_tipos} de {total} funciones ({ratio:.0%}) sin anotaciones completas; "
            f"el suelo es {TOPE_SIN_TIPOS:.0%} (REG-DOC-002)."
        )
    else:
        check.status = "OK"
        check.message = (
            f"Docstrings al día; {ratio:.0%} de funciones sin anotaciones completas "
            f"(suelo {TOPE_SIN_TIPOS:.0%})."
        )
    report.add(check)


def check_idioma_de_la_documentacion(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Los documentos del repo se escriben en español.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (traducir es trabajo humano).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="idioma_de_la_documentacion")
    sospechosos: list[str] = []
    revisados = 0
    for base, dirs, archivos in os.walk(project_dir):
        dirs[:] = [
            d for d in dirs
            if not _es_carpeta_ignorada(d) and not d.startswith(".context-map")
        ]
        for archivo in archivos:
            if not archivo.endswith(".md") or TRADUCCIONES.search(archivo):
                continue
            ruta = os.path.join(base, archivo)
            palabras = re.findall(r"[a-záéíóúñü]+", _texto(ruta).lower())
            if len(palabras) < 200:
                continue
            revisados += 1
            inglesas = sum(palabras.count(p) for p in PALABRAS_INGLESAS)
            ratio = inglesas / len(palabras)
            if ratio > TOPE_INGLES:
                relativa = os.path.relpath(ruta, project_dir).replace("\\", "/")
                sospechosos.append(f"{relativa} ({ratio:.0%})")

    if sospechosos:
        check.status = "WARN"
        check.message = (
            f"{len(sospechosos)} documento(s) con prosa inglesa: "
            f"{', '.join(sospechosos[:3])}. El proyecto se documenta en español "
            "técnico (REG-DOC-001)."
        )
    else:
        check.status = "OK"
        check.message = f"{revisados} documento(s) en español técnico."
    report.add(check)


#: Chequeos de calidad del repositorio.
CHECKS_CALIDAD = (
    check_version_documentada,
    check_derivados_fuera_de_git,
    check_raiz_limpia,
    check_capas_respetadas,
    check_modulos_con_test,
    check_docstrings_y_tipos,
    check_idioma_de_la_documentacion,
)

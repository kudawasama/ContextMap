"""Chequeos del contenido del vault (memoria viva y humanización).

Cierra las reglas del catálogo que hablan del **vault**, no del motor:

* ``dominio_documentado`` (``REG-DOC-005``): si hay dominio, hay
  ``7.0-MANUAL/DOMINIO.md`` y no es un esqueleto.
* ``fuentes_procesadas`` (``REG-DOC-006`` + ``REG-MEM-001``): ninguna fuente de
  ``raw/`` ni chat de ``chats/`` es más nuevo que el brief.
* ``lecciones_completas`` (``REG-MEM-003``): cada lección de ``8.0-KNOWLEDGE/``
  tiene lección, solución, prompt, instrucción y conexiones.
* ``notas_sin_plantilla`` (``REG-HUM-001`` + ``REG-HUM-005``): sin marcadores de
  plantilla ni relleno en las notas.
* ``vault_acotado`` (``REG-LIM-001``): el vault no pasa del peso acordado.

Todos son ``WARN``; ninguno toca el contenido del usuario.
"""

from __future__ import annotations

import io
import os
import re
import unicodedata
from typing import Optional

from context_map.domain.health.doctor import DoctorCheck, DoctorReport

#: Peso a partir del cual el vault necesita build por secciones (15 MB).
LIMITE_MB = 15.0

#: Tamaño mínimo para considerar que ``DOMINIO.md`` está redactado.
MINIMO_DOMINIO = 500

#: Marcadores de plantilla que sí son inequívocos (fuera de bloques de código).
MARCADORES_PLANTILLA = re.compile(
    r"\{\{|\[completar\]|lorem ipsum|pendiente de redactar|<vac[ií]o>", re.IGNORECASE
)

#: Secciones que debe tener una lección reutilizable, con sus sinónimos.
#: «Cómo se resolvió» admite «diseño» y «fases»: una lección puede contar cómo se
#: diseñó cuando todavía no hay solución cerrada, y exigirle una solución que no
#: existe obligaría a inventarla.
SECCIONES_LECCION = {
    "lección": ("leccion", "lección", "aprendizaje"),
    "cómo se resolvió": ("como se resolvio", "cómo se resolvió", "solucion", "solución",
                         "como se soluciono", "cómo se solucionó", "remedio",
                         "diseno", "diseño", "fases"),
    "prompt": ("prompt", "indicacion", "indicación"),
    "instrucción": ("instruccion", "instrucción"),
    "conexiones": ("conexion", "conexión", "conexiones"),
}


def _texto(ruta: str) -> str:
    """Lee un archivo de texto del vault (vacío si no se puede)."""
    try:
        with io.open(ruta, encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def _sin_acentos(texto: str) -> str:
    """Minúsculas y sin acentos, para comparar secciones escritas a mano."""
    normalizado = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in normalizado if unicodedata.category(c) != "Mn")


def _vault_activo(project_dir: str) -> Optional[str]:
    """Ruta del vault del proyecto, o ``None`` si no hay vault."""
    contexto = os.path.join(project_dir, ".context-map")
    if not os.path.isdir(contexto):
        return None
    try:
        vaults = sorted(
            nombre for nombre in os.listdir(contexto)
            if nombre.startswith("vault-") and os.path.isdir(os.path.join(contexto, nombre))
        )
    except OSError:
        return None
    return os.path.join(contexto, vaults[0]) if vaults else None


def _notas(vault: str):
    """Recorre las notas ``.md`` del vault una a una."""
    for base, _dirs, archivos in os.walk(vault):
        for archivo in archivos:
            if archivo.endswith(".md"):
                yield os.path.join(base, archivo)


def check_dominio_documentado(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """El dominio se documenta en ``7.0-MANUAL/DOMINIO.md``.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (el manual se escribe leyendo el código).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="dominio_documentado")
    dominio = os.path.join(project_dir, "context_map", "domain")
    if not os.path.isdir(dominio):
        check.status = "OK"
        check.message = "Sin `domain/`: no hay lógica nuclear que documentar."
        report.add(check)
        return

    vault = _vault_activo(project_dir)
    if vault is None:
        check.status = "OK"
        check.message = "Sin vault: no hay dónde documentar el dominio."
        report.add(check)
        return

    ruta = os.path.join(vault, "7.0-MANUAL", "DOMINIO.md")
    if not os.path.isfile(ruta):
        check.status = "WARN"
        check.message = "Hay `domain/` y no existe `7.0-MANUAL/DOMINIO.md` (REG-DOC-005)."
    elif len(_texto(ruta).strip()) < MINIMO_DOMINIO:
        check.status = "WARN"
        check.message = (
            f"`7.0-MANUAL/DOMINIO.md` tiene menos de {MINIMO_DOMINIO} caracteres: "
            "es un esqueleto, no la lógica nuclear (REG-DOC-005)."
        )
    else:
        check.status = "OK"
        check.message = "DOMINIO.md documenta la lógica nuclear."
    report.add(check)


def check_fuentes_procesadas(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Las fuentes externas y los chats se procesan con ``refresh``.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (procesar es correr ``refresh``).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="fuentes_procesadas")
    contexto = os.path.join(project_dir, ".context-map")
    brief = os.path.join(contexto, "CONTEXT.md")
    if not os.path.isdir(contexto) or not os.path.isfile(brief):
        check.status = "OK"
        check.message = "Sin `.context-map/`: no hay fuentes que procesar."
        report.add(check)
        return

    referencia = os.path.getmtime(brief)
    pendientes: list[str] = []
    for subcarpeta in ("raw", "chats"):
        carpeta = os.path.join(contexto, subcarpeta)
        if not os.path.isdir(carpeta):
            continue
        for base, _dirs, archivos in os.walk(carpeta):
            for archivo in archivos:
                ruta = os.path.join(base, archivo)
                try:
                    if os.path.getmtime(ruta) > referencia:
                        pendientes.append(
                            os.path.relpath(ruta, project_dir).replace("\\", "/")
                        )
                except OSError:
                    continue

    if pendientes:
        check.status = "WARN"
        check.message = (
            f"{len(pendientes)} fuente(s) nueva(s) sin procesar: "
            f"{', '.join(pendientes[:3])}. Ejecuta `ctxmap refresh .` "
            "(REG-DOC-006 / REG-MEM-001)."
        )
    else:
        check.status = "OK"
        check.message = "Sin fuentes pendientes: raw/ y chats/ ya están procesados."
    report.add(check)


def check_lecciones_completas(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Cada lección reutilizable tiene las cinco secciones.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (redactar la lección es trabajo humano).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="lecciones_completas")
    vault = _vault_activo(project_dir)
    if vault is None:
        check.status = "OK"
        check.message = "Sin vault: no hay lecciones que revisar."
        report.add(check)
        return

    carpeta = os.path.join(vault, "8.0-KNOWLEDGE")
    if not os.path.isdir(carpeta):
        check.status = "OK"
        check.message = "Sin `8.0-KNOWLEDGE/`: no hay lecciones."
        report.add(check)
        return

    total = 0
    incompletas: list[str] = []
    indice = os.path.basename(carpeta) + ".md"
    for ruta in sorted(_notas(carpeta)):
        if os.path.dirname(ruta) != carpeta:
            continue  # las subcarpetas no son lecciones
        if os.path.basename(ruta) == indice:
            continue  # el índice de la sección cuelga de ella, no es una lección
        total += 1
        texto = _sin_acentos(_texto(ruta))
        faltan = [
            nombre for nombre, sinonimos in SECCIONES_LECCION.items()
            if not any(s in texto for s in sinonimos)
        ]
        if faltan:
            incompletas.append(f"{os.path.basename(ruta)} (falta {', '.join(faltan)})")

    if incompletas:
        check.status = "WARN"
        check.message = (
            f"{len(incompletas)} de {total} lección(es) sin las cinco secciones: "
            f"{'; '.join(incompletas[:2])} (REG-MEM-003)."
        )
    else:
        check.status = "OK"
        check.message = f"Las {total} lecciones tienen sus cinco secciones."
    report.add(check)


def _sin_codigo(texto: str) -> str:
    """Retira bloques cercados y código inline antes de buscar marcadores."""
    sin_bloques = re.sub(r"```.*?```", " ", texto, flags=re.DOTALL)
    return re.sub(r"`[^`\n]*`", " ", sin_bloques)


def check_notas_sin_plantilla(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """Las notas están redactadas: ni marcadores de plantilla ni relleno.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (redactar la nota es trabajo humano).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="notas_sin_plantilla")
    vault = _vault_activo(project_dir)
    if vault is None:
        check.status = "OK"
        check.message = "Sin vault: no hay notas que revisar."
        report.add(check)
        return

    total = 0
    plantillas: list[str] = []
    relleno: list[str] = []
    for ruta in sorted(_notas(vault)):
        nombre = os.path.basename(ruta)
        # Una plantilla contiene marcadores por definición: se reconoce por el
        # nombre y por la carpeta `templates/` del vault.
        en_plantillas = "templates" in ruta.replace("\\", "/").split("/")
        if en_plantillas or nombre.lower().startswith(("plantilla", "template")):
            continue
        total += 1
        cuerpo = _sin_codigo(_texto(ruta))
        if MARCADORES_PLANTILLA.search(cuerpo):
            plantillas.append(nombre)
        if "!!" in cuerpo or "¡¡" in cuerpo:
            relleno.append(nombre)

    if plantillas or relleno:
        check.status = "WARN"
        partes = []
        if plantillas:
            partes.append(
                f"{len(plantillas)} nota(s) con marcadores de plantilla: "
                f"{', '.join(plantillas[:3])}"
            )
        if relleno:
            partes.append(
                f"{len(relleno)} nota(s) con signos de admiración dobles: "
                f"{', '.join(relleno[:3])}"
            )
        check.message = " · ".join(partes) + " (REG-HUM-001 / REG-HUM-005)."
    else:
        check.status = "OK"
        check.message = f"Las {total} notas están redactadas, sin marcadores de plantilla."
    report.add(check)


def check_vault_acotado(
    report: DoctorReport, fix: bool = False, project_dir: str = "."
) -> None:
    """El vault se mantiene por debajo del peso acordado.

    Args:
        report (DoctorReport): Reporte donde se añade el resultado.
        fix (bool): Ignorado (podar conocimiento es una decisión).
        project_dir (str): Raíz del proyecto.
    """
    check = DoctorCheck(name="vault_acotado")
    vault = _vault_activo(project_dir)
    if vault is None:
        check.status = "OK"
        check.message = "Sin vault: no hay peso que medir."
        report.add(check)
        return

    bytes_totales = 0
    notas = 0
    for base, _dirs, archivos in os.walk(vault):
        for archivo in archivos:
            try:
                bytes_totales += os.path.getsize(os.path.join(base, archivo))
            except OSError:
                continue
            if archivo.endswith(".md"):
                notas += 1

    megas = bytes_totales / (1024 * 1024)
    if megas > LIMITE_MB:
        check.status = "WARN"
        check.message = (
            f"El vault pesa {megas:.1f} MB con {notas} nota(s); el límite acordado es "
            f"{LIMITE_MB:.0f} MB. Usa `build` por secciones (REG-LIM-001)."
        )
    else:
        check.status = "OK"
        check.message = f"Vault acotado: {megas:.1f} MB con {notas} nota(s)."
    report.add(check)


#: Chequeos del contenido del vault.
CHECKS_VAULT = (
    check_dominio_documentado,
    check_fuentes_procesadas,
    check_lecciones_completas,
    check_notas_sin_plantilla,
    check_vault_acotado,
)

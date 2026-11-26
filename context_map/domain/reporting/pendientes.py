"""Cruce determinista de las cuatro fuentes de pendientes (``REG-INI-004``).

Responder «¿qué queda pendiente?» leyendo un solo documento es la forma más
rápida de mentir sin querer: el backlog manual, las tareas, el diario y los
documentos sin procesar dicen cosas distintas, y la respuesta completa es la
unión. Como eso es mecánico, lo hace el motor en vez de la memoria del agente.

Fuentes que se cruzan, todas dentro del vault activo:

1. ``7.0-MANUAL/BACKLOG.md``       — backlog escrito a mano.
2. ``5.0-BACKLOG/5.1-Tareas.md``   — tareas con casilla.
3. ``7.0-MANUAL/Diario/``          — lo abierto en la entrada más reciente.
4. ``3.2-DOCUMENTOS/``             — documentos que aún no tienen nota que los
   cite (si nadie los nombró, nadie los trabajó).

Una fuente **ausente** se declara como tal: no se puede cruzar lo que no existe,
y callarlo convertiría el cruce en una lista incompleta con aspecto de completa.

Pero «ausente» y «no aplica» no son lo mismo. ``3.2-DOCUMENTOS/`` solo nace
cuando el proyecto ingirió documentos externos: en un proyecto que nunca ingirió
nada, avisar cada vez de que la carpeta falta es ruido —y un aviso que siempre
suena se aprende a ignorar. Se declara **no aplica** cuando no hay una sola razón
para que exista (medido: en los dos proyectos con vault que se revisaron, la
carpeta faltaba con ``raw/docs`` vacío). Lo que sí indica que debería existir se
nombra: con documentos pendientes de procesar, la ausencia se avisa.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any

#: Nombre y ubicación de cada fuente dentro del vault.
FUENTES: tuple[tuple[str, str, str], ...] = (
    ("backlog", os.path.join("7.0-MANUAL", "BACKLOG.md"), "Backlog manual"),
    ("tareas", os.path.join("5.0-BACKLOG", "5.1-Tareas.md"), "Tareas"),
    ("diario", os.path.join("7.0-MANUAL", "Diario"), "Diario"),
    ("documentos", "3.2-DOCUMENTOS", "Documentos sin nota"),
)

#: Casilla sin marcar, con o sin viñeta.
CASILLA_ABIERTA = re.compile(r"^\s*[-*+]\s*\[ \]\s*(?P<texto>\S.*)$", re.MULTILINE)

#: Una entrada de diario cuenta como «lo último» si su nombre es una fecha.
FECHA_EN_NOMBRE = re.compile(r"(?P<año>\d{4})-(?P<mes>\d{2})-(?P<dia>\d{2})")

#: Un pendiente escrito en el diario sin casilla también es un pendiente.
PENDIENTE_EN_PROSA = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:pendiente|queda|queda pendiente|falta)\b[:\s]+(?P<texto>\S.*)$",
    re.IGNORECASE | re.MULTILINE,
)


#: Estados de una tabla de backlog que significan «sigue abierto».
ESTADO_ABIERTO = re.compile(
    r"^\W*(abiert[oa]|pendiente|en curso|en progreso|por hacer|todo)\W*$", re.IGNORECASE
)

#: Línea separadora de una tabla Markdown (``|---|---|``).
SEPARADOR_TABLA = re.compile(r"^\s*\|[\s:|-]+\|\s*$")

#: Fila de tabla Markdown (no la línea de separación ``|---|---|``).
FILA_TABLA = re.compile(r"^\s*\|(?!\s*[-:]+\s*\|).+\|\s*$")


def _vault_activo(project_dir: str = ".") -> str | None:
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


def _leer(ruta: str) -> str:
    """Lee un archivo de texto, con tolerancia total (vacío si no se puede)."""
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _casillas(texto: str, limite: int) -> tuple[list[str], int]:
    """Extrae las casillas sin marcar de un texto.

    Args:
        texto (str): Contenido Markdown.
        limite (int): Máximo de elementos a devolver.

    Returns:
        Tuple[List[str], int]: Textos hasta ``limite`` y el total encontrado.
    """
    encontrados = [m.group("texto").strip() for m in CASILLA_ABIERTA.finditer(texto)]
    return encontrados[:limite], len(encontrados)


def _filas_abiertas(texto: str) -> list[str]:
    """Filas de tabla cuyo estado sigue abierto (``REG-INI-004``).

    Un backlog puede estar escrito como tabla con columna de estado en vez de
    casillas. Si solo se buscaran casillas, ese backlog se leería como «nada
    pendiente» — el peor error posible en un cruce: informar de vacío donde hay
    trabajo.

    Args:
        texto (str): Contenido Markdown.

    Returns:
        List[str]: Filas abiertas tal cual, sin interpretarlas.
    """
    lineas = texto.splitlines()
    abiertas: list[str] = []
    for indice, linea in enumerate(lineas):
        if not FILA_TABLA.match(linea):
            continue
        # La cabecera de la tabla nombra la columna «Pendiente»: no es un pendiente.
        siguiente = lineas[indice + 1] if indice + 1 < len(lineas) else ""
        if SEPARADOR_TABLA.match(siguiente):
            continue
        celdas = [c.strip() for c in linea.strip().strip("|").split("|")]
        if any(ESTADO_ABIERTO.match(c) for c in celdas):
            abiertas.append(linea.strip())
    return abiertas


def _pendientes_de_texto(texto: str, limite: int) -> tuple[list[str], int]:
    """Reúne los pendientes de un texto: casillas, filas de tabla y prosa.

    Args:
        texto (str): Contenido Markdown.
        limite (int): Máximo de elementos a devolver.

    Returns:
        Tuple[List[str], int]: Pendientes hasta ``limite`` y el total.
    """
    casillas, _ = _casillas(texto, limite=10_000)
    filas = _filas_abiertas(texto)
    prosa = [m.group("texto").strip() for m in PENDIENTE_EN_PROSA.finditer(texto)]

    vistos: list[str] = []
    for item in [*casillas, *filas, *prosa]:
        if item and item not in vistos:
            vistos.append(item)
    return vistos[:limite], len(vistos)


def _ultima_entrada_diario(carpeta: str) -> str | None:
    """Devuelve la entrada de diario más reciente por fecha en el nombre."""
    try:
        entradas = [n for n in os.listdir(carpeta) if n.endswith(".md")]
    except OSError:
        return None
    con_fecha = []
    for nombre in entradas:
        m = FECHA_EN_NOMBRE.search(nombre)
        if m:
            con_fecha.append((f"{m.group('año')}-{m.group('mes')}-{m.group('dia')}", nombre))
    if con_fecha:
        return os.path.join(carpeta, sorted(con_fecha)[-1][1])
    return os.path.join(carpeta, sorted(entradas)[-1]) if entradas else None


def _documentos_sin_nota(vault: str, limite: int) -> tuple[list[str], int, bool]:
    """Documentos de ``3.2-DOCUMENTOS/`` que ninguna nota del vault menciona.

    Args:
        vault (str): Raíz del vault.
        limite (int): Máximo de elementos a devolver.

    Returns:
        Tuple[List[str], int, bool]: Nombres, total y si la carpeta existía.
    """
    carpeta = os.path.join(vault, "3.2-DOCUMENTOS")
    if not os.path.isdir(carpeta):
        return [], 0, False
    try:
        docs = sorted(n for n in os.listdir(carpeta) if n.lower().endswith((".md", ".pdf")))
    except OSError:
        return [], 0, False

    citados: list[str] = []
    for base, _dirs, archivos in os.walk(vault):
        for archivo in archivos:
            if archivo.endswith(".md"):
                citados.append(_leer(os.path.join(base, archivo)))
    cuerpo = "\n".join(citados)

    sin_nota = [d for d in docs if os.path.splitext(d)[0] not in cuerpo]
    return sin_nota[:limite], len(sin_nota), True


def _documentos_pendientes(project_dir: str) -> int:
    """Cuenta los documentos externos en espera de convertirse en nota.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        int: Archivos bajo ``.context-map/raw/docs`` (0 si no hay carpeta).
    """
    raw = os.path.join(project_dir, ".context-map", "raw", "docs")
    if not os.path.isdir(raw):
        return 0
    try:
        return sum(len(archivos) for _base, _dirs, archivos in os.walk(raw))
    except OSError:
        return 0


def _aplica_documentos(vault: str, project_dir: str) -> tuple[bool, str]:
    """Decide si la fuente «Documentos sin nota» tiene sentido en este proyecto.

    Args:
        vault (str): Raíz del vault activo.
        project_dir (str): Raíz del proyecto.

    Returns:
        Tuple[bool, str]: Si aplica y, cuando no, el motivo declarado.
    """
    if os.path.isdir(os.path.join(vault, "3.2-DOCUMENTOS")):
        return True, ""
    if _documentos_pendientes(project_dir) > 0:
        return True, ""
    return False, "el proyecto no ingirió documentos externos (`3.2-DOCUMENTOS/` nace con la primera ingesta)"


def cruzar_fuentes(project_dir: str = ".", limite: int = 12) -> dict[str, Any]:
    """Cruza las cuatro fuentes y devuelve los pendientes con su origen.

    Args:
        project_dir (str): Raíz del proyecto.
        limite (int): Máximo de pendientes por fuente.

    Returns:
        dict: ``proyecto``, ``vault``, ``fuentes`` (una por fuente, con
        ``presente``/``total``/``items``), ``total`` y ``generado``.
    """
    vault = _vault_activo(project_dir)
    resultado: dict[str, Any] = {
        "proyecto": os.path.basename(os.path.abspath(project_dir)) or ".",
        "vault": vault,
        "fuentes": [],
        "total": 0,
        "generado": datetime.now().isoformat(timespec="seconds"),
    }
    if not vault:
        return resultado

    for clave, relativa, nombre in FUENTES:
        ruta = os.path.join(vault, relativa)
        fuente: dict[str, Any] = {
            "clave": clave,
            "nombre": nombre,
            "ruta": "/".join((".context-map", os.path.basename(vault), relativa)),
            "presente": os.path.exists(ruta),
            "aplica": True,
            "items": [],
            "total": 0,
        }
        if clave == "documentos":
            aplica, motivo = _aplica_documentos(vault, project_dir)
            fuente["aplica"] = aplica
            if not aplica:
                fuente["motivo"] = motivo

        if fuente["presente"]:
            if clave == "diario":
                entrada = _ultima_entrada_diario(ruta)
                if entrada:
                    items, total = _pendientes_de_texto(_leer(entrada), limite)
                    fuente["items"] = items
                    fuente["total"] = total
                    fuente["entrada"] = os.path.basename(entrada)
            elif clave == "documentos":
                items, total, _ = _documentos_sin_nota(vault, limite)
                fuente["items"] = items
                fuente["total"] = total
            else:
                items, total = _pendientes_de_texto(_leer(ruta), limite)
                fuente["items"] = items
                fuente["total"] = total

        resultado["total"] += fuente["total"]
        resultado["fuentes"].append(fuente)

    return resultado


def fuentes_no_aplicables(cruce: dict[str, Any]) -> list[dict[str, str]]:
    """Fuentes que no tienen sentido en este proyecto, con su motivo.

    No es lo mismo que una fuente ausente: aquí no falta nada, simplemente no
    había nada que esperar (``3.2-DOCUMENTOS/`` sin ingesta previa).

    Args:
        cruce (dict): Resultado de :func:`cruzar_fuentes`.

    Returns:
        List[Dict[str, str]]: ``nombre`` y ``motivo`` de cada fuente no aplicable.
    """
    return [
        {"nombre": f["nombre"], "motivo": f.get("motivo", "")}
        for f in cruce.get("fuentes", [])
        if not f.get("aplica", True)
    ]


def fuentes_ausentes(cruce: dict[str, Any]) -> list[str]:
    """Nombres de las fuentes que no existen en el vault.

    Args:
        cruce (dict): Resultado de :func:`cruzar_fuentes`.

    Returns:
        List[str]: Nombres legibles de las fuentes ausentes.
    """
    return [
        f["nombre"]
        for f in cruce.get("fuentes", [])
        if not f.get("presente") and f.get("aplica", True)
    ]

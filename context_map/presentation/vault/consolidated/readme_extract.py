"""Extracción del propósito del proyecto desde ``README.md``.

Dos niveles de extracción:
- ``_extract_project_purpose``: solo el primer párrafo (uso ligero).
- ``_extract_proposito_biblia``: tagline + secciones de identidad completas
  (usado por el brief y PROPOSITO-BIBLIA).
"""

from __future__ import annotations

import logging
import os
import re

logger = logging.getLogger(__name__)


# Encabezados ``## `` del README que NO son identidad del proyecto: cortan la
# extracción de PROPOSITO-BIBLIA (fix 2026-08-11 tras el piloto en
# Bot_AX_Contable, donde la primera sección era "## 🚀 Requisitos").
SECCIONES_NO_IDENTIDAD: set[str] = {
    "instalación", "instalacion", "licencia", "contribuir",
    "comparativa", "lista completa de comandos", "comandos",
    "referencias", "changelog", "roadmap",
    "requisitos", "requerimientos", "requirements", "dependencias",
    "prerequisitos", "pre-requisitos", "configuración inicial",
    "configuracion inicial", "uso", "uso rápido", "uso rapido",
    "instrucciones", "instalación y uso", "instalacion y uso",
    "puesta en marcha", "quickstart", "inicio rápido", "inicio rapido",
    "ejecución", "ejecucion", "cómo usar", "como usar",
    "cómo se usa", "como se usa",
}


def _es_linea_ignorable(stripped: str) -> bool:
    """True si la línea no aporta contenido al propósito (badge, TOC, HTML).

    Args:
        stripped (str): Línea sin espacios alrededor.

    Returns:
        bool: True si debe descartarse sin afectar el párrafo en curso.
    """
    return (
        stripped.startswith("[![")
        or stripped.startswith("- [")
        or stripped.startswith("* [")
        or stripped.startswith("<!--")
    )


def _es_linea_separadora(stripped: str) -> bool:
    """True si la línea es un separador HR que cierra el párrafo en curso.

    Args:
        stripped (str): Línea sin espacios alrededor.

    Returns:
        bool: True si es un separador horizontal (---, ___, ***).
    """
    return (
        stripped.startswith("---")
        or stripped.startswith("___")
        or stripped.startswith("***")
    )


def _cerrar_parrafo(paragraphs: list[str], current_para: list[str]) -> list[str]:
    """Cierra el párrafo en curso si tiene contenido, devolviendo un párrafo limpio.

    Args:
        paragraphs (list[str]): Acumulador de párrafos completados.
        current_para (list[str]): Líneas del párrafo en curso.

    Returns:
        list[str]: Párrafo actual vaciado tras archivarlo si correspondía.
    """
    if current_para:
        paragraphs.append(" ".join(current_para))
    return []


def _agrupar_parrafos(lines: list[str], start_idx: int) -> list[str]:
    """Agrupa las líneas posteriores a ``start_idx`` en párrafos de texto plano.

    Separa párrafos por líneas vacías y separadores HR; corta en el primer
    encabezado (``#``) y descarta badges, TOC y HTML. Conserva el comportamiento
    histórico de ``_extract_project_purpose``: el separador cierra el párrafo
    actual y las líneas ruidosas se descartan sin romperlo.

    Args:
        lines (list[str]): Líneas completas del README.
        start_idx (int): Índice desde el que agrupar (tras el título).

    Returns:
        list[str]: Párrafos de texto plano en orden de aparición.
    """
    paragraphs: list[str] = []
    current_para: list[str] = []

    for line in lines[start_idx:]:
        stripped = line.strip()

        if not stripped:
            current_para = _cerrar_parrafo(paragraphs, current_para)
            continue

        if _es_linea_separadora(stripped):
            current_para = _cerrar_parrafo(paragraphs, current_para)
            continue  # el separador cierra el párrafo; nunca forma parte de él

        if _es_linea_ignorable(stripped):
            continue  # badges, TOC y HTML: se descartan sin tocar el párrafo

        if stripped.startswith("#"):
            _cerrar_parrafo(paragraphs, current_para)
            break

        current_para.append(stripped)

    _cerrar_parrafo(paragraphs, current_para)

    return paragraphs


def _extract_project_purpose(cwd: str) -> str:
    """Extrae el propósito del proyecto desde README.md si existe.

    Busca README.md en cwd, extrae el primer párrafo después del título,
    saltando badges, TOC y líneas vacías.

    Returns:
        String con el párrafo extraído, o string vacío si no existe.
    """
    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""

    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("#!"):
            title_idx = i
            break

    if title_idx is None:
        return ""

    parrafos = _agrupar_parrafos(lines, title_idx + 1)
    return parrafos[0] if parrafos else ""


def _es_linea_ruido_markdown(stripped: str) -> bool:
    """True si la línea es ruido estructural de Markdown (tabla, TOC, bloque de código).

    Args:
        stripped (str): Línea sin espacios alrededor.

    Returns:
        bool: True si debe descartarse sin afectar el párrafo en curso.
    """
    return (
        stripped.startswith("|")
        or stripped.startswith("- [")
        or stripped.startswith("* [")
        or stripped.startswith("```")
    )


def _limpiar_markdown_linea(linea: str) -> str:
    """Limpia el formato Markdown de una línea: imágenes, enlaces y negritas.

    Args:
        linea (str): Línea cruda del README.

    Returns:
        str: Texto limpio sin imágenes, enlaces colapsados a su texto y sin ``**``.
    """
    texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", linea)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    return texto.replace("**", "").strip()


def _es_linea_separadora_biblia(stripped: str) -> bool:
    """True si la línea es un separador HR reconocido por PROPOSITO-BIBLIA.

    Históricamente la biblia descartaba solo ``---``, ``___`` y comentarios
    ``<!--`` (a diferencia del extractor de propósito, que también cerraba
    párrafos con ``***``). Se mantiene el mismo subconjunto para no alterar
    la extracción.

    Args:
        stripped (str): Línea sin espacios alrededor.

    Returns:
        bool: True si debe descartarse como separador.
    """
    return stripped.startswith("---") or stripped.startswith("___")


def _clasificar_linea_biblia(stripped: str) -> str:
    """Clasifica una línea del README para la extracción de PROPOSITO-BIBLIA.

    Devuelve un token de acción para que el bucle principal de
    ``_extract_proposito_biblia`` no acumule puntos de decisión por línea:
    'vacia', 'badge', 'comentario', 'separador', 'ruido', 'titulo'
    (encabezado ``# `` principal), 'seccion' (``## ``) o 'contenido' (texto).

    Args:
        stripped (str): Línea sin espacios alrededor.

    Returns:
        str: Token de clasificación.
    """
    if not stripped:
        return "vacia"
    if stripped.startswith("[!["):
        return "badge"
    if stripped.startswith("<!--"):
        return "comentario"
    if stripped.startswith("## "):
        return "seccion"
    if stripped.startswith("# "):
        return "titulo"
    if _es_linea_separadora_biblia(stripped):
        return "separador"
    if _es_linea_ruido_markdown(stripped):
        return "ruido"
    return "contenido"


def _capturar_seccion_biblia(
    titulo: str,
    en_seccion_contenido: bool,
    secciones_capturadas: int,
    max_secciones: int,
) -> tuple[str, int]:
    """Procesa un encabezado ``## `` y decide la acción de corte.

    Comportamiento histórico (preservado del refactor):
    - Sección NO identidad corta SIEMPRE (incluso si es la primera).
    - La primera sección de contenido nunca corta por ``max_secciones``.
    - Desde la segunda sección, al alcanzar ``max_secciones`` se corta.

    Args:
        titulo (str): Título de la sección normalizado (sin emojis).
        en_seccion_contenido (bool): Si ya se capturó alguna sección de identidad.
        secciones_capturadas (int): Secciones de contenido capturadas hasta ahora.
        max_secciones (int): Máximo de secciones a capturar.

    Returns:
        tuple[str, int]: (acción 'break' | 'ok', secciones_capturadas actualizada).
    """
    seccion_norm = re.sub(r"[^\w\sáéíóñü-]", "", titulo).strip()
    if seccion_norm in SECCIONES_NO_IDENTIDAD:
        return "break", secciones_capturadas  # sección operativa: cortar (fix 2026-08-11)
    nuevas = secciones_capturadas + 1
    if en_seccion_contenido and nuevas >= max_secciones:
        return "break", nuevas
    return "ok", nuevas


def _asignar_tagline(tagline: str, texto: str) -> str:
    """Asigna el tagline si aún no existe y el texto cabe en el límite histórico.

    Args:
        tagline (str): Tagline actual (posiblemente vacío).
        texto (str): Línea de texto candidata a tagline.

    Returns:
        str: El tagline nuevo si correspondía, o el previo.
    """
    if not tagline and len(texto) < 400:
        return texto
    return tagline


def _procesar_linea_contenido(
    line: str,
    en_seccion_contenido: bool,
    tagline: str,
    parrafos: list[str],
    max_caracteres: int,
) -> tuple[bool, str, list[str]]:
    """Procesa una línea de contenido: tagline o párrafo de identidad.

    Args:
        line (str): Línea cruda del README.
        en_seccion_contenido (bool): Si ya se capturó alguna sección de identidad.
        tagline (str): Tagline actual (posiblemente vacío).
        parrafos (list[str]): Párrafos acumulados.
        max_caracteres (int): Límite de caracteres del resultado.

    Returns:
        tuple[bool, str, list[str]]: (cortar, tagline actualizado, parrafos).
    """
    texto = _limpiar_markdown_linea(line)
    if not texto:
        return False, tagline, parrafos
    if not en_seccion_contenido:
        # antes de la primera sección: el tagline (frase de identidad;
        # límite generoso para frases reales de ~150-300 caracteres)
        return False, _asignar_tagline(tagline, texto), parrafos
    if sum(len(p) + len(texto) for p in parrafos) > max_caracteres:
        return True, tagline, parrafos  # límite: no sumar el párrafo que desborda
    return False, tagline, parrafos + [texto]


def _extract_proposito_biblia(cwd: str, max_secciones: int = 3, max_caracteres: int = 2600) -> str:
    """Extrae el PROPOSITO-BIBLIA del README: tagline + secciones de identidad.

    A diferencia de ``_extract_project_purpose`` (solo el primer párrafo),
    esta función recoge la identidad completa: el tagline (línea en negrita
    tras el título) y los párrafos de las primeras secciones de contenido
    (``¿Qué es?``, metodología, etc.), que contienen el alma del proyecto.

    Args:
        cwd (str): Directorio raíz del proyecto.
        max_secciones (int): Máximo de secciones ``## `` a capturar.
        max_caracteres (int): Límite de caracteres del resultado.

    Returns:
        str: Párrafos de identidad separados por doble salto de línea,
        o string vacío si no se pudo extraer.
    """
    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""
    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    tagline = ""
    parrafos: list[str] = []
    secciones_capturadas = 0
    en_seccion_contenido = False

    for line in lines:
        tipo = _clasificar_linea_biblia(line.strip())

        if tipo == "seccion":
            accion, secciones_capturadas = _capturar_seccion_biblia(
                line.strip().lstrip("#").strip().lower(),
                en_seccion_contenido,
                secciones_capturadas,
                max_secciones,
            )
            if accion == "break":
                break
            en_seccion_contenido = True
            continue

        if tipo == "contenido":
            cortar, tagline, parrafos = _procesar_linea_contenido(
                line, en_seccion_contenido, tagline, parrafos, max_caracteres
            )
            if cortar:
                break
            continue

        # vacia, badge, comentario, separador, ruido, titulo: se ignoran
        continue

    partes = [p for p in [tagline] + parrafos if p]
    resultado = "\n\n".join(partes)
    return resultado[:max_caracteres]

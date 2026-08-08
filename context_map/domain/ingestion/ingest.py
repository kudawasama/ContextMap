"""Ingesta de documentos externos para el mapa de contexto.

Convierte documentos brutos (Markdown, TXT, PDF) en nodos de tipo
``DOCUMENTO`` con síntesis del contenido y citas textuales referenciadas,
de modo que el conocimiento externo quede a disposición del grafo sin
re-leer el original en cada interacción.
"""

from __future__ import annotations

import logging
import os
import re

from context_map.core.models import Node

logger = logging.getLogger(__name__)

# ============================================================
# Constantes de síntesis extractiva
# ============================================================

MAX_CARACTERES_SINTESIS: int = 1200
MAX_CITAS: int = 10
STOPWORDS_ES: frozenset[str] = frozenset({
    "de", "la", "el", "que", "y", "en", "a", "los", "las", "del", "se", "por",
    "con", "para", "una", "un", "es", "lo", "como", "más", "pero", "sus",
    "le", "ya", "o", "este", "si", "me", "porque", "esta", "entre", "cuando",
    "muy", "sin", "sobre", "también", "fue", "hay", "todos", "puede", "ser",
    "su", "al", "ha", "desde", "the", "and", "of", "to", "in", "is", "for",
    "on", "with", "at", "by", "are", "that", "this", "it", "as", "was",
})


def _slugificar_documento(texto: str) -> str:
    """Convierte texto en slug seguro para nombres de archivo y nodos."""
    slug = texto.lower().strip()
    slug = re.sub(r"[áàäâ]", "a", slug)
    slug = re.sub(r"[éèëê]", "e", slug)
    slug = re.sub(r"[íìïî]", "i", slug)
    slug = re.sub(r"[óòöô]", "o", slug)
    slug = re.sub(r"[úùüû]", "u", slug)
    slug = re.sub(r"[ñ]", "n", slug)
    slug = re.sub(r"[^a-z0-9\s\-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-")[:60] or "documento"


def _limpiar_texto(texto: str) -> str:
    """Normaliza el texto extraído: colapsa espacios y saltos múltiples."""
    texto = texto.replace("\x00", "")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def extraer_texto(ruta: str) -> tuple[str, str]:
    """Extrae el texto plano de un documento (MD/TXT/PDF).

    Args:
        ruta (str): Ruta al archivo.

    Returns:
        tuple[str, str]: (texto_extraído, tipo_detectado) donde tipo es
        'markdown', 'texto' o 'pdf'.

    Raises:
        FileNotFoundError: Si la ruta no existe.
        ValueError: Si la extensión no es soportada o el PDF no tiene texto.
    """
    if not os.path.isfile(ruta):
        raise FileNotFoundError(f"Archivo no encontrado: {ruta}")

    ext = os.path.splitext(ruta)[1].lower()

    if ext in (".md", ".markdown"):
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return _limpiar_texto(f.read()), "markdown"

    if ext in (".txt", ".text"):
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return _limpiar_texto(f.read()), "texto"

    if ext == ".pdf":
        return _extraer_pdf(ruta), "pdf"

    raise ValueError(
        f"Extensión no soportada '{ext}'. Usa .md, .txt o .pdf (instala 'pymupdf' para PDF)."
    )


def _extraer_pdf(ruta: str) -> str:
    """Extrae texto de un PDF usando PyMuPDF (fitz).

    Raises:
        ValueError: Si pymupdf no está instalado o el PDF no tiene texto.
    """
    try:
        # PyMuPDF moderno (>=1.24): import pymupdf; legado: import fitz
        try:
            import pymupdf  # type: ignore[import-not-found]
        except ImportError:
            import fitz as pymupdf  # type: ignore[no-redef]
    except ImportError as err:
        raise ValueError(
            "Para ingerir PDFs instala PyMuPDF: `uv pip install pymupdf`"
        ) from err

    try:
        doc = pymupdf.open(ruta)
        paginas: list[str] = []
        for pagina in doc:
            texto = pagina.get_text()
            if texto.strip():
                paginas.append(f"## [p.{pagina.number + 1}]\n{texto.strip()}")
        doc.close()
    except Exception as err:
        raise ValueError(f"No se pudo leer el PDF {ruta}: {err}") from err

    texto_total = _limpiar_texto("\n\n".join(paginas))
    if not texto_total:
        raise ValueError(f"El PDF {ruta} no contiene texto extraíble (¿es escaneado?).")
    return texto_total


def _oraciones(texto: str) -> list[str]:
    """Divide texto en oraciones no vacías."""
    bruto = re.split(r"(?<=[.!?])\s+|\n+", texto)
    return [o.strip() for o in bruto if len(o.strip()) > 40]


def _puntuar_oracion(oracion: str, frecuencia: dict[str, int]) -> float:
    """Puntúa una oración según la frecuencia de sus términos relevantes."""
    palabras = re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}", oracion.lower())
    if not palabras:
        return 0.0
    relevantes = [p for p in palabras if p not in STOPWORDS_ES]
    if not relevantes:
        return 0.0
    return sum(frecuencia.get(p, 0) for p in relevantes) / len(relevantes)


def sintetizar(texto: str, max_caracteres: int = MAX_CARACTERES_SINTESIS) -> str:
    """Genera una síntesis extractiva del documento.

    Selecciona las oraciones con mayor densidad de términos relevantes
    (frecuencia de palabras significativas), manteniendo un límite de
    caracteres. Es un resumen determinista sin LLM.

    Args:
        texto (str): Texto plano del documento.
        max_caracteres (int): Límite de caracteres de la síntesis.

    Returns:
        str: Síntesis del contenido.
    """
    oraciones = _oraciones(texto)
    if not oraciones:
        return texto[:max_caracteres].strip() or "_(Documento sin texto suficiente)_"

    palabras = re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{3,}", texto.lower())
    frecuencia: dict[str, int] = {}
    for p in palabras:
        if p not in STOPWORDS_ES:
            frecuencia[p] = frecuencia.get(p, 0) + 1

    puntuadas = sorted(
        ((_puntuar_oracion(o, frecuencia), o) for o in oraciones),
        key=lambda x: x[0],
        reverse=True,
    )
    # Mantener las mejores oraciones preservando su orden original
    mejores = [o for _, o in puntuadas if _ > 0][:6]

    sintesis = ""
    for oracion in mejores:
        if len(sintesis) + len(oracion) + 2 > max_caracteres:
            break
        sintesis += (" " if sintesis else "") + oracion

    if len(sintesis) < 80:
        sintesis = " ".join(oraciones[:2])[:max_caracteres]

    return sintesis.strip() or "_(Documento sin texto suficiente)_"


def extraer_citas(texto: str, max_citas: int = MAX_CITAS) -> list[str]:
    """Extrae citas representativas con referencia (página si es PDF).

    Para PDFs el texto ya incluye marcas ``[p.N]``; las citas conservan esa
    referencia. Para MD/TXT se toman las primeras oraciones significativas.

    Args:
        texto (str): Texto plano del documento.
        max_citas (int): Máximo de citas a extraer.

    Returns:
        list[str]: Citas con referencia.
    """
    oraciones = _oraciones(texto)
    citas: list[str] = []

    for oracion in oraciones:
        if len(citas) >= max_citas:
            break
        # Referencia de página: la marca [p.N] precede al texto
        pagina = ""
        if oracion.startswith("## [p."):
            m = re.match(r"## \[p\.(\d+)\]", oracion)
            if m:
                pagina = f"p.{m.group(1)}"
                oracion = oracion.replace(m.group(0), "").strip()

        if len(oracion) < 50:
            continue
        if len(oracion) > 300:
            oracion = oracion[:297].rsplit(" ", 1)[0] + "..."
        ref = f"[{pagina}] " if pagina else ""
        citas.append(f"{ref}{oracion}")

    return citas


def detectar_concepto(texto: str) -> str:
    """Detecta el concepto/dominio dominante por frecuencia de términos.

    Devuelve el término significativo más frecuente en mayúsculas como
    identificador de concepto (p. ej. 'INVERSION', 'FINANZAS').

    Args:
        texto (str): Texto plano del documento.

    Returns:
        str: ID de concepto detectado.
    """
    palabras = re.findall(r"[a-zA-ZáéíóúñüÁÉÍÓÚÑÜ]{4,}", texto.lower())
    frecuencia: dict[str, int] = {}
    for p in palabras:
        if p not in STOPWORDS_ES:
            frecuencia[p] = frecuencia.get(p, 0) + 1

    if not frecuencia:
        return "GENERAL"

    top = sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:3]
    # Tomar el término con más frecuencia y longitud >= 5 (más específico)
    for palabra, _conteo in top:
        if len(palabra) >= 5:
            return palabra.upper()
    return top[0][0].upper()


def crear_nodo_documento(
    ruta: str,
    texto: str,
    project_name: str,
    status: str = "vigente",
) -> Node:
    """Crea un nodo de tipo DOCUMENTO a partir de un texto extraído.

    Args:
        ruta (str): Ruta original del documento.
        texto (str): Texto plano del documento.
        project_name (str): Nombre del proyecto.
        status (str): Estado del nodo (default 'vigente').

    Returns:
        Node: Nodo DOCUMENTO con síntesis y citas.
    """
    nombre = os.path.basename(ruta)
    slug = _slugificar_documento(os.path.splitext(nombre)[0])
    concepto = detectar_concepto(texto)

    sintesis = sintetizar(texto)
    citas = extraer_citas(texto)

    node = Node(
        id=f"DOC-{slug.upper()[:40]}",
        type="DOCUMENTO",
        title=os.path.splitext(nombre)[0],
        summary=sintesis,
        status=status,
        tags=["context-map", "documento", concepto.lower()],
        source="ingest",
        evidence=citas,
        concept=concepto,
        classification="docs",
    )
    # project se setea al persistir vía build; el nodo solo lleva datos puros
    node.concept = concepto
    return node

"""Mundo CONOCIMIENTO: LLM Wiki (patrón Karpathy).

Páginas de resumen, entidades/conceptos y bitácora (entry log) dentro de
``90-CONOCIMIENTO/05-WIKI``. Operaciones deterministas que el AGENTE (o el
usuario) usa para construir y mantener la wiki del curso de Obsidian:

- ``ingresar``   → crea la página de resumen de una fuente, actualiza el índice
  de resúmenes, el entry log y las páginas de entidades/conceptos.
- ``consultar``  → ranking por solape de tokens (BM25) + embeddings opcionales;
  devuelve páginas CON CITAS (ruta del wikilink) para que el agente sintetice
  con trazabilidad.
- ``lint``       → salud de la wiki: enlaces rotos, páginas huérfanas,
  conceptos sin página e ítems del entry log apuntando a nada.
"""

from __future__ import annotations

import contextlib
import math
import os
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from context_map.domain.knowledge import embeddings
from context_map.domain.knowledge.indices import (
    agregar_a_indice,
    backlink_relativo,
    leer_titulo,
    ruta_libre,
    sanear,
    slug,
)

NS_CONOCIMIENTO = "90-CONOCIMIENTO"
WIKI = "05-WIKI"
RESUMENES = "resumenes"
ENTIDADES = "entidades"
ENTRY_LOG = "entry-log.md"
MOC = "MOC.md"

# Anclas de los índices generados en F1 (esqueleto).
_ANCLA_RESUMENES = "## 📄 Resúmenes"
_ANCLA_ENTIDADES = "## 🔖 Páginas"

@dataclass
class ReporteLint:
    """Resultado del lint de la wiki.

    Attributes:
        ok (bool): True si no hay errores.
        errores (list[str]): Problemas que rompen la wiki (enlaces rotos, etc.).
        avisos (list[str]): Cuestiones menores (huérfanas, pendientes).
    """

    ok: bool
    errores: list[str]
    avisos: list[str]


def _sin_acentos(texto: str) -> str:
    """Quita los acentos de un texto ("generación" → "generacion").

    Mejora el matching: una consulta escrita sin tildes encuentra la página.

    Args:
        texto (str): Texto de entrada.

    Returns:
        str: Texto sin marcas diacríticas.
    """
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


_PATRON_TOKEN = re.compile(r"[a-z0-9]{3,}")

# Palabras vacías para el ranking de consulta (normalizadas sin acentos).
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en",
    "y", "o", "a", "para", "por", "con", "que", "se", "su", "al", "lo", "como",
    "es", "son", "mas", "pero", "sobre", "entre", "esto", "esta", "the",
    "of", "and", "to", "in", "on", "for",
}


def ruta_wiki(vault_dir: str) -> str:
    """Ruta de ``90-CONOCIMIENTO/05-WIKI`` dentro del vault.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        str: Ruta de la carpeta de la wiki.
    """
    return os.path.join(vault_dir, NS_CONOCIMIENTO, WIKI)


def ruta_resumenes(vault_dir: str) -> str:
    """Ruta de la carpeta de resúmenes de fuentes."""
    return os.path.join(ruta_wiki(vault_dir), RESUMENES)


def ruta_entidades(vault_dir: str) -> str:
    """Ruta de la carpeta de entidades/conceptos."""
    return os.path.join(ruta_wiki(vault_dir), ENTIDADES)


def _tokens_lista(texto: str) -> list[str]:
    """Tokens relevantes con repetición (para TF): minúsculos, sin acentos ni stopwords."""
    norm = _PATRON_TOKEN.findall(_sin_acentos((texto or "").lower()))
    return [t for t in norm if t not in _STOPWORDS]


def _tokens(texto: str) -> set[str]:
    """Conjunto de tokens relevantes (sin stopwords) de un texto."""
    return set(_tokens_lista(texto))


def _padre_wiki(seccion: str) -> str:
    """Ruta del wikilink padre para el pie de una página de la wiki."""
    return f"{NS_CONOCIMIENTO}/{WIKI}/{seccion}/{seccion}"


def _contenido_resumen(titulo: str, contenido: str, fuente: str,
                       entidades: list[str]) -> str:
    """Construye el Markdown de una página de resumen con sus entidades."""
    fecha = datetime.now().isoformat(timespec="seconds")
    partes = [
        "---",
        "type: resumen",
        "namespace: knowledge",
        "preserve: true",
        f"created: {fecha}",
        f'title: "{sanear(titulo)}"',
        f'source: "{sanear(fuente)}"',
        "status: activo",
        "tags: [knowledge, wiki, resumen]",
        "---",
        "",
        f"# {titulo}",
        "",
        contenido.strip(),
    ]
    if entidades:
        partes += ["", "## 🔖 Entidades relacionadas", ""]
        for ent in entidades:
            link = f"{NS_CONOCIMIENTO}/{WIKI}/{ENTIDADES}/{slug(ent)}"
            partes.append(f"- [[{link}|{ent}]]")
    partes += ["", "---", f"[[{_padre_wiki(RESUMENES)}|⬅ Volver a Resúmenes]]", ""]
    return "\n".join(partes)


def _contenido_entidad(entidad: str, resumen_link: str, resumen_titulo: str) -> str:
    """Construye el Markdown de la página de una entidad/concepto."""
    fecha = datetime.now().isoformat(timespec="seconds")
    return (
        "---\n"
        "type: entidad\n"
        "namespace: knowledge\n"
        "preserve: true\n"
        f"created: {fecha}\n"
        f'title: "{sanear(entidad)}"\n'
        "status: activo\n"
        "tags: [knowledge, wiki, entidad]\n"
        "---\n\n"
        f"# {entidad}\n\n"
        "> Definición pendiente — el agente la redacta con el contexto de la wiki.\n\n"
        "## 📄 Páginas relacionadas\n\n"
        f"- [[{resumen_link}|{resumen_titulo}]]\n\n"
        "---\n"
        f"[[{_padre_wiki(ENTIDADES)}|⬅ Volver a Entidades]]\n"
    )


def _append_entry_log(entry_log: str, ruta_resumen_abs: str, vault_dir: str,
                      titulo: str, fecha: str) -> None:
    """Agrega una fila al entry log apuntando a la página de resumen creada."""
    if not os.path.exists(entry_log):
        return
    link = backlink_relativo(vault_dir, ruta_resumen_abs)
    with open(entry_log, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    # Quitar la fila placeholder (| — | — | — |) la primera vez que se registra.
    lineas = [ln for ln in lineas if not set("—").issubset(set(ln)) or ln.count("|") != 3]
    fila = f"| {fecha} | Ingest | [[{link}|{titulo}]] |"
    if not any(f"[[{link}" in ln for ln in lineas):
        # Insertar después de la línea separadora |---|---|---|
        idx = next((i for i, ln in enumerate(lineas) if set(ln.strip()) == set("|:- ")), None)
        if idx is None:
            lineas.append(fila)
        else:
            lineas.insert(idx + 1, fila)
    with open(entry_log, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def ingresar(vault_dir: str, titulo: str, contenido: str, fuente: str = "",
             entidades: str | list[str] | None = None) -> dict[str, str]:
    """Ingesta una fuente a la wiki: página de resumen + índices + entry log + entidades.

    Args:
        vault_dir (str): Directorio raíz del vault.
        titulo (str): Título de la página de resumen.
        contenido (str): Cuerpo del resumen (lo redacta el agente).
        fuente (str): Origen (URL, video, PDF, conversación…).
        entidades (str | list[str] | None): Conceptos a crear/actualizar.
            Acepta "a, b" o una lista.

    Returns:
        dict[str, str]: Detalle con ``ruta`` (resumen), ``titulo``, ``fuente``
        y ``entidades`` (lista de las creadas/actualizadas).
    """
    if not (titulo or "").strip() and not (contenido or "").strip():
        raise ValueError("La ingesta necesita un título o contenido.")

    titulo_final = (titulo or contenido).strip().splitlines()[0][:120] or "Resumen"
    fecha = datetime.now().date().isoformat()

    lista_entidades: list[str] = []
    if isinstance(entidades, str):
        lista_entidades = [e.strip() for e in entidades.split(",") if e.strip()]
    elif entidades:
        lista_entidades = [str(e).strip() for e in entidades if str(e).strip()]

    carpeta_res = ruta_resumenes(vault_dir)
    os.makedirs(carpeta_res, exist_ok=True)
    ruta_res = ruta_libre(carpeta_res, f"{fecha}-{slug(titulo_final)}")
    with open(ruta_res, "w", encoding="utf-8") as f:
        f.write(_contenido_resumen(titulo_final, contenido, fuente, lista_entidades))

    idx_res = os.path.join(carpeta_res, f"{RESUMENES}.md")
    agregar_a_indice(idx_res, ruta_res, vault_dir, titulo_final, _ANCLA_RESUMENES)

    _append_entry_log(
        os.path.join(ruta_wiki(vault_dir), ENTRY_LOG), ruta_res, vault_dir, titulo_final, fecha,
    )

    # Entidades: crear/actualizar página + índice, y enlazarlas al resumen.
    # La ruta de una entidad es CANÓNICA (``<slug>.md``): se hace upsert, nunca
    # se duplica con sufijo -2 (a diferencia de los resúmenes, que son únicos).
    resumen_link = backlink_relativo(vault_dir, ruta_res)
    for ent in lista_entidades:
        carpeta_ent = ruta_entidades(vault_dir)
        os.makedirs(carpeta_ent, exist_ok=True)
        ruta_ent = os.path.join(carpeta_ent, f"{slug(ent)}.md")
        if not os.path.exists(ruta_ent):
            with open(ruta_ent, "w", encoding="utf-8") as f:
                f.write(_contenido_entidad(ent, resumen_link, titulo_final))
            agregar_a_indice(
                os.path.join(carpeta_ent, f"{ENTIDADES}.md"), ruta_ent, vault_dir, ent, _ANCLA_ENTIDADES,
            )
        # Si la entidad ya existe, asegurar el enlace al resumen en su página.
        else:
            with open(ruta_ent, encoding="utf-8") as f:
                ent_txt = f.read()
            if f"[[{resumen_link}" not in ent_txt:
                ent_txt = ent_txt.replace(
                    "## 📄 Páginas relacionadas\n",
                    f"## 📄 Páginas relacionadas\n- [[{resumen_link}|{titulo_final}]]\n",
                )
                with open(ruta_ent, "w", encoding="utf-8") as f:
                    f.write(ent_txt)

    # El MOC se regenera para que el grafo de conceptos quede al día.
    # Nunca debe romper la ingesta.
    with contextlib.suppress(Exception):
        generar_moc(vault_dir)

    return {
        "ruta": ruta_res,
        "titulo": titulo_final,
        "fuente": fuente,
        "entidades": ", ".join(lista_entidades),
    }


def _paginas(vault_dir: str) -> list[tuple[str, str]]:
    """Devuelve (ruta_abs, titulo) de todas las páginas de resúmenes y entidades."""
    paginas: list[tuple[str, str]] = []
    for carpeta in (ruta_resumenes(vault_dir), ruta_entidades(vault_dir)):
        if not os.path.isdir(carpeta):
            continue
        nombre_idx = os.path.basename(carpeta) + ".md"
        for nombre in os.listdir(carpeta):
            if not nombre.endswith(".md") or nombre == nombre_idx:
                continue
            ruta = os.path.join(carpeta, nombre)
            paginas.append((ruta, leer_titulo(ruta)))
    return paginas


# Negaciones para el lint de contradicciones.
_NEGACIONES = re.compile(
    r"\b(no|nunca|jamás|jamas|sin|tampoco|nada|ningún|ningun|ninguna)\b",
    re.IGNORECASE,
)


def _frases(texto: str) -> list[str]:
    """Divide un texto en frases útiles (sin frontmatter ni wikilinks).

    Args:
        texto (str): Contenido Markdown de una página.

    Returns:
        list[str]: Frases de al menos 30 caracteres.
    """
    plano = re.sub(r"^---\n.*?\n---\n", "", texto, flags=re.DOTALL)
    plano = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", plano)
    partes = re.split(r"(?<=[.!?])\s+|\n+", plano)
    return [p.strip() for p in partes if len(p.strip()) >= 30]


def _mejores_frases(ruta: str, q_tokens: set[str], max_frases: int = 2) -> list[str]:
    """Frases de una página con mayor solape de tokens con la consulta.

    Args:
        ruta (str): Ruta de la página.
        q_tokens (set[str]): Tokens de la consulta.
        max_frases (int): Máximo de frases a devolver.

    Returns:
        list[str]: Frases ordenadas por afinidad (solo con solape > 0).
    """
    with open(ruta, encoding="utf-8") as f:
        texto = f.read()
    con_score = [(len(q_tokens & _tokens(fr)), fr) for fr in _frases(texto)]
    con_score = [(s, fr) for s, fr in con_score if s > 0]
    con_score.sort(key=lambda x: x[0], reverse=True)
    return [fr for _s, fr in con_score[:max_frases]]


def sintetizar(vault_dir: str, pregunta: str, limite: int = 5) -> dict[str, Any]:
    """Sintetiza una respuesta **extractiva local** con citas a la wiki.

    No usa red ni LLM: elige las frases más afines de las páginas rankeadas y las
    encadena citando cada fuente como ``[n]``. Determinista y trazable.

    Args:
        vault_dir (str): Directorio raíz del vault.
        pregunta (str): Consulta del usuario/agente.
        limite (int): Máximo de páginas fuente (default 5).

    Returns:
        dict: ``pregunta``, ``respuesta`` (texto con marcadores ``[n]``) y
        ``fuentes`` (lista de {titulo, cita, excerpt}).
    """
    q_tokens = _tokens(pregunta)
    resultados = consultar(vault_dir, pregunta, limite=limite)
    if not resultados:
        return {"pregunta": pregunta, "respuesta": "", "fuentes": []}

    bloques: list[str] = []
    fuentes: list[dict[str, str]] = []
    for i, r in enumerate(resultados, 1):
        frases = _mejores_frases(r["ruta"], q_tokens)
        if frases:
            bloques.append(" ".join(frases) + f" [{i}]")
        fuentes.append({"titulo": r["titulo"], "cita": r["cita"], "excerpt": r["excerpt"]})
    return {
        "pregunta": pregunta,
        "respuesta": "\n\n".join(bloques),
        "fuentes": fuentes,
    }


def listar_paginas(vault_dir: str) -> list[dict[str, str]]:
    """Lista las páginas de la wiki (resúmenes y entidades) con su wikilink.

    Pensada para el brief de agentes: expone el Second Brain sin cargar el
    contenido completo de cada página.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        list[dict[str, str]]: Items con ``titulo``, ``tipo`` (``resumen`` |
        ``entidad``), ``ruta`` absoluta y ``cita`` (wikilink relativo al
        vault). Los resúmenes van primero para priorizarse al truncar.
    """
    resultado: list[dict[str, str]] = []
    for carpeta, tipo in (
        (ruta_resumenes(vault_dir), "resumen"),
        (ruta_entidades(vault_dir), "entidad"),
    ):
        if not os.path.isdir(carpeta):
            continue
        nombre_idx = os.path.basename(carpeta) + ".md"
        for nombre in sorted(os.listdir(carpeta)):
            if not nombre.endswith(".md") or nombre == nombre_idx:
                continue
            ruta = os.path.join(carpeta, nombre)
            titulo = leer_titulo(ruta)
            cita = backlink_relativo(vault_dir, ruta)
            resultado.append({
                "titulo": titulo,
                "tipo": tipo,
                "ruta": ruta,
                "cita": f"[[{cita}|{titulo}]]",
            })
    return resultado


def consultar(vault_dir: str, pregunta: str, limite: int = 5) -> list[dict[str, str]]:
    """Busca páginas relevantes de la wiki y las devuelve con citas.

    Fusión de dos señales: **BM25** (solape de tokens, siempre disponible) y
    **embeddings** (similitud semántica, opcional; ver
    ``context_map.domain.knowledge.embeddings``). Sin ``sentence-transformers``
    el comportamiento es idéntico al BM25 puro.

    Args:
        vault_dir (str): Directorio raíz del vault.
        pregunta (str): Texto de la consulta.
        limite (int): Máximo de resultados (default 5).

    Returns:
        list[dict[str, str]]: Resultados con ``titulo``, ``ruta``, ``cita``
        (wikilink) y ``excerpt`` (fragmento del contenido).
    """
    q_tokens = _tokens(pregunta)

    # Señal semántica opcional. Es best-effort: si falta la librería o falla el
    # modelo, devuelve {} y el ranking se queda en BM25.
    semanticas: dict[str, float] = {}
    with contextlib.suppress(Exception):
        semanticas = embeddings.similitudes(vault_dir, pregunta)

    if not q_tokens and not semanticas:
        return []

    # Corpus con TF por documento (título + contenido).
    documentos: list[tuple[str, str, str, list[str]]] = []
    for ruta, titulo in _paginas(vault_dir):
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        documentos.append((ruta, titulo, contenido, _tokens_lista(titulo + " " + contenido)))
    if not documentos:
        return []

    n_docs = len(documentos)
    largo_medio = sum(len(d[3]) for d in documentos) / n_docs or 1.0
    frecuencia_doc: Counter[str] = Counter()
    for *_resto, toks in documentos:
        frecuencia_doc.update(set(toks))

    # BM25 (k1=1.5, b=0.75): pondera frecuencia, rareza del término y longitud.
    k1, b = 1.5, 0.75
    puntajes_bm25: dict[str, float] = {}
    for ruta, _titulo, _contenido, toks in documentos:
        tf = Counter(toks)
        largo = len(toks) or 1
        score = 0.0
        for termino in q_tokens:
            if termino not in tf:
                continue
            df = frecuencia_doc[termino]
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            score += idf * (tf[termino] * (k1 + 1)) / (
                tf[termino] + k1 * (1 - b + b * largo / largo_medio)
            )
        if score > 0:
            puntajes_bm25[ruta] = score

    # Fusión de señales: BM25 normalizado + peso × similitud semántica. Así una
    # paráfrasis sin solape léxico también puede recuperar su página.
    max_bm25 = max(puntajes_bm25.values(), default=0.0) or 1.0
    resultados: list[tuple[float, dict[str, str]]] = []
    for ruta, titulo, contenido, _toks in documentos:
        score = puntajes_bm25.get(ruta, 0.0) / max_bm25 + (
            embeddings.PESO_SEMANTICO * semanticas.get(ruta, 0.0)
        )
        if score <= 0:
            continue
        cuerpo = re.sub(r"^---\n.*?\n---\n", "", contenido, flags=re.DOTALL)
        excerpt = re.sub(r"\s+", " ", cuerpo).strip()[:220]
        cita = backlink_relativo(vault_dir, ruta)
        resultados.append((score, {
            "titulo": titulo,
            "ruta": ruta,
            "cita": f"[[{cita}|{titulo}]]",
            "excerpt": excerpt,
        }))
    resultados.sort(key=lambda x: x[0], reverse=True)
    return [r for _score, r in resultados[:limite]]


def _detectar_contradicciones(vault_dir: str) -> list[str]:
    """Detecta posibles contradicciones: misma frase afirmada y negada.

    Heurística conservadora: dos frases de páginas distintas cuya forma sin
    negaciones coincide, pero una lleva negación y la otra no.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        list[str]: Avisos de posibles contradicciones.
    """
    declaraciones: dict[str, list[tuple[str, bool]]] = {}
    for ruta, _t in _paginas(vault_dir):
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
        for frase in _frases(texto):
            base = re.sub(r"\s+", " ", _NEGACIONES.sub(" ", frase.lower())).strip(" .,;:")
            if len(_tokens(base)) < 4:
                continue
            negada = bool(_NEGACIONES.search(frase))
            declaraciones.setdefault(base, []).append(
                (os.path.basename(ruta), negada)
            )

    avisos: list[str] = []
    for base, items in declaraciones.items():
        archivos = {a for a, _n in items}
        if len(archivos) < 2 or len({n for _a, n in items}) < 2:
            continue
        avisos.append(
            "POSIBLE CONTRADICCIÓN entre "
            + " y ".join(sorted(archivos))
            + f": «{base[:80]}» aparece afirmada y negada."
        )
    return avisos


def _rutas_md(carpeta: str, indice: str) -> list[str]:
    """Rutas de las páginas .md de una carpeta, excluyendo su índice."""
    if not os.path.isdir(carpeta):
        return []
    return sorted(
        os.path.join(carpeta, n)
        for n in os.listdir(carpeta)
        if n.endswith(".md") and n != indice
    )


def _asegurar_enlace_moc(vault_dir: str) -> None:
    """Asegura (idempotente) el enlace al MOC desde el índice ``05-WIKI.md``."""
    index_path = os.path.join(ruta_wiki(vault_dir), f"{WIKI}.md")
    if not os.path.exists(index_path):
        return
    link = f"[[{NS_CONOCIMIENTO}/{WIKI}/MOC|🗺️ MOC — Mapa de contenido]]"
    with open(index_path, encoding="utf-8") as f:
        texto = f.read()
    if f"/{WIKI}/{MOC}" in texto:
        return
    texto = texto.replace(
        "## 📚 Subsecciones\n",
        f"## 📚 Subsecciones\n\n- {link}\n",
    )
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(texto)


def generar_moc(vault_dir: str) -> str:
    """Genera el MOC (mapa de contenido): cada concepto con sus fuentes.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        str: Ruta del archivo ``MOC.md`` generado.
    """
    ruta_moc = os.path.join(ruta_wiki(vault_dir), MOC)
    resumenes = _rutas_md(ruta_resumenes(vault_dir), f"{RESUMENES}.md")
    entidades = _rutas_md(ruta_entidades(vault_dir), f"{ENTIDADES}.md")

    bloques: list[str] = ["## 🔖 Conceptos", ""]
    if entidades:
        for ruta_ent in entidades:
            slug_ent = os.path.splitext(os.path.basename(ruta_ent))[0]
            bloques.append(f"### 🔖 {leer_titulo(ruta_ent)}")
            relacionados = []
            for ruta_res in resumenes:
                with open(ruta_res, encoding="utf-8") as f:
                    if f"/{ENTIDADES}/{slug_ent}" in f.read():
                        relacionados.append(
                            f"[[{backlink_relativo(vault_dir, ruta_res)}|"
                            f"{leer_titulo(ruta_res)}]]"
                        )
            if relacionados:
                bloques += [f"- {r}" for r in relacionados]
            else:
                bloques.append("- _(sin fuentes asociadas todavía)_")
            bloques.append("")
    else:
        bloques += ["_(sin conceptos todavía)_", ""]

    sin_concepto: list[str] = []
    for ruta_res in resumenes:
        with open(ruta_res, encoding="utf-8") as f:
            enlaces = re.findall(rf"\[\[[^\]]*?/{ENTIDADES}/[^\]|]+", f.read())
        if not enlaces:
            sin_concepto.append(
                f"- [[{backlink_relativo(vault_dir, ruta_res)}|{leer_titulo(ruta_res)}]]"
            )

    partes = [
        "---",
        "type: moc",
        "namespace: knowledge",
        "preserve: true",
        f"created: {datetime.now().isoformat(timespec='seconds')}",
        'title: "MOC — Mapa de contenido"',
        "tags: [knowledge, wiki, moc]",
        "---",
        "",
        "# 🗺️ MOC — Mapa de contenido",
        "",
        "> Índice generado de la wiki: cada concepto con las fuentes que lo tratan.",
        "",
        *bloques,
        "## 📄 Resúmenes sin concepto",
        "",
        *(sin_concepto or ["_(ninguno)_"]),
        "",
        "---",
        f"[[{NS_CONOCIMIENTO}/{WIKI}/{WIKI}|⬅ Volver a 05-WIKI]]",
        "",
    ]
    with open(ruta_moc, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))

    _asegurar_enlace_moc(vault_dir)
    return ruta_moc


def lint(vault_dir: str) -> ReporteLint:
    """Audita la salud de la wiki: enlaces rotos, huérfanas, conceptos sin página.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        ReporteLint: Con ``ok``, ``errores`` y ``avisos``.
    """
    errores: list[str] = []
    avisos: list[str] = []

    def _existe_target(target: str) -> bool:
        base = target.split("|")[0].strip().split("/")[-1].removesuffix(".md")
        for ruta, _t in _paginas(vault_dir) + [(os.path.join(ruta_wiki(vault_dir), ENTRY_LOG), "")]:
            if os.path.splitext(os.path.basename(ruta))[0] == base:
                return True
        # Índices y raíz del mundo conocimiento como targets válidos.
        extras = [
            f"{RESUMENES}.md", f"{ENTIDADES}.md", ENTRY_LOG, "05-WIKI.md", MOC,
            os.path.join(RESUMENES, RESUMENES),
            os.path.join(ENTIDADES, ENTIDADES),
            "00-INBOX.md", "01-PROJECTS.md", "02-AREAS.md", "03-RESOURCES.md",
            "04-ARCHIVE.md", "90-CONOCIMIENTO.md",
        ]
        return any(base == os.path.splitext(os.path.basename(x))[0] for x in extras)

    # 1. Enlaces de todas las páginas de la wiki que no resuelven.
    for ruta, _t in _paginas(vault_dir):
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", contenido):
            target = m.group(1)
            if not _existe_target(target):
                errores.append(f"ENLACE ROTO: {os.path.relpath(ruta, vault_dir)} -> [[{target}]]")

    # 2. Huérfanas: páginas de resumenes/entidades no enlazadas desde su índice.
    for carpeta, idx_name, _ancla in (
        (ruta_resumenes(vault_dir), f"{RESUMENES}.md", _ANCLA_RESUMENES),
        (ruta_entidades(vault_dir), f"{ENTIDADES}.md", _ANCLA_ENTIDADES),
    ):
        idx_path = os.path.join(carpeta, idx_name)
        if not os.path.isdir(carpeta):
            continue
        idx_txt = ""
        if os.path.exists(idx_path):
            with open(idx_path, encoding="utf-8") as f:
                idx_txt = f.read()
        for nombre in os.listdir(carpeta):
            if not nombre.endswith(".md") or nombre == idx_name:
                continue
            ruta = os.path.join(carpeta, nombre)
            link = backlink_relativo(vault_dir, ruta)
            if f"[[{link}" not in idx_txt:
                avisos.append(f"HUÉRFANA (no enlazada desde su índice): {os.path.relpath(ruta, vault_dir)}")

    # 3. Conceptos sin página: la página del resumen menciona una entidad que
    #    no tiene archivo propio.
    carpeta_ent = ruta_entidades(vault_dir)
    if os.path.isdir(carpeta_ent):
        existentes = {os.path.splitext(n)[0] for n in os.listdir(carpeta_ent) if n.endswith(".md")}
        for ruta, _t in _paginas(vault_dir):
            if ruta.startswith(carpeta_ent):
                continue
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
            for m in re.finditer(r"\[\[[^\]]*?" + ENTIDADES + r"/([^\]|]+)", contenido):
                ent = m.group(1).split("|")[0].strip().lower()
                if ent not in existentes:
                    errores.append(f"CONCEPTO SIN PÁGINA: {ent} mencionado en {os.path.basename(ruta)}")

    # 4. Posibles contradicciones entre páginas (misma frase afirmada y negada).
    avisos.extend(_detectar_contradicciones(vault_dir))

    # 5. Entry log apuntando a páginas que no existen.
    entry_log = os.path.join(ruta_wiki(vault_dir), ENTRY_LOG)
    if os.path.exists(entry_log):
        with open(entry_log, encoding="utf-8") as f:
            contenido = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", contenido):
            target = m.group(1)
            if not _existe_target(target):
                errores.append(f"ENTRY LOG ROTO: [[{target}]]")

    return ReporteLint(ok=not errores, errores=errores, avisos=avisos)

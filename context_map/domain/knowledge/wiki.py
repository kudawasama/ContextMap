"""Mundo CONOCIMIENTO: LLM Wiki (patrón Karpathy).

Páginas de resumen, entidades/conceptos y bitácora (entry log) dentro de
``90-CONOCIMIENTO/05-WIKI``. Operaciones deterministas que el AGENTE (o el
usuario) usa para construir y mantener la wiki del curso de Obsidian:

- ``ingresar``   → crea la página de resumen de una fuente, actualiza el índice
  de resúmenes, el entry log y las páginas de entidades/conceptos.
- ``consultar``  → ranking por solape de tokens; devuelve páginas CON CITAS
  (ruta del wikilink) para que el agente sintetice con trazabilidad.
- ``lint``       → salud de la wiki: enlaces rotos, páginas huérfanas,
  conceptos sin página e ítems del entry log apuntando a nada.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

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


# Palabras vacías para el ranking de consulta (es, de, la…).
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "en",
    "y", "o", "a", "para", "por", "con", "que", "se", "su", "al", "lo", "como",
    "es", "son", "mas", "más", "pero", "sobre", "entre", "esto", "esta", "the",
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


def _tokens(texto: str) -> set[str]:
    """Extrae tokens relevantes (minúsculos, sin stopwords) de un texto."""
    norm = re.findall(r"[a-záéíóúüñ0-9]{3,}", (texto or "").lower())
    return {t for t in norm if t not in _STOPWORDS}


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


def listar_paginas(vault_dir: str) -> list[dict[str, str]]:
    """Lista las páginas de la wiki (resúmenes y entidades) con su wikilink.

    Pensada para el brief de agentes: expone el Second Brain sin cargar el
    contenido completo de cada página.

    Args:
        vault_dir (str): Directorio raíz del vault.

    Returns:
        list[dict[str, str]]: Items con ``titulo``, ``tipo`` (``resumen`` |
        ``entidad``) y ``cita`` (wikilink relativo al vault). Los resúmenes
        van primero para priorizarse al truncar.
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
                "cita": f"[[{cita}|{titulo}]]",
            })
    return resultado


def consultar(vault_dir: str, pregunta: str, limite: int = 5) -> list[dict[str, str]]:
    """Busca páginas relevantes de la wiki por solape de tokens, con citas.

    Args:
        vault_dir (str): Directorio raíz del vault.
        pregunta (str): Texto de la consulta.
        limite (int): Máximo de resultados (default 5).

    Returns:
        list[dict[str, str]]: Resultados con ``titulo``, ``ruta``, ``cita``
        (wikilink) y ``excerpt`` (fragmento del contenido).
    """
    q_tokens = _tokens(pregunta)
    if not q_tokens:
        return []
    resultados: list[tuple[int, dict[str, str]]] = []
    for ruta, titulo in _paginas(vault_dir):
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
        doc_tokens = _tokens(titulo + " " + contenido)
        score = len(q_tokens & doc_tokens)
        if score == 0:
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
            f"{RESUMENES}.md", f"{ENTIDADES}.md", ENTRY_LOG, "05-WIKI.md",
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

    # 4. Entry log apuntando a páginas que no existen.
    entry_log = os.path.join(ruta_wiki(vault_dir), ENTRY_LOG)
    if os.path.exists(entry_log):
        with open(entry_log, encoding="utf-8") as f:
            contenido = f.read()
        for m in re.finditer(r"\[\[([^\]]+)\]\]", contenido):
            target = m.group(1)
            if not _existe_target(target):
                errores.append(f"ENTRY LOG ROTO: [[{target}]]")

    return ReporteLint(ok=not errores, errores=errores, avisos=avisos)

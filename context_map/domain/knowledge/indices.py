"""Utilidades compartidas del mundo CONOCIMIENTO (índices y notas PKM).

Funciones auxiliares que comparten el inbox (Second Brain) y la wiki (LLM Wiki):
slugs, rutas libres, backlinks relativos y mantenimiento de wikilinks en los
índices de cada categoría. Toda nota es ``namespace: knowledge`` + ``preserve``.
"""

from __future__ import annotations

import os
import re
import unicodedata


def slug(texto: str, max_len: int = 60) -> str:
    """Convierte un texto libre en un slug seguro para nombre de archivo.

    Args:
        texto (str): Texto de origen.
        max_len (int): Longitud máxima del slug.

    Returns:
        str: Slug en minúsculas con guiones.
    """
    norm = unicodedata.normalize("NFKD", texto)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return (norm[:max_len].rstrip("-")) or "nota"


def sanear(titulo: str) -> str:
    """Sanea un título para incrustarlo en frontmatter YAML entre comillas."""
    return (titulo or "").replace('"', "'").replace("\n", " ").strip()


def ruta_libre(carpeta: str, base: str) -> str:
    """Devuelve una ruta de archivo libre (agrega sufijo -2, -3… si existe).

    Args:
        carpeta (str): Directorio destino.
        base (str): Nombre base sin extensión.

    Returns:
        str: Ruta ``<carpeta>/<base>.md`` (o con sufijo si ya existe).
    """
    ruta = os.path.join(carpeta, f"{base}.md")
    contador = 2
    while os.path.exists(ruta):
        ruta = os.path.join(carpeta, f"{base}-{contador}.md")
        contador += 1
    return ruta


def backlink_relativo(vault_dir: str, ruta_nota: str) -> str:
    """Ruta del wikilink de una nota relativa al vault, sin extensión."""
    rel = os.path.relpath(ruta_nota, vault_dir).replace(os.sep, "/")
    return rel[:-3] if rel.endswith(".md") else rel


def leer_titulo(ruta: str) -> str:
    """Lee el título de una nota desde su frontmatter o su primer heading."""
    try:
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()
    except OSError:
        return os.path.basename(ruta)
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', contenido, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
    return m.group(1).strip() if m else os.path.basename(ruta)


def agregar_a_indice(index_path: str, ruta_nota_abs: str, vault_dir: str,
                     titulo: str, ancla: str) -> None:
    """Añade el wikilink de una nota al índice de su categoría (sin duplicar).

    Args:
        index_path (str): Ruta del archivo índice.
        ruta_nota_abs (str): Ruta absoluta de la nota a enlazar.
        vault_dir (str): Raíz del vault (para la ruta relativa del wikilink).
        titulo (str): Texto visible del enlace.
        ancla (str): Heading ``## ...`` bajo el cual insertar el enlace.
    """
    if not os.path.exists(index_path):
        return
    link = backlink_relativo(vault_dir, ruta_nota_abs)
    with open(index_path, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    if any(f"[[{link}" in ln for ln in lineas):
        return
    lineas = [ln for ln in lineas if not ln.strip().startswith("- _(vacío")]
    idx = next((i for i, ln in enumerate(lineas) if ln.strip() == ancla), None)
    entrada = f"- [[{link}|{titulo}]]"
    if idx is None:
        lineas.append(entrada)
    else:
        lineas.insert(idx + 1, "")
        lineas.insert(idx + 1, entrada)
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def quitar_de_indice(index_path: str, ruta_nota_abs: str, vault_dir: str) -> None:
    """Quita el wikilink de una nota de un índice (evita enlaces rotos al mover).

    Args:
        index_path (str): Ruta del archivo índice.
        ruta_nota_abs (str): Ruta absoluta de la nota.
        vault_dir (str): Raíz del vault (para la ruta relativa del wikilink).
    """
    if not os.path.exists(index_path):
        return
    link = backlink_relativo(vault_dir, ruta_nota_abs)
    with open(index_path, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    filtradas = [ln for ln in lineas if f"[[{link}" not in ln]
    if len(filtradas) != len(lineas):
        with open(index_path, "w", encoding="utf-8") as f:
            f.write("\n".join(filtradas) + "\n")

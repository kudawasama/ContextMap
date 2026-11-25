"""Validador de topología estricta del vault Obsidian (árbol puro).

Regla INAMOVIBLE (AGENTS.md §4): el Graph View debe verse como un árbol.
Este módulo centraliza la validación para que tanto los tests como el doctor
(``check_topologia``) compartan la misma implementación.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

#: Bloques y tramos de código: un wikilink escrito ahí es **texto literal**
#: (documentación, ejemplos), no una arista del grafo.
_FENCE_RE = re.compile(r"```.*?```", re.S)
_CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
_MARCA_RE = re.compile(r"\x00(\d+)\x00")


def texto_enlazable(contenido: str) -> str:
    """Devuelve el texto de una nota sin los tramos que no generan aristas.

    El validador busca wikilinks con una expresión regular sobre todo el
    fichero, así que una nota que **documente** un enlace roto
    (``p.ej. [[...]]`` dentro de comillas invertidas) se acusaba a sí misma.
    Ese falso positivo obligaba a mutilar la documentación para callar al
    validador.

    El orden importa: primero caen los bloques cercados, después se protegen
    los wikilinks ya formados y solo al final se retiran los tramos de código
    en línea. Al revés se rompían los enlaces cuyo **título** contiene
    comillas invertidas (típico en los riesgos consolidados:
    ``[[... `keywords.py` ya no existe...]]``), y el padre desaparecía.

    Los bytes NUL se retiran antes de nada: una nota con codificación mixta
    (UTF-8 con restos de UTF-16) contiene ``\x00`` sueltos, y un ``\x00``
    seguido de dígitos y otro ``\x00`` se leía como una marca de protección
    inventada (``IndexError``). Se descubrió con 6 notas así en un vault
    ajeno: el validador reventaba y el doctor entero caía con él.

    Args:
        contenido (str): Markdown completo de la nota.

    Returns:
        str: El mismo Markdown sin los tramos que no generan aristas.
    """
    contenido = contenido.replace("\x00", "")
    sin_bloques = _FENCE_RE.sub(" ", contenido)

    enlaces: list[str] = []

    def _proteger(m: re.Match[str]) -> str:
        enlaces.append(m.group(0))
        return f"\x00{len(enlaces) - 1}\x00"

    protegido = LINK_RE.sub(_proteger, sin_bloques)
    sin_codigo = _CODE_SPAN_RE.sub(" ", protegido)

    def _restaurar(m: re.Match[str]) -> str:
        indice = int(m.group(1))
        # Cinturón y tirantes: una marca fuera de rango se deja como estaba en
        # lugar de tumbar el análisis entero.
        if indice >= len(enlaces):
            return m.group(0)
        return enlaces[indice]

    return _MARCA_RE.sub(_restaurar, sin_codigo)

SIN_PADRE_PERMITIDOS = {"00-INDICE.md", "00-CONEXIONES.md", "90-CONOCIMIENTO.md"}

ENLACES_DOCUMENTALES_PERMITIDOS = {"entre-notas"}


def _namespace(rel: str) -> str:
    if rel == "90-CONOCIMIENTO.md" or rel.startswith("90-CONOCIMIENTO/"):
        return "knowledge"
    return "code"


@dataclass
class ResultadoTopologia:
    archivos: int = 0
    sin_padre: List[str] = field(default_factory=list)
    colisiones: List[str] = field(default_factory=list)
    enlaces_rotos: List[str] = field(default_factory=list)
    enlaces_cruzados: List[str] = field(default_factory=list)
    indices_sin_sufijo: List[str] = field(default_factory=list)

    @property
    def errores(self) -> List[str]:
        return (
            self.sin_padre
            + self.colisiones
            + self.enlaces_rotos
            + self.enlaces_cruzados
            + self.indices_sin_sufijo
        )

    @property
    def ok(self) -> bool:
        return len(self.errores) == 0


def analizar_topologia(vault_dir: str) -> ResultadoTopologia:
    """Recorre el vault y valida la topología en árbol."""
    res = ResultadoTopologia()
    if not os.path.isdir(vault_dir):
        return res

    archivos: dict[str, str] = {}
    for root, _dirs, files in os.walk(vault_dir):
        for f in files:
            if not f.endswith(".md"):
                continue
            rel = os.path.relpath(os.path.join(root, f), vault_dir).replace("\\", "/")
            if rel.startswith("templates/") or "/templates/" in rel:
                continue
            archivos[rel] = f[:-3]

    res.archivos = len(archivos)
    por_nombre: dict[str, List[str]] = {}
    for rel, base in archivos.items():
        por_nombre.setdefault(base, []).append(rel)

    for base, rutas in por_nombre.items():
        if len(rutas) > 1:
            res.colisiones.append(f"COLISIÓN nombre base '{base}': {rutas}")

    in_degree: dict[str, set[str]] = {rel: set() for rel in archivos}
    for rel in archivos:
        ruta = os.path.join(vault_dir, rel)
        try:
            with open(ruta, encoding="utf-8") as fh:
                contenido = texto_enlazable(fh.read())
        except OSError:
            continue
        for m in LINK_RE.findall(contenido):
            target = m.split("|")[0].strip().split("/")[-1]
            if target.endswith(".md"):
                target = target[:-3]
            if target in por_nombre:
                for r2 in por_nombre[target]:
                    if r2 != rel:
                        in_degree[r2].add(rel)
                        if _namespace(r2) != _namespace(rel):
                            res.enlaces_cruzados.append(
                                f"ENLACE CRUZADO: {rel} -> [[{m}]]"
                            )

    for rel in archivos:
        if rel in SIN_PADRE_PERMITIDOS:
            continue
        if not in_degree[rel]:
            res.sin_padre.append(f"SIN PADRE: {rel}")

    for rel in archivos:
        ruta = os.path.join(vault_dir, rel)
        try:
            with open(ruta, encoding="utf-8") as fh:
                contenido = texto_enlazable(fh.read())
        except OSError:
            continue
        for m in LINK_RE.findall(contenido):
            target = m.split("|")[0].strip().split("/")[-1]
            if target.endswith(".md"):
                target = target[:-3]
            if target not in por_nombre and target not in ENLACES_DOCUMENTALES_PERMITIDOS:
                res.enlaces_rotos.append(f"ENLACE ROTO: {rel} -> [[{m}]]")

    for rel in archivos:
        partes = rel.split("/")
        if len(partes) >= 4 and rel.startswith("2.0-IDEAS"):
            carpeta = partes[-2]
            base = partes[-1][:-3]
            if base == carpeta:
                sufijos_ok = ("-Pendientes", "-Futuras", "-Completas")
                if not base.endswith(sufijos_ok):
                    res.indices_sin_sufijo.append(
                        f"ÍNDICE DE CONCEPTO SIN SUFIJO DE ESTADO: {rel} "
                        f"(debe ser {carpeta}-Pendientes/-Futuras/-Completas.md)"
                    )

    return res

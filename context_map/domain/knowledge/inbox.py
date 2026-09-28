"""Mundo CONOCIMIENTO: inbox de captura PKM (Second Brain).

Gestiona la captura cruda en ``90-CONOCIMIENTO/00-INBOX`` y su clasificación a
PARA (Projects · Areas · Resources · Archive). Implementa el flujo del curso de
Obsidian **sin colisionar** con el mundo de código:

- Todas las notas son ``namespace: knowledge`` + ``preserve: true``: viven en una
  isla separada y el build jamás las toca.
- La clasificación es determinista (heurística por palabras clave). El agente
  puede afinarla llamando a ``mover_nota`` con la categoría que decida.
- Al mover una nota se actualizan los wikilinks de los índices: la nota cuelga
  de su sección y cada índice enlaza a sus notas (topología válida).
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from context_map.domain.knowledge.indices import (
    agregar_a_indice as _agregar_a_indice,
)
from context_map.domain.knowledge.indices import (
    leer_titulo,
)
from context_map.domain.knowledge.indices import (
    quitar_de_indice as _quitar_de_indice,
)
from context_map.domain.knowledge.indices import (
    ruta_libre as _ruta_libre,
)
from context_map.domain.knowledge.indices import (
    sanear as _sanear,
)
from context_map.domain.knowledge.indices import (
    slug as _slug,
)

NS_CONOCIMIENTO = "90-CONOCIMIENTO"

# categoría -> (subcarpeta, archivo índice, ancla del índice)
CATEGORIAS: dict[str, tuple[str, str, str]] = {
    "inbox": ("00-INBOX", "00-INBOX.md", "## 📝 Notas en el inbox"),
    "projects": ("01-PROJECTS", "01-PROJECTS.md", "## 📝 Proyectos"),
    "areas": ("02-AREAS", "02-AREAS.md", "## 📝 Áreas"),
    "resources": ("03-RESOURCES", "03-RESOURCES.md", "## 📝 Recursos"),
    "archive": ("04-ARCHIVE", "04-ARCHIVE.md", "## 📝 Archivado"),
}

# Categorías destino válidas para clasificar (excluye 'inbox').
DESTINOS: tuple[str, ...] = ("projects", "areas", "resources", "archive")

# Heurística: (categoría, palabras clave). El orden importa (más específicas antes).
_PISTAS: list[tuple[str, tuple[str, ...]]] = [
    ("archive", ("archivar", "archivado", "cerrado", "terminado", "finalizado",
                 "obsoleto", "descartado", "deprecado")),
    ("projects", ("proyecto", "curso", "publicar", "publicacion", "implementar",
                  "entregar", "lanzar", "deadline", "sprint", "milestone",
                  "artículo", "articulo", "video", "tutorial", "charla")),
    ("areas", ("trabajo", "salud", "formacion", "formación", "rutina", "hobby",
               "equipo", "responsabilidad", "habito", "hábito", "carrera",
               "finanzas", "ejercicio", "familia")),
    ("resources", ("recurso", "apunte", "referencia", "documentacion",
                   "documentación", "tema", "guardar", "investigar", "aprender",
                   "paper", "libro", "resumen")),
]

# Categoría por defecto cuando ningún patrón coincide: 'resources' es el cajón
# "no sé cuándo lo usaré" del método PARA.
DEFAULT = "resources"


def ruta_conocimiento(vault_dir: str) -> str:
    """Ruta raíz del mundo conocimiento dentro del vault.

    Args:
        vault_dir (str): Directorio raíz del vault Obsidian.

    Returns:
        str: Ruta de ``90-CONOCIMIENTO``.
    """
    return os.path.join(vault_dir, NS_CONOCIMIENTO)


def ruta_categoria(vault_dir: str, categoria: str) -> str:
    """Ruta de la carpeta de una categoría (PARA o inbox).

    Args:
        vault_dir (str): Directorio raíz del vault.
        categoria (str): Clave de ``CATEGORIAS``.

    Returns:
        str: Ruta absoluta/relativa de la carpeta.
    """
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoría desconocida: {categoria!r}. Válidas: {list(CATEGORIAS)}")
    sub, _idx, _ancla = CATEGORIAS[categoria]
    return os.path.join(ruta_conocimiento(vault_dir), sub)


def _contenido_nota(titulo: str, texto: str, fuente: str, status: str, padre: str) -> str:
    """Construye el Markdown de una nota PKM con frontmatter y pie de padre."""
    fecha = datetime.now().isoformat(timespec="seconds")
    return (
        "---\n"
        "type: nota\n"
        "namespace: knowledge\n"
        "preserve: true\n"
        f"created: {fecha}\n"
        f'title: "{_sanear(titulo)}"\n'
        f'source: "{_sanear(fuente)}"\n'
        f"status: {status}\n"
        "tags: [knowledge, inbox]\n"
        "---\n\n"
        f"# {titulo}\n\n"
        f"{texto.strip()}\n\n"
        "---\n"
        f"[[{padre}|⬅ Volver a {padre.split('/')[-1]}]]\n"
    )


def crear_nota(vault_dir: str, texto: str, titulo: str | None = None,
               tags: str = "", fuente: str = "", categoria: str = "inbox") -> str:
    """Crea una nota PKM en la categoría indicada (por defecto el inbox).

    Args:
        vault_dir (str): Directorio raíz del vault.
        texto (str): Cuerpo de la nota.
        titulo (str | None): Título; si falta, se deriva del texto.
        tags (str): Etiquetas extra separadas por coma.
        fuente (str): Origen de la nota (URL, archivo, conversación…).
        categoria (str): Clave de ``CATEGORIAS`` destino.

    Returns:
        str: Ruta de la nota creada.
    """
    if categoria not in CATEGORIAS:
        raise ValueError(f"Categoría desconocida: {categoria!r}")
    if not (texto or "").strip() and not titulo:
        raise ValueError("La nota necesita texto o título.")

    titulo_final = (titulo or texto).strip().splitlines()[0][:120] or "Nota"
    carpeta = ruta_categoria(vault_dir, categoria)
    os.makedirs(carpeta, exist_ok=True)

    base = f"{datetime.now().date().isoformat()}-{_slug(titulo_final)}"
    ruta = _ruta_libre(carpeta, base)
    sub, idx_file, ancla = CATEGORIAS[categoria]
    padre = f"{NS_CONOCIMIENTO}/{sub}/{sub}"
    status = "inbox" if categoria == "inbox" else "activo"

    contenido = _contenido_nota(titulo_final, texto, fuente, status, padre)
    if tags:
        contenido = contenido.replace(
            "tags: [knowledge, inbox]",
            "tags: [knowledge, inbox, " + ", ".join(t.strip() for t in tags.split(",") if t.strip()) + "]",
        )
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)

    _agregar_a_indice(os.path.join(carpeta, idx_file), ruta, vault_dir, titulo_final, ancla)
    return ruta


def listar_notas(vault_dir: str, categoria: str = "inbox") -> list[dict[str, str]]:
    """Lista las notas de una categoría (sin contar el índice ni el entry-log).

    Args:
        vault_dir (str): Directorio raíz del vault.
        categoria (str): Clave de ``CATEGORIAS``.

    Returns:
        list[dict[str, str]]: Notas con claves ``ruta`` y ``titulo``.
    """
    carpeta = ruta_categoria(vault_dir, categoria)
    if not os.path.isdir(carpeta):
        return []
    _sub, idx_file, _ancla = CATEGORIAS[categoria]
    ignorar = {idx_file, "entry-log.md", "entidades.md", "resumenes.md"}
    notas: list[dict[str, str]] = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.endswith(".md") or nombre in ignorar:
            continue
        ruta = os.path.join(carpeta, nombre)
        notas.append({"ruta": ruta, "titulo": leer_titulo(ruta)})
    return notas


# leer_titulo se importa desde indices.py (compartido con la wiki).


def clasificar(texto: str) -> str:
    """Clasifica un texto en una categoría PARA mediante heurística.

    Args:
        texto (str): Título + cuerpo de la nota.

    Returns:
        str: Clave de categoría en ``DESTINOS``.
    """
    bajo = (texto or "").lower()
    for categoria, pistas in _PISTAS:
        if any(p in bajo for p in pistas):
            return categoria
    return DEFAULT


def mover_nota(vault_dir: str, archivo: str, destino: str) -> str:
    """Mueve una nota del inbox a una categoría destino y actualiza sus enlaces.

    Args:
        vault_dir (str): Directorio raíz del vault.
        archivo (str): Nombre o ruta de la nota a mover.
        destino (str): Categoría destino (``DESTINOS``).

    Returns:
        str: Ruta final de la nota.
    """
    if destino not in DESTINOS:
        raise ValueError(f"Destino inválido: {destino!r}. Válidos: {list(DESTINOS)}")

    origen = archivo if os.path.isabs(archivo) or os.sep in archivo else os.path.join(
        ruta_categoria(vault_dir, "inbox"), archivo
    )
    if not os.path.exists(origen):
        raise FileNotFoundError(f"No existe la nota: {origen}")

    titulo = leer_titulo(origen)
    carpeta_destino = ruta_categoria(vault_dir, destino)
    os.makedirs(carpeta_destino, exist_ok=True)
    ruta_final = _ruta_libre(carpeta_destino, os.path.splitext(os.path.basename(origen))[0])

    sub, idx_file, ancla = CATEGORIAS[destino]
    padre = f"{NS_CONOCIMIENTO}/{sub}/{sub}"

    with open(origen, encoding="utf-8") as f:
        contenido = f.read()
    contenido = re.sub(r"^status:.*$", "status: activo", contenido, count=1, flags=re.MULTILINE)
    contenido = re.sub(r"\[\[[^\]]*\|\s*⬅[^\]]*\]\]",
                       f"[[{padre}|⬅ Volver a {sub}]]", contenido)
    with open(ruta_final, "w", encoding="utf-8") as f:
        f.write(contenido)
    os.remove(origen)

    sub_ini, idx_ini, _a = CATEGORIAS["inbox"]
    _quitar_de_indice(os.path.join(ruta_categoria(vault_dir, "inbox"), idx_ini), origen, vault_dir)
    _agregar_a_indice(os.path.join(carpeta_destino, idx_file), ruta_final, vault_dir, titulo, ancla)
    return ruta_final


def purgar(vault_dir: str, dry_run: bool = False) -> list[dict[str, str]]:
    """Clasifica todas las notas del inbox a PARA y vacía el inbox.

    Args:
        vault_dir (str): Directorio raíz del vault.
        dry_run (bool): Si es True, solo calcula las decisiones sin mover nada.

    Returns:
        list[dict[str, str]]: Decisiones aplicadas (o simuladas) con claves
        ``nota``, ``destino`` y (si se movió) ``ruta``.
    """
    decisiones: list[dict[str, str]] = []
    for nota in listar_notas(vault_dir, "inbox"):
        ruta = nota["ruta"]
        try:
            with open(ruta, encoding="utf-8") as f:
                cuerpo = f.read()
        except OSError:
            continue
        destino = clasificar(f"{nota['titulo']} {cuerpo}")
        decision = {"nota": os.path.basename(ruta), "titulo": nota["titulo"], "destino": destino}
        if not dry_run:
            decision["ruta"] = mover_nota(vault_dir, ruta, destino)
        decisiones.append(decision)
    return decisiones

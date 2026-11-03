"""Sanitización, depuración y deduplicación de nodos del grafo.

Proporciona funciones para estandarización de tags, limpieza de rutas,
depuración de nodos de riesgo obsoletos y deduplicación de nodos.
"""

from __future__ import annotations

import os
import re

from context_map.core.models import Node
from context_map.core.normalization.inference import classification_tag
from context_map.core.normalization.mappings import (
    TAG_FILE_MAP,
    TAG_MERGE,
    TAGS_ELIMINAR,
)


def estandarizar_tags(tags: list[str]) -> list[str]:
    """Estandariza, limpia y desduplica la lista de etiquetas de un nodo.

    Args:
        tags (list[str]): Lista de etiquetas originales.

    Returns:
        list[str]: Lista de etiquetas estandarizadas y ordenadas.
    """
    tags_estandarizados: list[str] = []

    for tag in tags:
        if tag in TAGS_ELIMINAR:
            continue
        if tag in TAG_FILE_MAP:
            tag = TAG_FILE_MAP[tag]
        if tag in TAG_MERGE:
            tag = TAG_MERGE[tag]

        tag = tag.lower().strip()
        tag = re.sub(r"[^a-z0-9:]", "", tag)

        if tag and tag not in tags_estandarizados:
            tags_estandarizados.append(tag)

    return sorted(tags_estandarizados)


def ajustar_tags(tags: list[str], classif_id: str) -> list[str]:
    """Deja la lista de tags lista para persistir con su ``class:<id>``.

    Retira las etiquetas legacy sin dos puntos (``classchore``,
    ``classfeature``…) que dejaron escaneos antiguos y garantiza que la
    etiqueta de clasificación aparezca una sola vez y en formato limpio.

    Args:
        tags (list[str]): Etiquetas ya estandarizadas por
            :func:`estandarizar_tags`.
        classif_id (str): Clasificación semántica calculada para el nodo.

    Returns:
        list[str]: Etiquetas sin legacy y con ``class:<classif_id>`` presente.
    """
    limpios = [t for t in tags if not re.match(r"^class[a-z]+$", t)]
    etiqueta = classification_tag(classif_id)
    if etiqueta not in limpios:
        limpios.append(etiqueta)
    return limpios


def normalizar_titulo(node: Node) -> str:
    """Devuelve el título del nodo sin volátiles numéricos de complejidad.

    Los scans antiguos escribían ``RIESGO`` con el recuento de líneas pegado al
    título (``… (151 líneas); … (120 líneas)``). Ese número cambia con cualquier
    edición, así que rompe la deduplicación por título: se retira y se
    reconstruyen los paths aplanados (``context_mapcore…``) que dejaban esos
    mismos scans.

    Args:
        node (Node): Nodo original.

    Returns:
        str: Título limpio; intacto si el nodo no es ``RIESGO``.
    """
    if node.type != "RIESGO":
        return node.title

    titulo = re.sub(r"\s*\(\d+\s*(?:l[ií]neas?|l[ií]n|total|l(?!\w))\)?", "", node.title)
    titulo = re.sub(r";\s*[^;]+\(\d+\s*l[ií]neas?\)?", "", titulo)
    titulo = re.sub(r"\s*;\s*", ", ", titulo)
    return _restaurar_paths_legibles(titulo.rstrip(";,").strip())


def _restaurar_paths_legibles(titulo: str) -> str:
    """Reconstruye separadores en paths aplanados por scans antiguos.

    Ejemplo: ``context_mapcorenormalizationstandardize.py`` →
    ``context_map/core/normalization/standardize.py``.

    Args:
        titulo (str): Título del riesgo (posiblemente aplanado).

    Returns:
        str: Título con paths legibles cuando fue posible reconstruirlos.
    """
    SEGMENTOS = (
        "context_map", "core", "domain", "application", "infrastructure",
        "presentation", "scripts", "tests", "api", "src", "backend", "frontend",
        "models", "commands", "parsing", "storage", "generators", "normalization",
        "scanning", "synchronization", "ecosystem", "analysis", "vault", "briefs",
        "importers", "integrations", "cli", "adaptador", "detector", "templates",
        "raw", "consolidated", "atomic", "services", "utils", "helpers", "config",
        "standardize", "estandarizar",
    )
    texto = titulo
    for seg in SEGMENTOS:
        texto = re.sub(
            rf"(?<=\w){re.escape(seg)}(?=[a-z_.])",
            "/" + seg,
            texto,
        )
    return texto


def depurar_nodos_obsoletos(nodes: list[Node], project_root: str = ".") -> list[Node]:
    """Filtra y elimina nodos de RIESGO obsoletos cuyos archivos referenciados ya no existen.

    Args:
        nodes (list[Node]): Nodos del grafo.
        project_root (str): Ruta raíz del proyecto.

    Returns:
        list[Node]: Lista de nodos purgada.
    """
    nodos_validos: list[Node] = []
    for n in nodes:
        if n.type == "RIESGO":
            if re.search(r"\(\d+\s*l[ií]neas?\)", n.title, re.IGNORECASE) or re.search(r"\(\d+\s*l[ií]neas?\)", n.summary or "", re.IGNORECASE):
                continue

            archivos = re.findall(r"([\w.\-/]+\.py)", n.title + " " + (n.summary or ""))
            if archivos:
                existe = False
                for fname in archivos:
                    if os.path.exists(os.path.join(project_root, fname)) or os.path.exists(fname):
                        existe = True
                        break
                    base = os.path.basename(fname)
                    for _root, dirs, files in os.walk(project_root):
                        dirs[:] = [d for d in dirs if d not in (".git", ".venv", "venv", "node_modules", ".context-map")]
                        if base in files:
                            existe = True
                            break
                    if existe:
                        break
                if not existe:
                    continue

        nodos_validos.append(n)
    return nodos_validos


def dedup_nodes(nodes: list[Node]) -> list[Node]:
    """Elimina nodos duplicados conservando la última ocurrencia por (type, title[:80]).

    Previene la acumulación de nodos duplicados en graph.jsonl después de
    múltiples ciclos de scan/build. Mantiene el nodo más reciente (último
    en aparecer) como representante de cada clave única.

    Args:
        nodes (list[Node]): Lista de nodos con posibles duplicados.

    Returns:
        list[Node]: Lista desduplicada, último nodo por clave gana.
    """
    nodes_limpios = depurar_nodos_obsoletos(nodes)
    seen: dict[tuple[str, str], Node] = {}
    for n in nodes_limpios:
        key = (n.type, n.title[:80].lower())
        seen[key] = n  # última ocurrencia gana
    return list(seen.values())

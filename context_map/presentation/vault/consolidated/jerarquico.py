"""Renderizado de la bóveda Obsidian en modo jerárquico en árbol.

Genera la estructura temática en árbol con 6 secciones raíz (1.0-6.0), sus
sub-secciones y notas atómicas, respetando la topología estricta: el índice
enlaza solo a secciones raíz, cada sección raíz a sus sub-nodos, y las hojas
únicamente a su sección padre.
"""

from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.common import (
    _clasificar_nodos,
    _escribir_markdown,
    _render_grafo_conexiones,
)
from context_map.presentation.vault.consolidated.secciones_backlog import _render_seccion_backlog
from context_map.presentation.vault.consolidated.secciones_estructura import _render_seccion_estructura
from context_map.presentation.vault.consolidated.secciones_historial import _render_seccion_historial
from context_map.presentation.vault.consolidated.secciones_ideas import (
    _render_nota_idea,
    _render_seccion_ideas,
)
from context_map.presentation.vault.consolidated.secciones_proposito import _render_seccion_proposito
from context_map.presentation.vault.consolidated.secciones_riesgos import (
    _render_nota_riesgo,
    _render_seccion_riesgos,
)

logger = logging.getLogger(__name__)

TAG_FIXTOS: dict[str, list[str]] = {}


def _cabecera(
    tipo: str,
    subtype: str | None,
    project_name: str,
    fecha_actual: str,
    tags: list[str],
    titulo: str,
) -> list[str]:
    """Construye frontmatter YAML y encabezado para notas jerárquicas.

    Args:
        tipo (str): Valor del campo 'type'.
        subtype (str | None): Valor del campo 'subtype' si corresponde.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        tags (list[str]): Lista de tags.
        titulo (str): Título principal de la nota.

    Returns:
        list[str]: Líneas iniciales de la nota.
    """
    tags_str = ", ".join(tags)
    partes = [
        "---",
        f"type: {tipo}",
    ]
    if subtype:
        partes.append(f"subtype: {subtype}")
    partes.extend([
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        "---",
        "",
        titulo,
        "",
    ])
    return partes


def _pie(backlink: str) -> list[str]:
    """Construye el cierre estándar con wikilink de retorno.

    Args:
        backlink (str): Wikilink de navegación de regreso.

    Returns:
        list[str]: Líneas finales de la nota.
    """
    return [
        "---",
        backlink,
        "",
    ]


def _render_indice_hierarchico(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
) -> None:
    """Renderiza 00-INDICE.md del modo jerárquico enlazando a las 6 secciones raíz.

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Lista completa de nodos.
        edges (list[Edge]): Lista de aristas/relaciones.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
    """
    all_tags: set[str] = set()
    for n in nodes:
        all_tags.update(n.tags)
    tags_badges = " ".join(f"`#{t}`" for t in sorted(all_tags)[:20])

    # Notas manuales (zonas protegidas 7.0-MANUAL y .manual) para el índice
    from context_map.presentation.vault.preservar import ZONAS_MANUALES

    manual_notas: list[str] = []
    for zona in ZONAS_MANUALES:
        zona_dir = os.path.join(output_dir, zona)
        if os.path.isdir(zona_dir):
            for raiz, _dirs, archivos in os.walk(zona_dir):
                for fname in sorted(archivos):
                    if not fname.endswith(".md"):
                        continue
                    rel = os.path.relpath(os.path.join(raiz, fname), output_dir)
                    manual_notas.append(rel.replace(os.sep, "/"))

    partes = [
        "---",
        "type: moc",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"total_nodes: {len(nodes)}",
        f"total_edges: {len(edges)}",
        "tags: [context-map, indice, moc]",
        "---",
        "",
        f"# 🗺️ Indice MOC — {project_name}",
        "",
        "> Mapa jerárquico del proyecto. Navegá por secciones temáticas para explorar cada aspecto del contexto.",
        "",
        "---",
        "",
        "## 📊 Métricas",
        "",
        f"- 📦 Nodos Totales: **{len(nodes)}**",
        f"- 🧱 BASE: **{len(clasificados['BASE'])}**",
        f"- 💡 IDEA: **{len(clasificados['IDEA'])}**",
        f"- ⚠️ RIESGO: **{len(clasificados['RIESGO'])}**",
        f"- 🔄 CAMBIO/CORRECCION: **{len(clasificados['CAMBIO'])}**",
        f"- 🔮 FUTURO: **{len(clasificados['FUTURO'])}**",
        f"- 🎯 HITO: **{len(clasificados['HITO'])}**",
        f"- 🔗 Conexiones: **{len(edges)}**",
        "",
        "---",
        "",
        "## 📂 Secciones",
        "",
        "- [[1.0-PROPOSITO/1.0-PROPOSITO|1.0 Propósito]]",
        "- [[2.0-IDEAS/2.0-IDEAS|2.0 Ideas]]",
        "- [[3.0-ESTRUCTURA/3.0-ESTRUCTURA|3.0 Estructura]]",
        "- [[4.0-RIESGOS/4.0-RIESGOS|4.0 Riesgos]]",
        "- [[5.0-BACKLOG/5.0-BACKLOG|5.0 Backlog]]",
        "- [[6.0-HISTORIAL/6.0-HISTORIAL|6.0 Historial]]",
        "- [[8.0-KNOWLEDGE/8.0-KNOWLEDGE|8.0 Knowledge (aprendizaje)]]",
        "",
        "---",
        "",
    ]
    if manual_notas:
        partes.extend(["## 📝 Notas Manuales", ""])
        for rel in manual_notas:
            nombre = os.path.splitext(os.path.basename(rel))[0]
            partes.append(f"- [[{rel}|{nombre}]]")
        partes.extend(["", "---", ""])
    partes.extend(
        [
            "## 🏷️ Tags Principales",
            "",
        ]
    )
    partes.append(tags_badges or "`#context-map`")
    partes.append("")

    _escribir_markdown(output_dir, "00-INDICE.md", partes)


def _render_hierarchical_vault(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo jerárquico en árbol."""
    backlog_dir = os.path.join(output_dir, "5.0-BACKLOG")
    preservados: dict[str, str] = {}
    if os.path.isdir(backlog_dir):
        for fname in os.listdir(backlog_dir):
            if fname.endswith(".md") and fname not in ("5.0-BACKLOG.md", "5.1-Tareas.md"):
                fpath = os.path.join(backlog_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        preservados[fname] = f.read()
                except Exception as err:
                    logger.debug("No se pudo respaldar %s: %s", fname, err)

    # Limpiar el vault SIN destruir el trabajo manual (.manual/ + preserve:true)
    from context_map.presentation.vault.preservar import limpiar_vault

    limpiar_vault(output_dir)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    clasificados = _clasificar_nodos(nodes)

    _render_indice_hierarchico(project_name, nodes, edges, clasificados, fecha_actual, output_dir)
    _render_seccion_proposito(project_name, nodes, edges, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_seccion_ideas(project_name, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_seccion_estructura(project_name, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_seccion_riesgos(project_name, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_seccion_backlog(project_name, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_seccion_historial(project_name, clasificados, fecha_actual, output_dir, _cabecera, _pie)
    _render_grafo_conexiones(output_dir, nodes, edges, con_wikilinks=True, usar_rutas_reales=True)

    # Mapa mental conectado: lienzo, grupos de color, plantillas y nota del día
    from context_map.presentation.vault.consolidated.canvas import (
        render_canvas,
        render_graph_json,
        render_nota_dia,
        render_plantillas,
    )

    project_root = os.path.dirname(os.path.dirname(output_dir))
    # Fix CI (2026-08-12): los extras visuales (lienzo, plantillas, nota del
    # día) son OPCIONALES — si el directorio base no es escribible (p. ej. la
    # raíz del sistema al renderizar en un temp dir de 2 niveles), se omiten
    # sin romper el vault. En Linux CI esto era PermissionError: '/.context-map'.
    try:
        render_canvas(output_dir, nodes, edges)
        render_graph_json(output_dir, nodes)
        render_plantillas(project_root, project_name)
        render_nota_dia(project_root, project_name, nodes)
        os.makedirs(os.path.join(output_dir, "adjuntos"), exist_ok=True)
    except OSError as err:
        logging.getLogger(__name__).warning("Extras visuales omitidos: %s", err)

    if preservados:
        target_backlog = os.path.join(output_dir, "5.0-BACKLOG")
        os.makedirs(target_backlog, exist_ok=True)
        for fname, content in preservados.items():
            tpath = os.path.join(target_backlog, fname)
            with open(tpath, "w", encoding="utf-8") as f:
                f.write(content)

    return output_dir

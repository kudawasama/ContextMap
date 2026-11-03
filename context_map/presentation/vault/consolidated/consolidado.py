"""Renderizado de la bóveda Obsidian en modo consolidado.

Genera 8 notas temáticas sintéticas (índice MOC, propósito, ideas, estructura,
riesgos, backlog, historial y conexiones) a partir del grafo de contexto para
un consumo eficiente por parte de agentes de IA.

Este módulo es solo el **orquestador**. Las notas viven en:

- ``consolidado_base``: frontmatter, pie con wikilink y secciones del índice.
- ``consolidado_meta``: índice MOC, propósito y estructura.
- ``consolidado_contenido``: ideas, riesgos, backlog e historial.

El orden de escritura importa: el índice se escribe primero porque es el nodo
raíz del que cuelga la navegación del vault.
"""

from __future__ import annotations

from datetime import datetime

from context_map.core.models import Edge, Node
from context_map.presentation.vault.consolidated.consolidado_base import (
    SECCIONES_MOC,
    _cabecera_nota,
    _pie_nota,
)
from context_map.presentation.vault.consolidated.consolidado_contenido import (
    _render_backlog,
    _render_historial,
    _render_ideas,
    _render_lista_cambios,
    _render_lista_pruebas,
    _render_lista_riesgos,
    _render_riesgos,
)
from context_map.presentation.vault.consolidated.consolidado_meta import (
    _render_estructura,
    _render_indice,
    _render_proposito,
)
from context_map.presentation.vault.consolidated.escritura import _render_grafo_conexiones
from context_map.presentation.vault.consolidated.nodos import _clasificar_nodos


def _render_consolidated_vault(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    output_dir: str = ".context-map/vault",
) -> str:
    """Renderiza la bóveda Obsidian en modo consolidado (8 notas temáticas sintéticas)."""
    # Limpiar el vault SIN destruir el trabajo manual (.manual/ + preserve:true)
    from context_map.presentation.vault.preservar import limpiar_vault

    limpiar_vault(output_dir)
    fecha_actual = datetime.now().isoformat(timespec="seconds")

    clasificados = _clasificar_nodos(nodes)

    _render_indice(project_name, nodes, edges, clasificados, fecha_actual, output_dir)
    _render_proposito(project_name, clasificados, fecha_actual, output_dir)
    _render_ideas(project_name, clasificados, fecha_actual, output_dir)
    _render_estructura(project_name, clasificados, fecha_actual, output_dir)
    _render_riesgos(project_name, clasificados, fecha_actual, output_dir)
    _render_backlog(project_name, clasificados, fecha_actual, output_dir)
    _render_historial(project_name, clasificados, fecha_actual, output_dir)
    _render_grafo_conexiones(output_dir, nodes, edges)

    return output_dir


__all__ = [
    "SECCIONES_MOC",
    "_cabecera_nota",
    "_pie_nota",
    "_render_backlog",
    "_render_consolidated_vault",
    "_render_estructura",
    "_render_historial",
    "_render_ideas",
    "_render_indice",
    "_render_lista_cambios",
    "_render_lista_pruebas",
    "_render_lista_riesgos",
    "_render_proposito",
    "_render_riesgos",
]

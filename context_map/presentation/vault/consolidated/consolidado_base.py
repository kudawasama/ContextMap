"""Piezas comunes de las notas del modo consolidado.

El modo consolidado escribe 8 notas temáticas; todas comparten el mismo
frontmatter YAML, el mismo cierre con wikilink de retorno y la misma lista de
secciones del índice MOC. Esas tres piezas viven aquí para que los módulos de
notas no las dupliquen.
"""

from __future__ import annotations

SECCIONES_MOC = [
    ("01-PROPOSITO", "01. Propósito del Proyecto"),
    ("02-IDEAS", "02. Ideas y Características"),
    ("03-ESTRUCTURA", "03. Estructura del Proyecto"),
    ("04-RIESGOS_Y_COMPLEJIDAD", "04. Riesgos y Complejidad"),
    ("05-BACKLOG_Y_TODOS", "05. Backlog y Tareas Pendientes"),
    ("06-HISTORIAL_Y_DECISIONES", "06. Historial y Decisiones"),
    ("00-CONEXIONES", "07. Grafo Completo de Conexiones"),
]
"""Secciones que el índice MOC enlaza, en el orden en que se muestran."""


def _cabecera_nota(tipo: str, project_name: str, fecha_actual: str, tags: str, titulo: str) -> list[str]:
    """Construye el frontmatter YAML y encabezado estándar de una nota.

    Args:
        tipo (str): Valor del campo 'type' del frontmatter.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO de creación.
        tags (str): Lista de tags en formato YAML.
        titulo (str): Título principal de la nota.

    Returns:
        list[str]: Líneas iniciales de la nota (frontmatter + título).
    """
    return [
        "---",
        f"type: {tipo}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: {tags}",
        "---",
        "",
        titulo,
        "",
    ]


def _pie_nota(backlink: str = "[[00-INDICE|⬅ Volver al índice]]") -> list[str]:
    """Construye el cierre estándar de una nota con su wikilink de retorno.

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

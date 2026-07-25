"""Estandarización de nodos del grafo.

Proporciona funciones para:
- Estandarizar tags (elimina redundantes, fusiona duplicados)
- Inferir status (completado, pendiente, activo)
- Corregir tipos basado en contenido real
- Agregar evidence (rutas, líneas, clases)
"""

from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional

from context_map.core.models import Node


# ============================================================
# MAPEOS DE ESTANDARIZACIÓN
# ============================================================

# Tags a eliminar (redundantes o no informativos)
TAGS_ELIMINAR = {
    'todo',           # Redundante con 'pendiente'
    'otro',           # No informativo
    'docstring',      # Demasiado específico
    '__init__.py',    # Es un archivo, no un concepto
}

# Mapeo de tags de archivo a conceptos
TAG_FILE_MAP = {
    'antigravity.py': 'integracion',
    'chat_export.py': 'integracion',
    'checker.py': 'analisis',
    'cli.py': 'cli',
    'content.py': 'analisis',
    'git.py': 'integracion',
    'hermes.py': 'integracion',
    'models.py': 'modelos',
    'structure.py': 'analisis',
    'brief.py': 'presentacion',
    'generadores.py': 'generadores',
    'parser.py': 'parser',
    'reporter.py': 'reportes',
    'scanner.py': 'scanner',
    'smoke.py': 'testing',
    'store.py': 'persistencia',
    'sync.py': 'sincronizacion',
    'writer.py': 'presentacion',
}

# Tags duplicados a fusionar
TAG_MERGE = {
    'doc': 'documentacion',
    'docs': 'documentacion',
    'commit': 'git',
    'repo': 'git',
    'riesgo': 'riesgo',
    'complejidad': 'riesgo',
    'clases': 'modelos',
    'estructura': 'arquitectura',
    'config': 'configuracion',
    'entrypoint': 'cli',
    'tests': 'testing',
    'metricas': 'analisis',
    'python': 'lenguaje',
}


def estandarizar_tags(tags: List[str]) -> List[str]:
    """Estandariza una lista de tags."""
    tags_estandarizados = []

    for tag in tags:
        # 1. Eliminar tags redundantes
        if tag in TAGS_ELIMINAR:
            continue

        # 2. Mapear tags de archivo a conceptos
        if tag in TAG_FILE_MAP:
            tag = TAG_FILE_MAP[tag]

        # 3. Fusionar tags duplicados
        if tag in TAG_MERGE:
            tag = TAG_MERGE[tag]

        # 4. Normalizar: minúsculas, sin guiones raros
        tag = tag.lower().strip()
        tag = re.sub(r'[^a-z0-9]', '', tag)  # Solo alfanuméricos

        if tag and tag not in tags_estandarizados:
            tags_estandarizados.append(tag)

    return sorted(tags_estandarizados)


def inferir_status(node: Node) -> str:
    """Infiere el status basado en el contexto del nodo."""
    # 1. Si es de git, está completado
    if node.source == 'git':
        return 'completado'

    # 2. Si tiene tag 'pendiente', está pendiente
    if 'pendiente' in node.tags or 'todo' in node.tags:
        return 'pendiente'

    # 3. Si es RIESGO, está activo
    if node.type == 'RIESGO':
        return 'activo'

    # 4. Si es CORRECCION, está completado
    if node.type == 'CORRECCION':
        return 'completado'

    # 5. Por defecto: pendiente
    return 'pendiente'


def inferir_evidence(node: Node) -> List[str]:
    """Infiere evidencia basada en el contenido del nodo."""
    evidence = []

    # Del título
    if node.title:
        # Buscar rutas de archivo
        rutas = re.findall(r'[.\w/\\]+\.\w+', node.title)
        if rutas:
            evidence.extend([f"Archivo: {r}" for r in rutas[:3]])

        # Buscar números
        numeros = re.findall(r'\d+', node.title)
        if numeros:
            evidence.append(f"Cantidad: {numeros[0]}")

    # Del summary
    if node.summary:
        # Buscar líneas de código
        lineas = re.findall(r'(\d+)\s*líneas?', node.summary)
        if lineas:
            evidence.append(f"Líneas de código: {lineas[0]}")

        # Buscar clases
        clases = re.findall(r'clase[s]?\s*[:]\s*([A-Z]\w+)', node.summary)
        if clases:
            evidence.append(f"Clases: {', '.join(clases[:3])}")

    return evidence


def corregir_tipo(node: Node) -> str:
    """Corrige el tipo basado en el contenido real."""
    title_lower = node.title.lower()
    summary_lower = node.summary.lower() if node.summary else ""

    # CAMBIO: commits de git
    if node.source == 'git':
        if 'feat:' in title_lower or 'feat:' in summary_lower:
            return 'IDEA'  # Feature es una idea implementada
        elif 'fix:' in title_lower or 'fix:' in summary_lower:
            return 'CORRECCION'
        elif 'docs:' in title_lower or 'chore:' in title_lower:
            return 'CAMBIO'
        else:
            return 'CAMBIO'

    # RIESGO: complejidad, problemas
    if 'riesgo' in title_lower or 'complejidad' in title_lower:
        return 'RIESGO'

    # FUTURO: TODOs, pendientes
    if 'pendiente' in title_lower or 'todo' in title_lower:
        return 'FUTURO'

    # BASE: estructura del proyecto
    if 'proyecto' in title_lower and ('contiene' in title_lower or 'archivos' in title_lower):
        return 'BASE'

    # IDEA: todo lo demás
    return 'IDEA'


def estandarizar_nodo(node: Node) -> Node:
    """Estandariza un solo nodo."""
    return Node(
        id=node.id,
        type=corregir_tipo(node),
        title=node.title,
        summary=node.summary,
        tags=estandarizar_tags(node.tags),
        source=node.source,
        status=inferir_status(node),
        version=node.version,
        evidence=inferir_evidence(node) or node.evidence,
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def estandarizar_nodos(nodes: List[Node]) -> List[Node]:
    """Estandariza una lista de nodos."""
    return [estandarizar_nodo(n) for n in nodes]

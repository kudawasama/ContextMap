#!/usr/bin/env python3
"""
Script de estandarización de nodos del grafo de contexto.

Ejecutar con: python3 -m context_map.scripts.standardize
"""

import os
import sys
import re
import json
from collections import Counter
from typing import List, Dict, Set

# Agregar directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from context_map.core.store import load_jsonl, append_jsonl
from context_map.core.models import Node

# Definir STATE_DIR localmente
STATE_DIR = ".context-map/state"


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
    'smoke.py': 'tests',
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

# Mapeo de status según contexto
STATUS_MAP = {
    # Commits git = completado
    'git': 'completado',
    # TODOs = pendiente
    'scanner': 'pendiente',  # Por defecto
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


def save_jsonl(path: str, records: List[dict]) -> None:
    """Sobrescribe un JSONL completo (no append)."""
    _ensure_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _ensure_dir(path: str) -> None:
    """Crea directorios padres si no existen."""
    os.makedirs(os.path.dirname(path), exist_ok=True)


def estandarizar_nodos(nodes: List[Node]) -> List[Node]:
    """Estandariza todos los nodos del grafo."""
    nodos_estandarizados = []

    for node in nodes:
        # Crear copia
        n = Node(
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
        nodos_estandarizados.append(n)

    return nodos_estandarizados


def generar_reporte(original: List[Node], estandarizados: List[Node]) -> str:
    """Genera un reporte de los cambios realizados."""
    lineas = [
        "# Reporte de Estandarización",
        "",
        "## Resumen",
        f"- Nodos analizados: {len(original)}",
        f"- Nodos estandarizados: {len(estandarizados)}",
        "",
    ]

    # Cambios por tipo
    orig_tipos = Counter(n.type for n in original)
    est_tipos = Counter(n.type for n in estandarizados)
    lineas.append("### Cambios por Tipo")
    for tipo in set(list(orig_tipos.keys()) + list(est_tipos.keys())):
        orig = orig_tipos.get(tipo, 0)
        est = est_tipos.get(tipo, 0)
        diff = est - orig
        if diff != 0:
            lineas.append(f"- {tipo}: {orig} → {est} ({'+' if diff > 0 else ''}{diff})")
    lineas.append("")

    # Cambios por status
    orig_status = Counter(n.status for n in original)
    est_status = Counter(n.status for n in estandarizados)
    lineas.append("### Cambios por Status")
    for status in set(list(orig_status.keys()) + list(est_status.keys())):
        orig = orig_status.get(status, 0)
        est = est_status.get(status, 0)
        diff = est - orig
        if diff != 0:
            lineas.append(f"- {status}: {orig} → {est} ({'+' if diff > 0 else ''}{diff})")
    lineas.append("")

    # Tags eliminados
    orig_tags = set()
    for n in original:
        orig_tags.update(n.tags)
    est_tags = set()
    for n in estandarizados:
        est_tags.update(n.tags)

    tags_eliminados = orig_tags - est_tags
    tags_agregados = est_tags - orig_tags

    if tags_eliminados:
        lineas.append("### Tags Eliminados")
        for t in sorted(tags_eliminados):
            lineas.append(f"- `{t}`")
        lineas.append("")

    if tags_agregados:
        lineas.append("### Tags Agregados")
        for t in sorted(tags_agregados):
            lineas.append(f"- `{t}`")
        lineas.append("")

    return "\n".join(lineas)


def main():
    """Función principal."""
    print("=== Estandarización de Nodos ===")
    print()

    # Cargar nodos
    records = load_jsonl(os.path.join(STATE_DIR, "graph.jsonl"))
    if not records:
        print("No hay nodos para estandarizar.")
        return

    nodes = [Node.from_dict(r) for r in records]
    print(f"Nodos cargados: {len(nodes)}")

    # Estandarizar
    nodos_estandarizados = estandarizar_nodos(nodes)

    # Guardar
    save_jsonl(
        os.path.join(STATE_DIR, "graph.jsonl"),
        [n.to_dict() for n in nodos_estandarizados],
    )
    print(f"Nodos guardados: {len(nodos_estandarizados)}")

    # Generar reporte
    reporte = generar_reporte(nodes, nodos_estandarizados)
    reporte_path = os.path.join(STATE_DIR, "REPORTE_ESTANDARIZACION.md")
    with open(reporte_path, "w", encoding="utf-8") as f:
        f.write(reporte)
    print(f"Reporte generado: {reporte_path}")

    print()
    print("=== Listo ===")


if __name__ == "__main__":
    main()

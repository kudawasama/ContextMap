"""Generador de briefs para agentes de IA.

Genera un archivo CONTEXT.md con un resumen ejecutivo que cualquier
agente pueda leer en 30 segundos antes de trabajar en el proyecto.
"""

from __future__ import annotations

import os
from typing import List
from datetime import datetime

from context_map.core.models import Node, Edge


def generar_brief(
    project_name: str,
    nodes: List[Node],
    edges: List[Edge],
    readiness_score: int = 0,
    output_path: str = ".context-map/CONTEXT.md",
) -> str:
    """Genera un brief ejecutivo para agentes de IA.

    El brief debe ser:
    - Conciso (< 500 palabras)
    - Accionable (qué hacer, qué evitar)
    - Contextual (qué es, por qué existe)
    """
    # Estadísticas básicas
    stats = _calcular_stats(nodes)

    # Contenido del brief
    sections = [
        _header(project_name),
        _resumen_ejecutivo(project_name, stats, readiness_score),
        _estado_proyecto(stats),
        _riesgos_criticos(nodes),
        _tareas_pendientes(nodes),
        _estructura_recomendada(nodes),
        _comandos_utiles(),
        _footer(),
    ]

    brief = "\n\n".join(sections)

    # Escribir archivo
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    return brief


def _header(project_name: str) -> str:
    """Genera el header del brief."""
    return f"""# {project_name} — Brief para Agentes

> **Lee esto antes de trabajar en el proyecto.**
> Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def _resumen_ejecutivo(name: str, stats: dict, score: int) -> str:
    """Genera el resumen ejecutivo."""
    total = stats["total"]
    tipos = ", ".join(f"{k}: {v}" for k, v in stats["por_tipo"].items())

    return f"""## Resumen Ejecutivo

**Proyecto**: {name}
**Nodos totales**: {total}
**Distribución**: {tipos}
**Readiness**: {score}/100
"""


def _estado_proyecto(stats: dict) -> str:
    """Genera la sección de estado."""
    return f"""## Estado del Proyecto

- **Ideas**: {stats["por_tipo"].get("IDEA", 0)} (features, conceptos)
- **Bases**: {stats["por_tipo"].get("BASE", 0)} (fundamentos)
- **Riesgos**: {stats["por_tipo"].get("RIESGO", 0)} (problemas potenciales)
- **Cambios**: {stats["por_tipo"].get("CAMBIO", 0)} (modificaciones)
- **Pendientes**: {stats["por_tipo"].get("FUTURO", 0)} (tareas por hacer)
- **Correcciones**: {stats["por_tipo"].get("CORRECCION", 0)} (bugs/fixes)
"""


def _riesgos_criticos(nodes: List[Node]) -> str:
    """Genera la sección de riesgos."""
    riesgos = [n for n in nodes if n.type == "RIESGO"]

    if not riesgos:
        return "## Riesgos Críticos\n\nNo hay riesgos identificados. ✅"

    lines = ["## Riesgos Críticos\n"]
    for r in riesgos[:5]:  # Top 5
        lines.append(f"- ⚠️ **{r.title[:80]}**")
        if r.summary:
            lines.append(f"  {r.summary[:120]}")
    return "\n".join(lines)


def _tareas_pendientes(nodes: List[Node]) -> str:
    """Genera la sección de tareas pendientes."""
    futuros = [n for n in nodes if n.type == "FUTURO"]

    if not futuros:
        return "## Tareas Pendientes\n\nNo hay tareas pendientes. ✅"

    lines = ["## Tareas Pendientes\n"]
    for f in futuros[:5]:  # Top 5
        lines.append(f"- 📝 **{f.title[:80]}**")
    return "\n".join(lines)


def _estructura_recomendada(nodes: List[Node]) -> str:
    """Genera la sección de estructura."""
    return """## Estructura Recomendada

Al trabajar en este proyecto:
1. Lee el README para entender el propósito
2. Revisa los riesgos antes de hacer cambios
3. Ejecuta los tests antes de cada commit
4. Documenta las decisiones importantes
"""


def _comandos_utiles() -> str:
    """Genera la sección de comandos útiles."""
    return """## Comandos Útiles

```bash
# Verificar estado
ctxmap check .

# Generar contexto actualizado
ctxmap build --project "Nombre"

# Ver reporte semanal
ctxmap weekly
```
"""


def _footer() -> str:
    """Genera el footer."""
    return """---

> Este brief fue generado automáticamente por Context Map.
> Actualízalo ejecutando `ctxmap build --brief`.
"""


def _calcular_stats(nodes: List[Node]) -> dict:
    """Calcula estadísticas de los nodos."""
    stats = {"total": len(nodes), "por_tipo": {}}

    for n in nodes:
        stats["por_tipo"][n.type] = stats["por_tipo"].get(n.type, 0) + 1

    return stats

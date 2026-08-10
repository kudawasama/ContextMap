"""Generador de briefs para agentes de IA.

Construye un resumen ejecutivo en formato Markdown (`CONTEXT.md`) diseñado para que un agente
pueda comprender **qué es el proyecto, por qué existe, qué cumple**, sus riesgos y su estado
en menos de 30 segundos.

Regla de diseño: un brief puro de métricas NO sirve — el agente lo ignora. El brief debe
responder el PORQUÉ (alma del proyecto) y decirle al agente QUÉ HACER con el contexto
(leer el vault, trabajar y actualizar el mapa para mantenerlo vivo).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from context_map.core.models import Edge, Node


def generar_brief(
    project_name: str,
    nodes: list[Node],
    edges: list[Edge],
    readiness_score: int = 0,
    output_path: str = ".context-map/CONTEXT.md",
    project_dir: str = ".",
) -> str:
    """Genera el brief ejecutivo `CONTEXT.md` para los agentes de IA.

    Args:
        project_name (str): Nombre del proyecto.
        nodes (List[Node]): Nodos del mapa conceptual.
        edges (List[Edge]): Aristas del mapa conceptual.
        readiness_score (int): Score de readiness del proyecto.
        output_path (str): Ruta de salida para el archivo de brief.
        project_dir (str): Directorio raíz del proyecto (para leer README.md y el vault).

    Returns:
        str: Contenido Markdown del brief generado.
    """
    stats = _calcular_stats(nodes)
    proposito = _extraer_proposito(project_name, project_dir)

    sections = [
        _header(project_name),
        _que_es_y_por_que_existe(project_name, proposito),
        _resumen_ejecutivo(project_name, stats, readiness_score),
        _estado_proyecto(stats),
        _riesgos_criticos(nodes),
        _tareas_pendientes(nodes),
        _como_trabajar_aqui(project_name),
        _comandos_utiles(),
        _footer(),
    ]

    brief = "\n\n".join(sections)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(brief)

    return brief


def _extraer_proposito(project_name: str, project_dir: str) -> str:
    """Extrae el propósito del proyecto desde README.md (primer párrafo significativo).

    Args:
        project_name (str): Nombre del proyecto.
        project_dir (str): Directorio raíz del proyecto.

    Returns:
        str: Propósito del proyecto, o string vacío si no se pudo extraer.
    """
    try:
        from context_map.presentation.vault.consolidated.common import _extract_project_purpose

        return _extract_project_purpose(os.path.abspath(project_dir))
    except Exception:
        return ""


def _vault_nombre(project_name: str) -> str:
    """Nombre sanitizado de la carpeta del vault (mismo criterio que `vault_dir`)."""
    safe = project_name.strip().replace(" ", "-").replace("/", "-")
    return f"vault-{safe}"


def _header(project_name: str) -> str:
    """Encabezado del brief.

    Args:
        project_name (str): Nombre del proyecto.

    Returns:
        str: Encabezado en Markdown.
    """
    return f"""# {project_name} — Brief para Agentes

> **LEE esto ANTES de trabajar.** Este brief y el vault son la memoria viva del
> proyecto: qué es, por qué existe, qué cumple, qué está pendiente y qué riesgos tiene.
> Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def _que_es_y_por_que_existe(project_name: str, proposito: str) -> str:
    """Sección de identidad: qué es el proyecto, por qué existe y qué cumple.

    Args:
        project_name (str): Nombre del proyecto.
        proposito (str): Propósito extraído del README (o vacío).

    Returns:
        str: Sección en Markdown con el alma del proyecto.
    """
    if proposito:
        descripcion = f"**{project_name}**: {proposito}"
    else:
        descripcion = (
            f"**{project_name}**: consulta `README.md` y el vault "
            f"`.context-map/{_vault_nombre(project_name)}/1.0-PROPOSITO/` "
            "para conocer su identidad y propósito."
        )

    return f"""## ¿Qué es y por qué existe?

{descripcion}

Antes de tocar código, pregúntate y responde con el contexto del vault
(`1.0-PROPOSITO/1.1-Mapa-Mental-Narrativo.md` y `1.3-Proposito.md`):

- **¿Por qué existe este proyecto?** — qué problema resuelve.
- **¿Para qué sirve?** — qué valor entrega a quien lo usa.
- **¿Qué cumple?** — qué promesas y objetivos debe respetar (no romper).
"""


def _resumen_ejecutivo(name: str, stats: dict[str, Any], score: int) -> str:
    """Resumen ejecutivo principal.

    Args:
        name (str): Nombre del proyecto.
        stats (Dict[str, Any]): Estadísticas calculadas.
        score (int): Puntaje de readiness.

    Returns:
        str: Resumen ejecutivo.
    """
    total = stats["total"]
    tipos = ", ".join(f"{k}: {v}" for k, v in stats["por_tipo"].items())

    return f"""## Resumen Ejecutivo

**Proyecto**: {name}
**Nodos totales**: {total}
**Distribución**: {tipos}
**Readiness**: {score}/100
"""


def _estado_proyecto(stats: dict[str, Any]) -> str:
    """Sección de estado detallado del proyecto."""
    return f"""## Estado del Proyecto

- **Ideas**: {stats["por_tipo"].get("IDEA", 0)} (features, conceptos)
- **Bases**: {stats["por_tipo"].get("BASE", 0)} (fundamentos)
- **Riesgos**: {stats["por_tipo"].get("RIESGO", 0)} (problemas potenciales)
- **Cambios**: {stats["por_tipo"].get("CAMBIO", 0)} (modificaciones)
- **Pendientes**: {stats["por_tipo"].get("FUTURO", 0)} (tareas por hacer)
- **Correcciones**: {stats["por_tipo"].get("CORRECCION", 0)} (bugs/fixes)
"""


def _riesgos_criticos(nodes: list[Node]) -> str:
    """Sección de riesgos identificados."""
    riesgos = [n for n in nodes if n.type == "RIESGO"]

    if not riesgos:
        return "## Riesgos Críticos\n\nNo hay riesgos identificados. ✅"

    lines = ["## Riesgos Críticos\n"]
    for r in riesgos[:5]:
        titulo = r.title[:80].strip()
        lines.append(f"- ⚠️ **{titulo}**")
        # Evitar duplicar el título dentro del resumen
        if r.summary:
            resumen = r.summary.strip()
            if resumen != titulo and not resumen.startswith(titulo[:60]):
                lines.append(f"  {resumen[:120]}")
    return "\n".join(lines)


def _tareas_pendientes(nodes: list[Node]) -> str:
    """Sección de tareas y elementos futuros."""
    futuros = [n for n in nodes if n.type == "FUTURO"]

    if not futuros:
        return "## Tareas Pendientes\n\nNo hay tareas pendientes. ✅"

    lines = ["## Tareas Pendientes\n"]
    for f in futuros[:5]:
        lines.append(f"- 📝 **{f.title[:80]}**")
        if f.summary and f.summary != f.title:
            lines.append(f"  {f.summary[:120]}")
    return "\n".join(lines)


def _como_trabajar_aqui(project_name: str) -> str:
    """Sección de instrucciones para que el agente use y mantenga vivo el contexto.

    Args:
        project_name (str): Nombre del proyecto.

    Returns:
        str: Sección en Markdown con el protocolo de trabajo del agente.
    """
    vault = f".context-map/{_vault_nombre(project_name)}"

    return f"""## Cómo trabajar aquí — dale vida al contexto

Este proyecto se gobierna por su contexto. El agente DEBE:

1. **Leer este brief** y explorar el vault (`{vault}/`): propósito (1.0),
   ideas (2.0), riesgos (4.0) y backlog (5.0).
2. **Revisar los riesgos** antes de hacer cambios y **ejecutar los tests** antes de cada commit.
3. **Inspeccionar el código real** — no suponer rutas ni lógica.
4. **Mantener vivo el contexto**: después de implementar, actualizar el mapa para que
   refleje el trabajo realizado (`ctxmap scan .` + `ctxmap build --brief`).
   El contexto que no se actualiza muere y el siguiente agente queda ciego.
"""


def _comandos_utiles() -> str:
    """Sección de comandos esenciales del CLI."""
    return """## Comandos Útiles

```bash
# Verificar estado
ctxmap check .

# Escanear cambios y actualizar el mapa
ctxmap scan .

# Generar contexto actualizado (vault + brief)
ctxmap build --brief

# Ver reporte semanal
ctxmap weekly
```
"""


def _footer() -> str:
    """Pie de página del archivo."""
    return """---

> Este brief fue generado automáticamente por Context Map.
> Actualízalo ejecutando `ctxmap build --brief`.
"""


def _calcular_stats(nodes: list[Node]) -> dict[str, Any]:
    """Calcula estadísticas generales sobre los nodos.

    Args:
        nodes (List[Node]): Nodos.

    Returns:
        Dict[str, Any]: Estadísticas de conteo por tipo.
    """
    stats: dict[str, Any] = {"total": len(nodes), "por_tipo": {}}
    for n in nodes:
        stats["por_tipo"][n.type] = stats["por_tipo"].get(n.type, 0) + 1
    return stats

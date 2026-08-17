"""Submódulo de construcción de secciones Markdown para el brief de contexto."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from context_map.core.models import Node
from context_map.presentation.briefs.extractors import vault_nombre


def header(project_name: str) -> str:
    """Encabezado del brief."""
    return f"""# {project_name} — Brief para Agentes

> **LEE esto ANTES de trabajar.** Este brief y el vault son la memoria viva del
> proyecto: qué es, por qué existe, qué cumple, qué está pendiente y qué riesgos tiene.
> Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""


def que_es_y_por_que_existe(project_name: str, proposito: str) -> str:
    """Sección de identidad: qué es el proyecto, por qué existe y qué cumple."""
    if proposito:
        descripcion = f"**{project_name}**: {proposito}"
    else:
        descripcion = (
            f"**{project_name}**: consulta `README.md` y el vault "
            f"`.context-map/{vault_nombre(project_name)}/1.0-PROPOSITO/` "
            "para conocer su identidad y propósito."
        )

    return f"""## ¿Qué es y por qué existe?

{descripcion}

Antes de tocar código, pregúntate y responde con el contexto del vault
(`1.0-PROPOSITO/1.1-Mapa-Mental-Narrativo.md` y `1.3-Proposito.md`):

- **¿Por qué existe este proyecto?** — qué problema resuelve.
- **¿Para qué sirve?** — qué valor entrega a quien lo usa.
- **¿Qué cumple?** — qué promesas y objetivos debe respetar (no romper).
- **¿Para quién es?** — usuarios y stakeholders (completar con la historia).
- **¿Qué NO es?** — límites y fuera de alcance (lo que el proyecto NO hace).
- **¿Qué NO tocar?** — reglas inamovibles del proyecto.

> Si una casilla está "pendiente de contexto", complétala con la historia real
> (conversaciones, README, decisiones) en una nota protegida de
> `7.0-MANUAL/` (p. ej. `GOBIERNO.md`) — el build jamás la borra y el agente
> la lee en cada actualización.

"""


def resumen_ejecutivo(name: str, stats: dict[str, Any], score: int, version: str = "") -> str:
    """Resumen ejecutivo principal."""
    total = stats["total"]
    tipos = ", ".join(f"{k}: {v}" for k, v in stats["por_tipo"].items())
    version_line = f"\n**Versión**: {version}" if version else ""

    return f"""## Resumen Ejecutivo

**Proyecto**: {name}
**Nodos totales**: {total}
**Distribución**: {tipos}
**Readiness**: {score}/100{version_line}
"""


def estado_proyecto(stats: dict[str, Any]) -> str:
    """Sección de estado detallado del proyecto."""
    return f"""## Estado del Proyecto

- **Ideas**: {stats["por_tipo"].get("IDEA", 0)} (features, conceptos)
- **Bases**: {stats["por_tipo"].get("BASE", 0)} (fundamentos)
- **Riesgos**: {stats["por_tipo"].get("RIESGO", 0)} (problemas potenciales)
- **Cambios**: {stats["por_tipo"].get("CAMBIO", 0)} (modificaciones)
- **Pendientes**: {stats["por_tipo"].get("FUTURO", 0)} (tareas por hacer)
- **Correcciones**: {stats["por_tipo"].get("CORRECCION", 0)} (bugs/fixes)
"""


def aviso_frescura(frescura: str) -> str:
    """Sección que avisa si el contexto está desactualizado (o confirma que está al día)."""
    if not frescura:
        return "## Estado del Contexto\n\n✅ Contexto al día (último build).\n"
    return f"## Estado del Contexto\n\n⚠️ **{frescura}**\n"


def riesgos_criticos(nodes: list[Node]) -> str:
    """Sección de riesgos identificados."""
    riesgos = [n for n in nodes if n.type == "RIESGO"]

    if not riesgos:
        return "## Riesgos Críticos\n\nNo hay riesgos identificados. ✅"

    lines = ["## Riesgos Críticos\n"]
    for r in riesgos[:5]:
        titulo = r.title[:80].strip()
        lines.append(f"- ⚠️ **{titulo}**")
        if r.summary:
            resumen = r.summary.strip()
            if resumen != titulo and not resumen.startswith(titulo[:60]):
                lines.append(f"  {resumen[:120]}")
    return "\n".join(lines)


def tareas_pendientes(nodes: list[Node], pendientes_manuales: list[str] | None = None) -> str:
    """Sección de tareas y elementos futuros."""
    futuros = [n for n in nodes if n.type == "FUTURO"]
    from context_map.presentation.vault.consolidated.secciones_backlog import _es_todo_codigo

    futuros = [n for n in futuros if not _es_todo_codigo(n)]
    manuales = pendientes_manuales or []

    if not futuros and not manuales:
        return "## Tareas Pendientes\n\nNo hay tareas pendientes. ✅"

    lines = ["## Tareas Pendientes\n"]

    if manuales:
        lines.append("### 📋 Pendientes del proyecto (backlog manual)")
        lines.append("")
        for titulo in manuales:
            lines.append(f"- {titulo}")
        lines.append("")
        lines.append("> Fuente: `7.0-MANUAL/BACKLOG.md` (pendientes conversados, con criterios de listo).")
        lines.append("")

    if futuros:
        lines.append("### 🔧 TODOs del código (deuda técnica)")
        lines.append("")
        for f in futuros[:5]:
            lines.append(f"- 📝 **{f.title[:80]}**")
            if f.summary and f.summary != f.title:
                lines.append(f"  {f.summary[:120]}")
    return "\n".join(lines)


def como_trabajar_aqui(project_name: str) -> str:
    """Sección de instrucciones para que el agente use y mantenga vivo el contexto."""
    vault = f".context-map/{vault_nombre(project_name)}"

    return f"""## Cómo trabajar aquí — dale vida al contexto

Este proyecto se gobierna por su contexto. El agente DEBE:

1. **Leer este brief** y explorar el vault (`{vault}/`): propósito (1.0),
   ideas (2.0), riesgos (4.0) y backlog (5.0).
2. **Revisar los riesgos** antes de hacer cambios y **ejecutar los tests** antes de cada commit.
3. **Inspeccionar el código real** — no suponer rutas ni lógica.
4. **Importar la historia del proyecto** (chats y conversaciones con el usuario).
5. **Mantener vivo el contexto**: después de implementar, actualizar el mapa
   (`ctxmap refresh .`) y **verificar el resultado** — el script propone, el
   agente dispone: si quedaron títulos crudos, métricas en este brief, plantillas
   vacías o notas sin alma, corregirlas (notas con alma en `7.0-MANUAL/`).
   El contexto que no se actualiza muere y el siguiente agente queda ciego.

> Comandos exactos, criterios de verificación y metodología para escribir notas
> con alma: `.context-map/contextmap-skill.md`
"""


def comandos_utiles() -> str:
    """Sección de comandos esenciales del CLI (solo la referencia; detalle en la skill)."""
    return """## Comandos Útiles

```bash
# Actualizar el contexto en 1 paso (scan + build preservando manuales + check)
ctxmap refresh .
```

> Lista completa de comandos y metodología de escritura: `.context-map/contextmap-skill.md`
"""


def footer() -> str:
    """Pie de página del archivo."""
    return """---

> Este brief fue generado automáticamente por Context Map.
> Actualízalo ejecutando `ctxmap build --brief`.
"""

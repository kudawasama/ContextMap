"""Generador de briefs para agentes de IA.

Construye un resumen ejecutivo en formato Markdown (`CONTEXT.md`) diseñado para que un agente
pueda comprender **qué es el proyecto, por qué existe, qué cumple**, sus riesgos y su estado
en menos de 30 segundos.

Regla de diseño: un brief puro de métricas NO sirve — el agente lo ignora. El brief debe
responder el PORQUÉ (alma del proyecto) y decirle al agente QUÉ HACER con el contexto
(leer el vault, trabajar y actualizar el mapa para mantenerlo vivo).
"""

from __future__ import annotations

import json
import os
import re
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
    version = _detectar_version(project_dir)
    pendientes_manuales = _extraer_pendientes_manuales(project_name, project_dir)
    frescura = _chequear_frescura(project_name, project_dir)

    sections = [
        _header(project_name),
        _que_es_y_por_que_existe(project_name, proposito),
        _resumen_ejecutivo(project_name, stats, readiness_score, version),
        _estado_proyecto(stats),
        _aviso_frescura(frescura),
        _riesgos_criticos(nodes),
        _tareas_pendientes(nodes, pendientes_manuales),
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
    """Extrae el propósito del proyecto desde README.md (biblia: tagline + ¿Qué es?).

    Args:
        project_name (str): Nombre del proyecto.
        project_dir (str): Directorio raíz del proyecto.

    Returns:
        str: Propósito del proyecto, o string vacío si no se pudo extraer.
    """
    try:
        from context_map.presentation.vault.consolidated.common import (
            _extract_proposito_biblia,
        )

        return _extract_proposito_biblia(os.path.abspath(project_dir))
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
- **¿Para quién es?** — usuarios y stakeholders (completar con la historia).
- **¿Qué NO es?** — límites y fuera de alcance (lo que el proyecto NO hace).
- **¿Qué NO tocar?** — reglas inamovibles del proyecto.

> Si una casilla está "pendiente de contexto", complétala con la historia real
> (conversaciones, README, decisiones) en una nota protegida de
> `7.0-MANUAL/` (p. ej. `GOBIERNO.md`) — el build jamás la borra y el agente
> la lee en cada actualización.

"""


def _detectar_version(project_dir: str) -> str:
    """Detecta la versión actual del proyecto (pyproject.toml / package.json / git describe).

    Args:
        project_dir (str): Directorio raíz del proyecto.

    Returns:
        str: Versión detectada, o string vacío si no se pudo determinar.
    """
    try:
        pyproject = os.path.join(project_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            with open(pyproject, encoding="utf-8") as f:
                m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', f.read(), re.MULTILINE)
            if m:
                return m.group(1)

        package_json = os.path.join(project_dir, "package.json")
        if os.path.exists(package_json):
            with open(package_json, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("version"):
                return str(data["version"])
    except Exception:
        pass
    return ""


def _extraer_pendientes_manuales(project_name: str, project_dir: str) -> list[str]:
    """Extrae los pendientes REALES del backlog manual (7.0-MANUAL/BACKLOG.md si existe).

    El backlog generado (5.0-BACKLOG) solo lista TODOs del código. Los pendientes
    conversados con el usuario viven en la nota protegida ``7.0-MANUAL/BACKLOG.md``;
    el brief debe reflejarlos o el agente cree que no hay nada pendiente.

    Args:
        project_name (str): Nombre del proyecto (para resolver el vault).
        project_dir (str): Directorio raíz del proyecto.

    Returns:
        List[str]: Líneas con los pendientes manuales (títulos de sección + criterio).
    """
    vault = os.path.join(project_dir, ".context-map", _vault_nombre(project_name))
    backlog = os.path.join(vault, "7.0-MANUAL", "BACKLOG.md")
    if not os.path.exists(backlog):
        return []

    try:
        with open(backlog, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    pendientes: list[str] = []
    en_pendientes = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            titulo = stripped.lower()
            en_pendientes = "pendiente" in titulo or "tareas" in titulo or "por hacer" in titulo
            continue
        if not en_pendientes:
            continue
        # Sección "NO hacer" o "HECHO" corta la lista de pendientes
        if stripped.startswith("### ") or stripped.startswith("## "):
            if stripped.startswith("### "):
                titulo = stripped[4:].strip()
                # Quitar numeración "1." / "1)" y negritas
                titulo = re.sub(r"^\d+[.)]\s*", "", titulo)
                titulo = titulo.strip("*").strip()
                if titulo and len(pendientes) < 10:
                    pendientes.append(titulo)
            continue
    return pendientes


def _chequear_frescura(project_name: str, project_dir: str) -> str:
    """Compara la fecha del último build vs el diario manual más reciente.

    Si el diario (memoria viva, escrito por el agente) es MÁS NUEVO que el último
    ``ctxmap build``, el brief está desactualizado y el agente debe refrescar
    ANTES de responder — evita el error de responder con un contexto viejo.

    Args:
        project_name (str): Nombre del proyecto.
        project_dir (str): Directorio raíz del proyecto.

    Returns:
        str: Mensaje de aviso, o string vacío si el contexto está al día.
    """
    try:
        state = os.path.join(project_dir, ".context-map", "state", "last_build.json")
        if not os.path.exists(state):
            return ""
        with open(state, encoding="utf-8") as f:
            info = json.load(f)
        build_ts = info.get("timestamp", "")
        if not build_ts:
            return ""

        # Buscar el diario manual más reciente
        vault = os.path.join(project_dir, ".context-map", _vault_nombre(project_name))
        diario_dir = os.path.join(vault, "7.0-MANUAL", "Diario")
        if not os.path.isdir(diario_dir):
            return ""

        diarios = sorted(
            (d for d in os.listdir(diario_dir) if d.endswith(".md")),
            reverse=True,
        )
        if not diarios:
            return ""

        diario_fecha = diarios[0].replace(".md", "")
        try:
            build_dt = datetime.fromisoformat(build_ts).date()
            diario_dt = datetime.strptime(diario_fecha, "%Y-%m-%d").date()
        except ValueError:
            return ""

        if diario_dt > build_dt:
            return (
                f"El diario manual ({diario_fecha}) es MÁS NUEVO que este brief "
                f"(build {build_dt.isoformat()}). El contexto puede estar desactualizado: "
                f"ejecuta `ctxmap refresh .` ANTES de responder sobre el estado del proyecto."
            )
    except Exception:
        return ""
    return ""


def _aviso_frescura(frescura: str) -> str:
    """Sección que avisa si el contexto está desactualizado (o confirma que está al día)."""
    if not frescura:
        return "## Estado del Contexto\n\n✅ Contexto al día (último build).\n"
    return f"## Estado del Contexto\n\n⚠️ **{frescura}**\n"


def _resumen_ejecutivo(name: str, stats: dict[str, Any], score: int, version: str = "") -> str:
    """Resumen ejecutivo principal.

    Args:
        name (str): Nombre del proyecto.
        stats (Dict[str, Any]): Estadísticas calculadas.
        score (int): Puntaje de readiness.
        version (str): Versión detectada del proyecto (opcional).

    Returns:
        str: Resumen ejecutivo.
    """
    total = stats["total"]
    tipos = ", ".join(f"{k}: {v}" for k, v in stats["por_tipo"].items())
    version_line = f"\n**Versión**: {version}" if version else ""

    return f"""## Resumen Ejecutivo

**Proyecto**: {name}
**Nodos totales**: {total}
**Distribución**: {tipos}
**Readiness**: {score}/100{version_line}
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


def _tareas_pendientes(nodes: list[Node], pendientes_manuales: list[str] | None = None) -> str:
    """Sección de tareas y elementos futuros.

    Combina los TODOs detectados en el código (nodos FUTURO) con los pendientes
    REALES del backlog manual (7.0-MANUAL/BACKLOG.md) — que son los que el agente
    debe reflejar para no responder "no hay nada pendiente" cuando sí lo hay.

    Args:
        nodes (List[Node]): Nodos del mapa.
        pendientes_manuales (Optional[List[str]]): Pendientes del backlog manual.

    Returns:
        str: Sección de tareas pendientes en Markdown.
    """
    futuros = [n for n in nodes if n.type == "FUTURO"]
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
4. **Importar la historia del proyecto** (chats y conversaciones con el usuario).
5. **Mantener vivo el contexto**: después de implementar, actualizar el mapa
   (`ctxmap refresh .`) y **verificar el resultado** — el script propone, el
   agente dispone: si quedaron títulos crudos, métricas en este brief, plantillas
   vacías o notas sin alma, corregirlas (notas con alma en `7.0-MANUAL/`).
   El contexto que no se actualiza muere y el siguiente agente queda ciego.

> Comandos exactos, criterios de verificación y metodología para escribir notas
> con alma: `.context-map/contextmap-skill.md`
"""


def _comandos_utiles() -> str:
    """Sección de comandos esenciales del CLI (solo la referencia; detalle en la skill)."""
    return """## Comandos Útiles

```bash
# Actualizar el contexto en 1 paso (scan + build preservando manuales + check)
ctxmap refresh .
```

> Lista completa de comandos y metodología de escritura: `.context-map/contextmap-skill.md`
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

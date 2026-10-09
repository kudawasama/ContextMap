"""Brief **mínimo** por capas (P1.2 del plan de revisión 2026-10-08).

El brief completo pesa ~1.600 tokens y lo lee el agente en cada sesión. La capa
mínima conserva la **identidad** (qué es y por qué existe), el **estado** y los
**títulos** de riesgos y pendientes, y explica **cómo ampliar** con
``ctxmap search`` / la tool MCP ``context_search``. Se escribe junto al completo
(``CONTEXT.min.md``) para que el agente pueda elegir la capa según su presupuesto
de tokens, sin perder nada: el detalle sigue a un comando de distancia.
"""

from __future__ import annotations

import os
from typing import Any

from context_map.core.models import Node
from context_map.presentation.briefs.extractors import (
    calcular_stats,
    chequear_frescura,
    detectar_version,
    extraer_pendientes_manuales,
    extraer_proposito,
    panorama_conocimiento,
)
from context_map.presentation.briefs.sections import (
    aviso_frescura,
    estado_proyecto,
    footer,
    header,
    que_es_y_por_que_existe,
    resumen_ejecutivo,
)

LIMITE_ALMA = 480
LIMITE_TITULOS = 3
LIMITE_TITULO = 72


def _recortar(texto: str, limite: int) -> str:
    """Recorta un texto en el último salto de línea o frase antes del límite."""
    if len(texto) <= limite:
        return texto
    trozo = texto[:limite]
    corte = max(trozo.rfind("\n"), trozo.rfind(". "))
    if corte > limite // 2:
        trozo = trozo[:corte + 1]
    return trozo.rstrip() + " […]"


def _titulos(nodes: list[Node], tipo: str, limite: int = LIMITE_TITULOS) -> tuple[list[str], int]:
    """Títulos (recortados) de los nodos de un tipo y cuántos hay en total."""
    titulos = []
    for n in nodes:
        if (n.type or "").upper() != tipo or not n.title:
            continue
        titulo = n.title.strip()
        titulos.append(titulo if len(titulo) <= LIMITE_TITULO else titulo[:LIMITE_TITULO].rstrip() + "…")
    return titulos[:limite], len(titulos)


def como_ampliar_contexto() -> str:
    """Sección compacta que enseña al agente a pedir más contexto.

    Returns:
        str: Bloque Markdown breve con los comandos y rutas de ampliación.
    """
    return "\n".join([
        "## 🔎 Ampliar contexto",
        "",
        '- `ctxmap search "<tema>"` / tool MCP `context_search` → pasajes de nodos y',
        "  notas con citas (sin cargar ficheros completos).",
        "- Al volver a una sesión: `context_diff(since=<digest>)` → **solo lo que cambió**",
        "  (evita releer el brief si nada cambió).",
        "- Pendientes: `7.0-MANUAL/BACKLOG.md` · historia: `7.0-MANUAL/Diario/` · lecciones: `8.0-KNOWLEDGE/`.",
        "- Salud: `ctxmap check .` · peso: `ctxmap doctor --sizes` · vault: `.context-map/vault-*/`.",
    ])


def generar_brief_minimo(
    project_name: str,
    nodes: list[Node],
    readiness_score: int = 0,
    output_path: str = ".context-map/CONTEXT.min.md",
    project_dir: str = ".",
) -> str:
    """Genera la capa mínima del brief (``CONTEXT.min.md``).

    Args:
        project_name (str): Nombre del proyecto.
        nodes (list[Node]): Nodos del mapa conceptual.
        readiness_score (int): Score de readiness del proyecto.
        output_path (str): Ruta de salida del brief mínimo.
        project_dir (str): Raíz del proyecto (para leer propósito, frescura y PKM).

    Returns:
        str: Contenido Markdown del brief mínimo.
    """
    stats = calcular_stats(nodes)
    proposito = extraer_proposito(project_name, project_dir)
    frescura = chequear_frescura(project_name, project_dir)
    version = detectar_version(project_dir)
    pendientes_manuales = extraer_pendientes_manuales(project_name, project_dir)
    panorama = panorama_conocimiento(project_name, project_dir, limite=2)

    riesgos, total_riesgos = _titulos(nodes, "RIESGO")
    futuros, total_futuros = _titulos(nodes, "FUTURO")

    secciones: list[str] = [
        header(project_name),
        _recortar(que_es_y_por_que_existe(project_name, proposito), LIMITE_ALMA),
        resumen_ejecutivo(project_name, stats, readiness_score, version),
        estado_proyecto(stats),
        aviso_frescura(frescura),
    ]

    if riesgos:
        lineas = ["## ⚠️ Riesgos", ""]
        lineas += [f"- {t}" for t in riesgos]
        if total_riesgos > len(riesgos):
            lineas.append(f"_(+{total_riesgos - len(riesgos)} más en `4.0-RIESGOS/`)_")
        secciones.append("\n".join(lineas))

    if futuros or pendientes_manuales:
        lineas = ["## 📝 Pendientes", ""]
        lineas += [f"- {t}" for t in futuros]
        resto = total_futuros - len(futuros)
        if pendientes_manuales:
            lineas.append(f"_(+backlog manual: {len(pendientes_manuales)} en `7.0-MANUAL/BACKLOG.md`)_")
        elif resto > 0:
            lineas.append(f"_(+{resto} más en `5.0-BACKLOG/5.1-Tareas.md`)_")
        secciones.append("\n".join(lineas))

    paginas = panorama.get("paginas") or []
    if paginas:
        enlaces = " · ".join(str(p.get("cita") or p.get("titulo", "")) for p in paginas)
        secciones.append(f"## 🧠 Second Brain\n\n{enlaces}")

    secciones.append(como_ampliar_contexto())
    secciones.append(footer())

    texto = "\n\n".join(s for s in secciones if s)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(texto)
    return texto


def medir_brief(project_dir: str = ".") -> dict[str, Any]:
    """Compara el tamaño (tokens) del brief completo y el mínimo.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        dict[str, Any]: ``completo_tokens``, ``minimo_tokens``, ``ahorro_pct`` y
        las rutas de cada capa (0 si no existen).
    """
    from context_map.core.tokenization import TokenCounter

    counter = TokenCounter()
    base = os.path.join(project_dir, ".context-map")
    rutas = {"completo": os.path.join(base, "CONTEXT.md"), "minimo": os.path.join(base, "CONTEXT.min.md")}
    tamaños: dict[str, int] = {}
    for clave, ruta in rutas.items():
        if os.path.isfile(ruta):
            with open(ruta, encoding="utf-8") as f:
                tamaños[clave] = counter.count_tokens(f.read())
        else:
            tamaños[clave] = 0
    completo = tamaños.get("completo", 0) or 0
    minimo = tamaños.get("minimo", 0) or 0
    ahorro = round(100 * (1 - minimo / completo), 1) if completo and minimo else 0.0
    return {
        "completo_tokens": completo,
        "minimo_tokens": minimo,
        "ahorro_pct": ahorro,
        "completo": rutas["completo"],
        "minimo": rutas["minimo"],
    }

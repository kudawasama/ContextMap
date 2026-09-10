"""Estilo visual del vault de Obsidian: grupos de color del Graph View
(``.obsidian/graph.json``) y el snippet CSS de etiquetas coloreadas.
"""

from __future__ import annotations

import json
import os

from context_map.presentation.vault.consolidated.dominios import _leer_dominios

_COLORES_GRAFO: dict[str, str] = {
    "riesgo": "#ef4444",      # Rojo advertencia
    "idea": "#eab308",        # Ámbar idea
    "documento": "#0ea5e9",   # Celeste documento
    "base": "#94a3b8",        # Gris arquitectura
    "cambio": "#f97316",      # Naranja modificación
    "manual": "#14b8a6",      # Teal memoria viva
}

_PATH_GRAFO: dict[str, str] = {
    "1.0-PROPOSITO": "#0ea5e9",
    "2.0-IDEAS": "#eab308",
    "3.0-ESTRUCTURA": "#8b5cf6",
    "4.0-RIESGOS": "#ef4444",
    "5.0-BACKLOG": "#d97706",
    "6.0-HISTORIAL": "#f59e0b",
    "7.0-MANUAL": "#14b8a6",
    "8.0-KNOWLEDGE": "#10b981",
}


def generar_color_groups(vault_dir: str) -> str | None:
    """Genera los GRUPOS DE COLOR del grafo (graph view) en graph.json.

    Añade ``colorGroups`` a ``.obsidian/graph.json``: un grupo por etiqueta
    (tag:#riesgo en rojo, tag:#ideas en ámbar...), por estado, por concepto
    (DEVOPS/UI/ETL...) y por sección (path:4.0-RIESGOS...). Obsidian colorea
    los NODOS del grafo según estos filtros — funciona con el frontmatter
    (no depende de etiquetas inline).

    Args:
        vault_dir (str): Directorio del vault.

    Returns:
        str | None: Ruta de graph.json o None si falló.
    """
    obsidian_dir = os.path.join(vault_dir, ".obsidian")
    os.makedirs(obsidian_dir, exist_ok=True)
    graph_path = os.path.join(obsidian_dir, "graph.json")

    graph: dict = {}
    if os.path.exists(graph_path):
        try:
            with open(graph_path, encoding="utf-8") as f:
                graph = json.load(f)
        except Exception:
            graph = {}

    def _rgb(hex_color: str) -> int:
        return int(hex_color.lstrip("#"), 16)

    nuevos: list[dict] = []
    for etiqueta, color in sorted(_COLORES_GRAFO.items()):
        nuevos.append({
            "query": f"tag:#{etiqueta}",
            "color": {"a": 1, "rgb": _rgb(color)},
        })
    for ruta, color in sorted(_PATH_GRAFO.items()):
        nuevos.append({
            "query": f"path:{ruta}",
            "color": {"a": 1, "rgb": _rgb(color)},
        })

    # Grupos de DOMINIO (los grupos reales del contexto, desde dominios.yaml)
    paleta_dominios = [
        "#f43f5e", "#8b5cf6", "#059669", "#2563eb", "#06b6d4",
        "#0ea5e9", "#14b8a6", "#d946ef", "#f59e0b", "#10b981",
    ]
    cwd_proyecto = os.path.dirname(os.path.dirname(vault_dir))
    for i, dominio in enumerate(sorted(_leer_dominios(cwd_proyecto).keys())):
        nuevos.append({
            "query": f"tag:#grupo-{dominio}",
            "color": {"a": 1, "rgb": _rgb(paleta_dominios[i % len(paleta_dominios)])},
        })

    # Reemplazar los colorGroups (los nuestros cubren tags y paths completos)
    graph["colorGroups"] = nuevos
    graph.setdefault("collapse-filter", False)
    graph.setdefault("showTags", True)
    graph.setdefault("showAttachments", False)
    graph.setdefault("hideUnresolved", False)
    graph.setdefault("showOrphans", True)
    graph.setdefault("collapse-color-groups", False)

    with open(graph_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)

    return graph_path


_COLORES_ETIQUETAS: dict[str, tuple[str, str]] = {
    # (fondo, texto) — contraste legible sobre tema oscuro de Obsidian
    "ideas": ("#0e7490", "#ffffff"),
    "pendiente": ("#b45309", "#ffffff"),
    "activo": ("#1d4ed8", "#ffffff"),
    "completado": ("#15803d", "#ffffff"),
    "riesgo": ("#b91c1c", "#ffffff"),
    "cambio": ("#c2410c", "#ffffff"),
    "correccion": ("#c2410c", "#ffffff"),
    "base": ("#475569", "#ffffff"),
    "prueba": ("#475569", "#ffffff"),
    "futuro": ("#6d28d9", "#ffffff"),
    "DEVOPS": ("#4338ca", "#ffffff"),
    "UI": ("#be185d", "#ffffff"),
    "ETL": ("#0e7490", "#ffffff"),
    "TESTING": ("#15803d", "#ffffff"),
    "TUI": ("#7c3aed", "#ffffff"),
    "GENERAL": ("#475569", "#ffffff"),
    "BASEDEDATOS": ("#0891b2", "#ffffff"),
    "manual": ("#0f766e", "#ffffff"),
    "historia": ("#a16207", "#ffffff"),
    "backlog": ("#92400e", "#ffffff"),
    "indice": ("#334155", "#ffffff"),
    "mejora": ("#15803d", "#ffffff"),
    "mapa-mental": ("#1d4ed8", "#ffffff"),
    "gobierno": ("#065f46", "#ffffff"),
    "mcp": ("#1e40af", "#ffffff"),
    "sesiones": ("#6d28d9", "#ffffff"),
    "importador": ("#0e7490", "#ffffff"),
}


def generar_snippet_etiquetas(vault_dir: str) -> str | None:
    """Genera el snippet CSS que colorea las etiquetas por contexto.

    Escribe ``.obsidian/snippets/colored-tags.css`` dentro del vault y lo
    activa en ``.obsidian/appearance.json`` (enabledCssSnippets). Cada
    etiqueta (type, status, concept) tiene su color: ideas en teal,
    riesgo en rojo, DEVOPS en índigo, etc. Aplica a etiquetas inline
    (modo lectura y live preview).

    Args:
        vault_dir (str): Directorio del vault.

    Returns:
        str | None: Ruta del snippet generado, o None si no se pudo.
    """
    obsidian_dir = os.path.join(vault_dir, ".obsidian")
    snippets_dir = os.path.join(obsidian_dir, "snippets")
    os.makedirs(snippets_dir, exist_ok=True)

    partes = [
        "/* ContextMap — etiquetas por contexto (autogenerado) */",
        "/* Cada etiqueta con su color: ideas=teal, riesgo=rojo, DEVOPS=índigo... */",
        "",
    ]
    for etiqueta, (fondo, texto) in sorted(_COLORES_ETIQUETAS.items()):
        partes.append(
            f'.tag[href="#{etiqueta}"], .cm-hashtag[href="#{etiqueta}"] '
            f'{{ background-color: {fondo}; color: {texto}; }}'
        )
    partes.append(
        '.tag, .cm-hashtag { border-radius: 6px; padding: 0 6px; '
        'font-weight: 500; }'
    )
    css = "\n".join(partes) + "\n"

    css_path = os.path.join(snippets_dir, "colored-tags.css")
    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)

    # Activar el snippet en appearance.json (sin romper el resto)
    appearance_path = os.path.join(obsidian_dir, "appearance.json")

    appearance: dict = {}
    if os.path.exists(appearance_path):
        try:
            with open(appearance_path, encoding="utf-8") as f:
                appearance = json.load(f)
        except Exception:
            appearance = {}
    habilitados = appearance.get("enabledCssSnippets", [])
    if isinstance(habilitados, list) and "colored-tags" not in habilitados:
        habilitados.append("colored-tags")
        appearance["enabledCssSnippets"] = habilitados
        with open(appearance_path, "w", encoding="utf-8") as f:
            json.dump(appearance, f, ensure_ascii=False, indent=2)

    return css_path

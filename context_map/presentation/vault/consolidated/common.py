"""Utilidades compartidas para el renderizado de vaults consolidados y jerárquicos.

Centraliza helpers de propósito común: clasificación de nodos por tipo,
extracción del propósito del proyecto desde README y escritura de archivos
Markdown con codificación UTF-8.
"""

from __future__ import annotations

import logging
import os

from context_map.core.models import Edge, Node

logger = logging.getLogger(__name__)


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
    import json

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


_DOMINIOS_CACHE: dict[str, dict[str, list[str]]] = {}


def _parsear_dominios_simple(texto: str) -> dict[str, list[str]]:
    """Parser mínimo del formato de dominios.yaml (sin depender de pyyaml).

    Soporta el subconjunto que usamos: ``nombre:`` seguido de líneas
    ``  - palabra clave``. Comentarios (#) y ``---`` se ignoran.
    """
    dominios: dict[str, list[str]] = {}
    nombre_actual: str | None = None
    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or limpia.startswith("---"):
            continue
        if limpia.endswith(":") and not limpia.startswith("-"):
            nombre_actual = limpia[:-1].strip()
            dominios[nombre_actual] = []
        elif limpia.startswith("- ") and nombre_actual:
            valor = limpia[2:].strip().strip('"').strip("'")
            if valor:
                dominios[nombre_actual].append(valor)
    return {k: v for k, v in dominios.items() if v}


def _leer_dominios(cwd: str | None = None) -> dict[str, list[str]]:
    """Lee los dominios temáticos del proyecto desde ``.context-map/dominios.yaml``.

    Cada dominio define palabras clave; una nota se etiqueta con
    ``grupo-<dominio>`` cuando su título/resumen las menciona. Son los
    GRUPOS REALES del contexto (configurables por proyecto).

    Args:
        cwd (str | None): Directorio del proyecto (default: os.getcwd()).

    Returns:
        dict[str, list[str]]: Mapeo dominio -> palabras clave.
    """
    base = cwd or os.getcwd()
    ruta = os.path.join(base, ".context-map", "dominios.yaml")
    if ruta in _DOMINIOS_CACHE:
        return _DOMINIOS_CACHE[ruta]
    dominios: dict[str, list[str]] = {}
    try:
        if os.path.isfile(ruta):
            with open(ruta, encoding="utf-8") as f:
                texto = f.read()
            try:
                import yaml  # noqa: PLC0415 — opcional; fallback si no está

                datos = yaml.safe_load(texto) or {}
                for nombre, claves in datos.items():
                    if isinstance(claves, list):
                        dominios[str(nombre)] = [str(c).lower() for c in claves]
            except ImportError:
                # El entorno del binario (uv tool) puede no tener pyyaml:
                # usamos el parser mínimo del formato.
                for nombre, claves in _parsear_dominios_simple(texto).items():
                    dominios[nombre] = [c.lower() for c in claves]
    except Exception as err:  # noqa: BLE001 — los dominios son opcionales
        logger.debug("dominios.yaml no legible: %s", err)
    _DOMINIOS_CACHE[ruta] = dominios
    return dominios


def _tags_dominio(n: Node, cwd: str | None = None) -> list[str]:
    """Devuelve los tags ``grupo-<dominio>`` que aplican al nodo.

    Args:
        n (Node): Nodo del mapa.
        cwd (str | None): Directorio del proyecto.

    Returns:
        list[str]: Etiquetas de dominio (ej. ``grupo-humanizacion``).
    """
    texto = f"{n.title or ''} {n.summary or ''}".lower()
    if not texto.strip():
        return []
    resultado: list[str] = []
    for nombre, claves in _leer_dominios(cwd).items():
        if any(c in texto for c in claves):
            resultado.append(f"grupo-{nombre}")
    return resultado


def _linea_tags_inline(n: Node, cwd: str | None = None) -> str:
    """Línea de etiquetas inline coloreadas para poner bajo el título de una nota.

    Devuelve algo como ``> #ideas #pendiente #DEVOPS`` (se pinta con el
    snippet CSS ``colored-tags``). Vacío si el nodo no tiene etiquetas útiles.

    Args:
        n (Node): Nodo del mapa.

    Returns:
        str: Línea de etiquetas o string vacío.
    """
    mapa_tipo = {
        "IDEA": "ideas",
        "RIESGO": "riesgo",
        "CAMBIO": "cambio",
        "CORRECCION": "correccion",
        "BASE": "base",
        "PRUEBA": "prueba",
        "FUTURO": "futuro",
    }
    etiquetas: list[str] = []
    tipo = getattr(n, "type", "") or ""
    estado = getattr(n, "status", "") or ""
    concepto = getattr(n, "concept", "") or ""

    if tipo in mapa_tipo:
        etiquetas.append(mapa_tipo[tipo])
    if estado in ("pendiente", "activo", "completado"):
        etiquetas.append(estado)
    if concepto:
        etiquetas.append(concepto)
    # Tags de dominio (grupos REALES del contexto, de dominios.yaml)
    etiquetas.extend(_tags_dominio(n, cwd))
    if not etiquetas:
        return ""
    return "> " + " ".join(f"#{e}" for e in etiquetas)


def _extract_project_purpose(cwd: str) -> str:
    """Extrae el propósito del proyecto desde README.md si existe.

    Busca README.md en cwd, extrae el primer párrafo después del título,
    saltando badges, TOC y líneas vacías.

    Returns:
        String con el párrafo extraído, o string vacío si no existe.
    """
    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""

    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    title_idx = None
    for i, line in enumerate(lines):
        if line.startswith("# ") or line.startswith("#!"):
            title_idx = i
            break

    if title_idx is None:
        return ""

    start_idx = title_idx + 1
    paragraphs: list[str] = []
    current_para: list[str] = []

    for line in lines[start_idx:]:
        stripped = line.strip()

        if not stripped:
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("[!["):
            continue

        if stripped.startswith("- [") or stripped.startswith("* ["):
            continue

        if stripped.startswith("<!--"):
            continue

        if stripped.startswith("---") or stripped.startswith("___") or stripped.startswith("***"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            continue

        if stripped.startswith("#"):
            if current_para:
                paragraphs.append(" ".join(current_para))
                current_para = []
            break

        current_para.append(stripped)

    if current_para:
        paragraphs.append(" ".join(current_para))

    return paragraphs[0] if paragraphs else ""


def _extract_proposito_biblia(cwd: str, max_secciones: int = 3, max_caracteres: int = 2600) -> str:
    """Extrae el PROPOSITO-BIBLIA del README: tagline + secciones de identidad.

    A diferencia de ``_extract_project_purpose`` (solo el primer párrafo),
    esta función recoge la identidad completa: el tagline (línea en negrita
    tras el título) y los párrafos de las primeras secciones de contenido
    (``¿Qué es?``, metodología, etc.), que contienen el alma del proyecto.

    Args:
        cwd (str): Directorio raíz del proyecto.
        max_secciones (int): Máximo de secciones ``## `` a capturar.
        max_caracteres (int): Límite de caracteres del resultado.

    Returns:
        str: Párrafos de identidad separados por doble salto de línea,
        o string vacío si no se pudo extraer.
    """
    import re

    SECCIONES_NO_IDENTIDAD = {
        "instalación", "instalacion", "licencia", "contribuir",
        "comparativa", "lista completa de comandos", "comandos",
        "referencias", "changelog", "roadmap",
        # Secciones operativas — NO son identidad (ampliado 2026-08-11 tras el
        # piloto en Bot_AX_Contable: la primera sección del README era
        # "## 🚀 Requisitos" y se capturaba como "alma").
        "requisitos", "requerimientos", "requirements", "dependencias",
        "prerequisitos", "pre-requisitos", "configuración inicial",
        "configuracion inicial", "uso", "uso rápido", "uso rapido",
        "instrucciones", "instalación y uso", "instalacion y uso",
        "puesta en marcha", "quickstart", "inicio rápido", "inicio rapido",
        "ejecución", "ejecucion", "cómo usar", "como usar",
        "cómo se usa", "como se usa",
    }

    readme_path = os.path.join(cwd, "README.md")
    if not os.path.isfile(readme_path):
        return ""
    try:
        with open(readme_path, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as err:
        logger.warning("No se pudo leer README.md: %s", err)
        return ""

    tagline = ""
    parrafos: list[str] = []
    secciones_capturadas = 0
    en_seccion_contenido = False

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("[!["):          # badge de imagen
            continue
        if s.startswith("---") or s.startswith("<!--") or s.startswith("___"):
            continue
        if s.startswith("# "):           # título principal
            continue
        if s.startswith("## "):
            titulo_seccion = s.lstrip("#").strip().lower()
            # normalizar: quitar emojis/símbolos para comparar (p. ej. "🚀 requisitos")
            titulo_norm = re.sub(r"[^\w\sáéíóñü-]", "", titulo_seccion).strip()
            if titulo_norm in SECCIONES_NO_IDENTIDAD:
                # La PRIMERA sección operativa también corta: requisitos/instalación
                # NO son identidad (fix 2026-08-11, caso Bot_AX_Contable).
                break
            if not en_seccion_contenido:
                # primera sección con contenido (normalmente ¿Qué es?)
                en_seccion_contenido = True
                secciones_capturadas += 1
                continue
            secciones_capturadas += 1
            if secciones_capturadas >= max_secciones:
                break
            continue
        if s.startswith("|") or s.startswith("- [") or s.startswith("* ["):
            continue
        if s.startswith("```"):
            continue

        # limpiar markdown: **bold**, enlaces [x](url), imágenes ![..](..)
        texto = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", s)
        texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
        texto = texto.replace("**", "").strip()
        if not texto:
            continue

        if not en_seccion_contenido:
            # antes de la primera sección: el tagline (frase de identidad;
            # límite generoso para frases reales de ~150-300 caracteres)
            if not tagline and len(texto) < 400:
                tagline = texto
            continue

        parrafos.append(texto)
        if sum(len(p) for p in parrafos) > max_caracteres:
            parrafos = parrafos[:-1]
            break

    partes = [p for p in [tagline] + parrafos if p]
    resultado = "\n\n".join(partes)
    return resultado[:max_caracteres]


def _clasificar_nodos(nodes: list[Node]) -> dict[str, list[Node]]:
    """Clasifica los nodos del grafo según su tipo semántico.

    Args:
        nodes (list[Node]): Lista completa de nodos del mapa de contexto.

    Returns:
        dict[str, list[Node]]: Diccionario con listas de nodos agrupadas por
        tipo ('BASE', 'IDEA', 'RIESGO', 'CAMBIO', 'PRUEBA', 'FUTURO', 'HITO').
        CAMBIO agrupa también los nodos de tipo 'CORRECCION'.
    """
    return {
        "BASE": [n for n in nodes if n.type == "BASE"],
        "IDEA": [n for n in nodes if n.type == "IDEA"],
        "RIESGO": [n for n in nodes if n.type == "RIESGO"],
        "CAMBIO": [n for n in nodes if n.type in ("CAMBIO", "CORRECCION")],
        "PRUEBA": [n for n in nodes if n.type == "PRUEBA"],
        "FUTURO": [n for n in nodes if n.type == "FUTURO"],
        "HITO": [n for n in nodes if n.type == "HITO"],
        "DOCUMENTO": [n for n in nodes if n.type == "DOCUMENTO"],
    }


def _escribir_markdown(output_dir: str, nombre: str, partes: list[str]) -> str:
    """Escribe un archivo Markdown uniendo las líneas generadas.

    Args:
        output_dir (str): Directorio donde se escribe el archivo.
        nombre (str): Nombre del archivo (debe incluir la extensión .md).
        partes (list[str]): Líneas de contenido en orden.

    Returns:
        str: Ruta absoluta/relativa del archivo escrito.
    """
    ruta = os.path.join(output_dir, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(partes))
    return ruta


def _mencion_nodo_en_lista(nodo: Node, vistos: set[str], clave_limite: int = 80) -> bool:
    """Verifica si un nodo ya fue incluido en el listado.

    Args:
        nodo (Node): Nodo a evaluar.
        vistos (set[str]): Conjunto de claves ya procesadas.
        clave_limite (int): Límite de caracteres para la clave de deduplicación.

    Returns:
        bool: True si el nodo ya fue procesado, False en caso contrario.
    """
    clave = nodo.title[:clave_limite]
    if clave in vistos:
        return True
    vistos.add(clave)
    return False


def _render_grafo_conexiones(
    output_dir: str,
    nodes: list[Node],
    edges: list[Edge],
    con_wikilinks: bool = True,
    usar_rutas_reales: bool = False,
) -> None:
    """Renderiza el archivo de conexiones del grafo.

    Args:
        output_dir (str): Directorio de salida de la bóveda.
        nodes (list[Node]): Lista de nodos del mapa de contexto.
        edges (list[Edge]): Lista de aristas/relaciones.
        con_wikilinks (bool): Si True renderiza con wikilinks; si False usa
            texto plano (topología jerárquica estricta, evita nodos fantasma).
        usar_rutas_reales (bool): Si True, los wikilinks se resuelven a la
            ruta real de archivo del nodo (modo jerárquico); si False, usa
            slugs (modo raw/consolidado donde los slugs existen como archivos).
    """
    from context_map.presentation.vault.atomic import _render_conexiones

    _render_conexiones(
        output_dir, nodes, edges,
        con_wikilinks=con_wikilinks,
        usar_rutas_reales=usar_rutas_reales,
    )


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
    import json

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

"""Renderizado de la sección 3.0-ESTRUCTURA para la bóveda Obsidian jerárquica."""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.common import _escribir_markdown
from context_map.presentation.vault.templates import _normalize_tags, _safe_filename


def _render_nota_documento(
    n: Node,
    project_name: str,
    fecha_actual: str,
    directorio: str,
    pie_fn,
) -> None:
    """Renderiza una nota atómica de tipo DOCUMENTO con síntesis y citas.

    Args:
        n (Node): Nodo DOCUMENTO a renderizar.
        project_name (str): Nombre del proyecto.
        fecha_actual (str): Marca de tiempo ISO.
        directorio (str): Directorio donde se escribe la nota.
        pie_fn (Callable): Generador de pie.
    """
    from context_map.core.generators import generar_contexto_narrativo

    filename = _safe_filename(n.title) + ".md"
    tags_list = _normalize_tags(n.tags, n.type)
    tags_str = ", ".join(f'"{t}"' for t in tags_list)
    concepto = getattr(n, "concept", "") or "GENERAL"

    partes = [
        "---",
        "type: documento",
        f"status: {n.status}",
        f"concept: {concepto}",
        f"created: {fecha_actual}",
        f'project: "{project_name}"',
        f"tags: [{tags_str}]",
        f'source: "{n.source}"' if n.source else "source: ''",
        "---",
        "",
        f"# 📄 {n.title}",
        "",
        f"> **Concepto:** `{concepto}` · **Origen:** `{n.source or 'ingest'}`",
        "",
        "---",
        "",
    ]
    if n.summary:
        partes.append("## 🧠 Síntesis")
        partes.append("")
        partes.append(n.summary)
        partes.append("")

    partes.append("## 📖 Contexto Narrativo con Alma")
    partes.append("")
    partes.append(generar_contexto_narrativo(n))
    partes.append("")

    if n.evidence:
        partes.append("## 🔖 Citas")
        partes.append("")
        for cita in n.evidence:
            partes.append(f"- {cita}")
        partes.append("")

    partes.extend(pie_fn("[[3.2-DOCUMENTOS|⬅ Volver a 3.2 Documentos]]"))

    _escribir_markdown(directorio, filename, partes)


def _render_seccion_estructura(
    project_name: str,
    clasificados: dict[str, list[Node]],
    fecha_actual: str,
    output_dir: str,
    cabecera_fn,
    pie_fn,
) -> None:
    """Renderiza la sección 3.0-ESTRUCTURA (3.0, 3.1, 3.2).

    Args:
        project_name (str): Nombre del proyecto.
        clasificados (dict[str, list[Node]]): Nodos agrupados por tipo.
        fecha_actual (str): Marca de tiempo ISO.
        output_dir (str): Directorio de salida de la bóveda.
        cabecera_fn (Callable): Generador de cabecera.
        pie_fn (Callable): Generador de pie.
    """
    estructura_dir = os.path.join(output_dir, "3.0-ESTRUCTURA")
    os.makedirs(estructura_dir, exist_ok=True)

    documentos = clasificados.get("DOCUMENTO", [])

    partes = cabecera_fn(
        "seccion", "estructura", project_name, fecha_actual,
        ["context-map", "estructura"],
        f"# 3.0 Estructura — {project_name}",
    )
    partes.extend([
        "Componentes base, entrypoints, documentación e identidad del proyecto.",
        "",
        "---",
        "",
        "## Sub-secciones",
        "",
        "- [[3.1-Fundamentos|3.1 Fundamentos]]",
    ])
    if documentos:
        partes.append(f"- [[3.2-DOCUMENTOS|3.2 Documentos]] ({len(documentos)})")
    partes.extend([
        "",
        "---",
        "[[00-INDICE|⬅ Volver al índice]]",
        "",
    ])
    _escribir_markdown(estructura_dir, "3.0-ESTRUCTURA.md", partes)

    fund_parts = cabecera_fn(
        "fundamentos", None, project_name, fecha_actual,
        ["context-map", "fundamentos", "estructura"],
        "# 3.1 Fundamentos",
    )
    fund_parts.extend([
        "Componentes base del proyecto con sus descripciones y orígenes.",
        "",
        "---",
        "",
    ])
    if clasificados["BASE"]:
        from context_map.core.generators import generar_contexto_narrativo
        from context_map.core.generators.generadores import _titulo_limpio
        from context_map.presentation.vault.consolidated.secciones_proposito import (
            _es_ruido_identidad,
        )

        seen_base: set[str] = set()
        for n in clasificados["BASE"]:
            if _es_ruido_identidad(n):
                continue  # métricas del scan ('Proyecto X — N archivos') y entrypoints no son fundamentos
            key = n.title[:80]
            if key in seen_base:
                continue
            seen_base.add(key)
            fund_parts.append(f"## 📦 {_titulo_limpio(n.title)}")
            fund_parts.append("")
            if n.summary:
                fund_parts.append(_titulo_limpio(n.summary))
                fund_parts.append("")
            fund_parts.append(generar_contexto_narrativo(n))
            fund_parts.append("")
        if len(fund_parts) <= 7:
            fund_parts.append("_(Los componentes base con significado se listan aquí; las métricas del scan viven en 1.2-Datos-Clave)_")
            fund_parts.append("")
    else:
        fund_parts.append("_(No se registraron componentes base)_")
        fund_parts.append("")

    fund_parts.extend(pie_fn("[[3.0-ESTRUCTURA/3.0-ESTRUCTURA|⬅ Volver a 3.0 Estructura]]"))
    _escribir_markdown(estructura_dir, "3.1-Fundamentos.md", fund_parts)

    # ============================================================
    # 3.2 Documentos — ingesta de conocimiento externo
    # ============================================================
    if documentos:
        docs_dir = os.path.join(estructura_dir, "3.2-DOCUMENTOS")
        os.makedirs(docs_dir, exist_ok=True)

        index_parts = cabecera_fn(
            "seccion", "documentos", project_name, fecha_actual,
            ["context-map", "documentos", "ingesta"],
            f"# 3.2 Documentos — {project_name}",
        )
        index_parts.extend([
            f"Documentos externos ingeridos: **{len(documentos)}**",
            "",
            "---",
            "",
            "## Lista de Documentos",
            "",
        ])
        seen_doc: set[str] = set()
        for n in documentos:
            key = n.title[:80]
            if key in seen_doc:
                continue
            seen_doc.add(key)
            slug = _safe_filename(n.title)
            concepto = getattr(n, "concept", "") or "GENERAL"
            index_parts.append(
                f"- 📄 [[{slug}|{n.title}]] · `{concepto}` · {len(n.evidence)} citas"
            )
            _render_nota_documento(n, project_name, fecha_actual, docs_dir, pie_fn)
        index_parts.append("")
        index_parts.extend(pie_fn("[[3.0-ESTRUCTURA/3.0-ESTRUCTURA|⬅ Volver a 3.0 Estructura]]"))
        _escribir_markdown(docs_dir, "3.2-DOCUMENTOS.md", index_parts)

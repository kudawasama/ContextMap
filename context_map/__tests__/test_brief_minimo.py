"""Brief por capas (P1.2): la capa mínima reduce tokens sin perder el hilo.

El brief completo (~1.600 tokens) se lee en cada sesión. La capa mínima conserva
identidad, estado, títulos de riesgos/pendientes y **cómo ampliar** con
`context_search`; el detalle queda a un comando de distancia.
"""

from __future__ import annotations

import os

from context_map.core.models import Node
from context_map.core.tokenization import TokenCounter
from context_map.presentation.briefs.brief import generar_brief
from context_map.presentation.briefs.brief_minimo import (
    generar_brief_minimo,
    medir_brief,
)


def _proyecto(tmp_path) -> str:
    """Proyecto mínimo con README y vault para los dos briefs."""
    raiz = str(tmp_path)
    with open(os.path.join(raiz, "README.md"), "w", encoding="utf-8") as f:
        f.write(
            "# ContextMap\n\n> Memoria viva del proyecto para agentes de IA.\n\n"
            "ContextMap escanea el proyecto y genera un brief y un vault de Obsidian "
            "para que las IAs no pierdan el contexto entre sesiones.\n"
        )
    os.makedirs(os.path.join(raiz, ".context-map", "vault-Demo", "7.0-MANUAL"), exist_ok=True)
    with open(
        os.path.join(raiz, ".context-map", "vault-Demo", "7.0-MANUAL", "BACKLOG.md"),
        "w", encoding="utf-8",
    ) as f:
        f.write("# BACKLOG\n\n- [ ] Limpiar TODO históricos\n")
    return raiz


def _nodos() -> list[Node]:
    """Nodos con riesgos y pendientes para las dos capas del brief."""
    return [
        Node(id="R1", type="RIESGO", title="Ruido de snapshots sin retención"),
        Node(id="R2", type="RIESGO", title="Vaults duplicados mezclando grafos"),
        Node(id="F1", type="FUTURO", title="Implementar context_search"),
        Node(id="B1", type="BASE", title="Servidor MCP nativo"),
    ]


def test_brief_minimo_conserva_identidad_titulos_y_ampliacion(tmp_path) -> None:
    """La capa mínima trae lo esencial y explica cómo pedir más contexto."""
    raiz = _proyecto(tmp_path)
    ruta = os.path.join(raiz, ".context-map", "CONTEXT.min.md")

    texto = generar_brief_minimo("Demo", _nodos(), readiness_score=100, output_path=ruta, project_dir=raiz)

    assert os.path.isfile(ruta)
    assert "Demo" in texto
    assert "Ruido de snapshots" in texto, "los riesgos deben aparecer (al menos el título)"
    assert "Implementar context_search" in texto
    assert "Ampliar contexto" in texto
    assert "context_search" in texto and "BACKLOG.md" in texto


def test_brief_minimo_ahorra_tokens(tmp_path) -> None:
    """El brief mínimo pesa bastante menos que el completo."""
    raiz = _proyecto(tmp_path)
    ruta_full = os.path.join(raiz, ".context-map", "CONTEXT.md")
    ruta_min = os.path.join(raiz, ".context-map", "CONTEXT.min.md")

    completo = generar_brief("Demo", _nodos(), [], 100, ruta_full, project_dir=raiz)
    minimo = generar_brief_minimo("Demo", _nodos(), 100, ruta_min, project_dir=raiz)

    contador = TokenCounter()
    tk_full, tk_min = contador.count_tokens(completo), contador.count_tokens(minimo)
    assert tk_min < tk_full, f"mín ({tk_min}) debería ser menor que completo ({tk_full})"
    assert tk_min <= tk_full * 0.75, f"ahorro insuficiente: {tk_min} vs {tk_full}"


def test_medir_brief_reporta_ahorro(tmp_path) -> None:
    """``medir_brief`` compara las dos capas y calcula el porcentaje de ahorro."""
    raiz = _proyecto(tmp_path)
    generar_brief("Demo", _nodos(), [], 100, os.path.join(raiz, ".context-map", "CONTEXT.md"), project_dir=raiz)
    generar_brief_minimo(
        "Demo", _nodos(), 100, os.path.join(raiz, ".context-map", "CONTEXT.min.md"), project_dir=raiz
    )

    datos = medir_brief(raiz)

    assert datos["completo_tokens"] > datos["minimo_tokens"] > 0
    assert 0 < datos["ahorro_pct"] < 100


def test_brief_minimo_sin_nodos_no_falla(tmp_path) -> None:
    """Sin nodos sigue generando un brief válido (proyecto recién inicializado)."""
    raiz = _proyecto(tmp_path)
    ruta = os.path.join(raiz, ".context-map", "CONTEXT.min.md")
    texto = generar_brief_minimo("Demo", [], 0, ruta, project_dir=raiz)
    assert "Demo" in texto and "Ampliar contexto" in texto


def test_brief_minimo_incluye_las_reglas_fijas(tmp_path) -> None:
    """El agente lee la capa mínima: si las reglas no están ahí, no las ve.

    Regresión: la capa completa tenía "Reglas de Negocio" pero la mínima —la que
    se lee por defecto— no decía nada de las obligaciones del proyecto.
    """
    raiz = _proyecto(tmp_path)
    catalogo = os.path.join(raiz, "references", "reglas")
    os.makedirs(catalogo, exist_ok=True)
    with open(os.path.join(catalogo, "reglas_registro.yaml"), "w", encoding="utf-8") as f:
        f.write(
            "version: 1.0\nreglas:\n"
            "  - id: REG-EJE-001\n"
            "    resumen: \"intérprete del venv\"\n"
            "    nombre: \"Ejecutar con el intérprete del venv\"\n"
            "    categoria: REG-EJE\n"
            "    prioridad: critica\n"
            "    estado: implementada\n"
            "    norma: \"AGENTS.md\"\n"
            "    seccion: \"3. Protocolo\"\n"
            "  - id: REG-DOC-001\n"
            "    resumen: \"español técnico\"\n"
            "    nombre: \"Responder en español técnico\"\n"
            "    categoria: REG-DOC\n"
            "    prioridad: media\n"
            "    estado: implementada\n"
            "    norma: \"AGENTS.md\"\n"
            "    seccion: \"1. Reglas globales\"\n"
        )

    texto = generar_brief_minimo(
        "Demo",
        _nodos(),
        readiness_score=90,
        output_path=os.path.join(raiz, ".context-map", "CONTEXT.min.md"),
        project_dir=raiz,
    )

    assert "Reglas fijas" in texto
    assert "001 intérprete del venv" in texto
    assert "references/reglas/reglas_registro.yaml" in texto
    # Solo las críticas pueblan la línea; la media queda en el catálogo.
    assert "español técnico" not in texto


def test_brief_minimo_sin_catalogo_no_inventa_reglas(tmp_path) -> None:
    """Un proyecto sin catálogo no debe ver una sección vacía ni falsa."""
    raiz = _proyecto(tmp_path)
    texto = generar_brief_minimo(
        "Demo",
        _nodos(),
        readiness_score=90,
        output_path=os.path.join(raiz, ".context-map", "CONTEXT.min.md"),
        project_dir=raiz,
    )
    assert "Reglas fijas" not in texto

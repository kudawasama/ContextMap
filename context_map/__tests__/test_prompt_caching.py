"""Pruebas unitarias para el optimizador de Prompt Caching en CONTEXT.md.

Verifica que el brief se particione de forma determinista entre un prefijo
invariante estático (congelable en caché para Claude 3.7 y Gemini 2.5) y un
bloque dinámico de métricas y tareas, garantizando la máxima tasa de Cache Hit.
"""

from __future__ import annotations

import tempfile

from context_map.core.models import Edge, Node
from context_map.presentation.briefs.brief import generar_brief


def test_particion_prompt_caching_determinista() -> None:
    """Verifica que el brief sitúe el prefijo invariante antes del boundary."""
    nodos = [
        Node(id="B1", type="BASE", title="Motor Principal", summary="Fundamento del sistema"),
        Node(id="R1", type="RIESGO", title="Falla de Conexión", summary="Pérdida de red"),
        Node(id="F1", type="FUTURO", title="Refactorizar CLI", summary="Mejorar comandos"),
    ]
    edges: list[Edge] = []

    with tempfile.TemporaryDirectory() as tmpdir:
        salida_brief = f"{tmpdir}/CONTEXT.md"
        contenido = generar_brief(
            project_name="ContextMap",
            nodes=nodos,
            edges=edges,
            readiness_score=85,
            output_path=salida_brief,
            project_dir=tmpdir,
        )

        assert "<!-- PROMPT_CACHE_BOUNDARY: INVARIANT_PREFIX -->" in contenido

        partes = contenido.split("<!-- PROMPT_CACHE_BOUNDARY: INVARIANT_PREFIX -->")
        assert len(partes) == 2, "El brief debe dividirse exactamente en dos bloques por la frontera"

        prefijo_invariante, bloque_dinamico = partes[0], partes[1]

        # El prefijo invariante debe contener identidad, propósito y directivas operativas
        assert "# ContextMap — Brief para Agentes" in prefijo_invariante
        assert "¿Qué es y por qué existe?" in prefijo_invariante
        assert "Cómo trabajar aquí" in prefijo_invariante
        assert "Comandos Útiles" in prefijo_invariante

        # El bloque dinámico debe contener estadísticas, riesgos, tareas y métricas de tokens
        assert "Resumen Ejecutivo" in bloque_dinamico
        assert "Estado del Proyecto" in bloque_dinamico
        assert "Riesgos Críticos" in bloque_dinamico
        assert "Tareas Pendientes" in bloque_dinamico
        assert "Eficiencia de Contexto & Presupuesto de Tokens" in bloque_dinamico
        assert "Prefijo Invariante (Prompt Cache)" in bloque_dinamico

        # Determinismo: una segunda compilación debe producir exactamente el mismo prefijo invariante
        contenido_2 = generar_brief(
            project_name="ContextMap",
            nodes=nodos,
            edges=edges,
            readiness_score=85,
            output_path=salida_brief,
            project_dir=tmpdir,
        )
        prefijo_2 = contenido_2.split("<!-- PROMPT_CACHE_BOUNDARY: INVARIANT_PREFIX -->")[0]
        assert prefijo_invariante == prefijo_2, "El prefijo invariante debe ser 100% determinista"

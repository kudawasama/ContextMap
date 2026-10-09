"""Tests de `context(seccion=...)`: leer solo una parte del brief."""

from __future__ import annotations

import os

from context_map.infrastructure.mcp_server import context


def _proyecto(tmp_path) -> str:
    """Proyecto mínimo con un CONTEXT.md con varias secciones."""
    cm = os.path.join(str(tmp_path), ".context-map")
    os.makedirs(cm, exist_ok=True)
    with open(os.path.join(cm, "CONTEXT.md"), "w", encoding="utf-8") as f:
        f.write(
            "# Brief\n\n"
            "## ¿Qué es y por qué existe?\n\nSoy ContextMap.\n\n"
            "## ⚠️ Riesgos Críticos\n\n- Riesgo uno\n- Riesgo dos\n\n"
            "## 📝 Tareas Pendientes\n\n- Ninguna\n"
        )
    return str(tmp_path)


def test_seccion_devuelve_solo_esa_parte(tmp_path) -> None:
    """La sección pedida se devuelve y no arrastra el resto del brief."""
    txt = context(target=_proyecto(tmp_path), seccion="riesgos")
    assert "Riesgos Críticos" in txt
    assert "Riesgo uno" in txt
    assert "¿Qué es y por qué existe?" not in txt


def test_seccion_ignora_acentos_y_mayusculas(tmp_path) -> None:
    """La búsqueda de sección normaliza acentos y mayúsculas."""
    txt = context(target=_proyecto(tmp_path), seccion="TAREAS")
    assert "Tareas Pendientes" in txt


def test_seccion_inexistente_lista_disponibles(tmp_path) -> None:
    """Si no existe, se listan las secciones disponibles."""
    txt = context(target=_proyecto(tmp_path), seccion="nope")
    assert "no encontrada" in txt
    assert "Riesgos Críticos" in txt

"""Humanización de las notas narrativas generadas (1.1, 1.3 y 2.4).

El scanner y los importadores producen eventos útiles como *historia* pero que
ensucian la narrativa. Estos tests garantizan que las notas generadas hablen
del proyecto y no del proceso: sin métricas repetitivas, TODOs crudos ni
mensajes de chat.
"""

from __future__ import annotations

import tempfile

from context_map.core.models import Edge, Node
from context_map.core.normalization.humanizacion import (
    es_entrypoint_descartable,
    es_mensaje_chat,
    es_metrica_scan,
    es_resumen_plantilla,
    es_ruido_narrativo,
    es_todo_crudo,
)
from context_map.presentation.vault import render_obsidian_vault


def _nodo(id_: str, tipo: str, titulo: str, resumen: str = "") -> Node:
    """Crea un nodo mínimo para las pruebas."""
    return Node(id=id_, type=tipo, title=titulo, summary=resumen, source="test")


def test_predicados_de_ruido() -> None:
    """Cada predicado reconoce su patrón y no marca nodos legítimos."""
    metrica = _nodo("B1", "BASE", "Proyecto 'Demo' — 100 archivos, 5000 líneas, entrypoints: 2")
    todo = _nodo("B2", "FUTURO", "TODO (x.py:L1): pendiente")
    chat = _nodo("B3", "BASE", "¡La tool MCP funciona! (◕‿◕)")
    plantilla = _nodo(
        "B4", "BASE", "REG-ING-001: DB activa",
        "REGLA: REG-ING-001: DB activa. Este evento forma parte del mapa contextual del proyecto.",
    )
    real = _nodo("B5", "BASE", "Núcleo de la arquitectura", "El dominio central del sistema")
    # Un nodo importado de un chat se detecta por su ``source``, aunque el texto
    # no tenga marcas visibles.
    chat_src = Node(id="B6", type="BASE", title="Todo listo", summary="", source="chat")
    scratch = _nodo("B7", "BASE", r"Entrypoint: .work\scratch\abc\app.py")

    assert es_metrica_scan(metrica)
    assert es_todo_crudo(todo)
    assert es_mensaje_chat(chat)
    assert es_mensaje_chat(chat_src)
    assert es_resumen_plantilla(plantilla)
    assert es_entrypoint_descartable(scratch)

    assert es_ruido_narrativo(metrica)
    assert es_ruido_narrativo(todo)
    assert es_ruido_narrativo(chat)
    assert es_ruido_narrativo(chat_src)
    assert es_ruido_narrativo(scratch)
    # La plantilla NO es "ruido narrativo" genérico (solo se filtra en identidad).
    assert not es_ruido_narrativo(plantilla)
    assert not es_ruido_narrativo(real)


def test_notas_narrativas_no_muestran_ruido() -> None:
    """1.1, 1.3 y 2.4 excluyen métricas del scan, TODOs crudos y chats."""
    nodos = [
        _nodo("BASE-01", "BASE", "Proyecto 'Demo' — 100 archivos, 5000 líneas"),
        _nodo("BASE-02", "BASE", "Entrypoint: main.py"),
        _nodo(
            "BASE-03", "BASE", "REG-ING-001: DB activa",
            "REGLA: REG-ING-001. Este evento forma parte del mapa contextual del proyecto.",
        ),
        _nodo("IDEA-01", "IDEA", "¡La tool MCP funciona! (◕‿◕)", "Corrección: funciona con la BD real"),
        _nodo("IDEA-02", "IDEA", "TODO (foo.py:L3): refactor pendiente", "deuda"),
        _nodo("IDEA-03", "IDEA", "feat: dedup de nodos y tags limpias", "Feature implementada"),
        _nodo("BASE-04", "BASE", "Núcleo de la arquitectura", "El dominio central del sistema"),
    ]
    edges = [Edge(source="BASE-04", target="IDEA-03", kind="relates_to")]
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_humanizacion_")

    render_obsidian_vault(
        project_name="ProyectoDemo",
        nodes=nodos,
        edges=edges,
        output_dir=temp_dir,
        mode="hierarchical",
    )

    def _leer(*partes: str) -> str:
        import os

        ruta = os.path.join(temp_dir, *partes)
        with open(ruta, encoding="utf-8") as f:
            return f.read()

    narrativa = _leer("1.0-PROPOSITO", "1.1-Mapa-Mental-Narrativo.md")
    proposito = _leer("1.0-PROPOSITO", "1.3-Proposito.md")
    ideas = _leer("2.0-IDEAS", "2.4-Ideas-Relevantes.md")

    # Ruido fuera de las tres notas
    assert "Proyecto 'Demo'" not in narrativa
    assert "TODO (foo.py:L3)" not in ideas
    assert "REG-ING-001" not in proposito
    assert "◕‿◕" not in proposito
    assert "◕‿◕" not in ideas

    # Contenido legítimo conservado
    assert "Núcleo de la arquitectura" in proposito
    assert "feat: dedup de nodos" in ideas

"""Test: mapa mental conectado — rutas reales de archivo y conexiones semánticas."""

from __future__ import annotations

import os
import shutil
import tempfile

from context_map.core.models import Node


def _nodo(
    id_: str,
    tipo: str = "IDEA",
    titulo: str = "Idea",
    concepto: str = "",
    status: str = "pendiente",
    fecha: str = "2026-08-01T10:00:00",
    summary: str = "",
    clasif: str = "feature",
) -> Node:
    return Node(
        id=id_, type=tipo, title=titulo, concept=concepto, status=status,
        created_at=fecha, summary=summary, classification=clasif,
    )


def test_ruta_archivo_nodo_idea_pendiente() -> None:
    from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo

    idea = _nodo("FUTURO001", titulo="Nueva feature", concepto="DEVOPS")
    ruta = ruta_archivo_nodo(idea)
    assert ruta == (
        "2.0-IDEAS/2.1-Ideas-Pendientes/DEVOPS/"
        "idea_FUTURO001_NUEVA_FUNCIONALIDAD.md"
    )


def test_ruta_archivo_nodo_idea_activa_y_completada() -> None:
    from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo

    activa = _nodo("I2", titulo="Roadmap", concepto="ETL", status="activo")
    assert ruta_archivo_nodo(activa).startswith("2.0-IDEAS/2.2-Ideas-Futuras/ETL/")

    completada = _nodo("I3", titulo="Hecho", concepto="UI", status="completado")
    assert ruta_archivo_nodo(completada) == (
        "2.0-IDEAS/2.3-Ideas-Completas-e-Implementadas/UI/UI-Completas.md"
    )


def test_ruta_archivo_nodo_riesgo_y_agrupados() -> None:
    from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo

    riesgo = _nodo("R1", tipo="RIESGO", titulo="Deuda técnica en parser.py")
    assert ruta_archivo_nodo(riesgo).startswith("4.0-RIESGOS/")

    for tipo in ("BASE", "FUTURO", "CAMBIO", "CORRECCION", "PRUEBA", "DOCUMENTO", "HITO"):
        assert ruta_archivo_nodo(_nodo(f"{tipo}1", tipo=tipo)) is None, tipo


def test_conexiones_semanticas_por_concepto_y_fecha() -> None:
    from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo

    a = _nodo("I1", titulo="Bot contable", concepto="AUTOMATIZACION")
    b = _nodo("I2", titulo="Reporte diario", concepto="AUTOMATIZACION")
    c = _nodo("I3", titulo="UI nueva", concepto="UI", fecha="2026-08-02T09:00:00")

    cons = conexiones_de_nodo(a, [a, b, c])
    ids = [n.id for n in cons]
    assert "I2" in ids            # mismo concepto
    assert "I3" not in ids        # concepto y fecha distintos
    assert len(cons) <= 5


def test_conexiones_ignoran_nodos_sin_archivo() -> None:
    from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo

    a = _nodo("I1", titulo="Bot contable", concepto="AUTOMATIZACION")
    base = _nodo("B1", tipo="BASE", titulo="Proyecto", concepto="AUTOMATIZACION")
    fut = _nodo("F1", tipo="FUTURO", titulo="TODO pendiente", concepto="AUTOMATIZACION")

    cons = conexiones_de_nodo(a, [a, base, fut])
    # BASE y FUTURO no tienen archivo individual → no aparecen como conexión
    assert all(n.type == "IDEA" for n in cons)


def test_conexiones_por_mencion_cruzada() -> None:
    from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo

    a = _nodo("I1", titulo="Bot contable", concepto="AUTOMATIZACION",
              summary="El bot contable se integra con el Reporte diario.")
    b = _nodo("I2", titulo="Reporte diario", concepto="REPORTES")
    cons = conexiones_de_nodo(a, [a, b])
    assert "I2" in [n.id for n in cons]


def test_canvas_es_json_valido_con_archivos_reales() -> None:
    """T8: 00-MAPA-MENTAL.canvas — nodos file que existen y aristas válidas."""
    import json

    from context_map.presentation.vault.consolidated.canvas import render_canvas

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_canvas_")
    try:
        nodos = [
            _nodo("I1", titulo="A", concepto="DEVOPS"),
            _nodo("I2", titulo="B", concepto="DEVOPS"),
            _nodo("B1", tipo="BASE", titulo="Proyecto"),
        ]
        # Simular los archivos reales que el renderizador crearía
        for n in nodos:
            from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo

            ruta = ruta_archivo_nodo(n)
            if ruta:
                p = os.path.join(temp_dir, ruta.replace("/", os.sep))
                os.makedirs(os.path.dirname(p), exist_ok=True)
                with open(p, "w", encoding="utf-8") as f:
                    f.write("# x\n")

        render_canvas(temp_dir, nodos, [])
        canvas_path = os.path.join(temp_dir, "00-MAPA-MENTAL.canvas")
        assert os.path.exists(canvas_path)
        with open(canvas_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["nodes"]) == 2          # solo archivos reales (sin BASE)
        for node in data["nodes"]:
            assert node["type"] == "file"
            assert os.path.exists(os.path.join(temp_dir, node["file"].replace("/", os.sep)))
        assert data["edges"] == []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_graph_json_grupos_por_estado() -> None:
    """T9: .obsidian/graph.json con grupos de color por estado."""
    import json

    from context_map.presentation.vault.consolidated.canvas import render_graph_json

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_graph_")
    try:
        render_graph_json(temp_dir, [])
        graph_path = os.path.join(temp_dir, ".obsidian", "graph.json")
        assert os.path.exists(graph_path)
        with open(graph_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["groups"]) >= 3
        queries = [g["query"] for g in data["groups"]]
        assert any("2.1-Ideas-Pendientes" in q for q in queries)
        assert any("4.0-RIESGOS" in q for q in queries)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_plantillas_y_nota_del_dia() -> None:
    """T10: plantilla de sesión y nota del día con wikilinks."""
    from context_map.presentation.vault.consolidated.canvas import (
        render_nota_dia,
        render_plantillas,
    )

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_plantillas_")
    try:
        render_plantillas(temp_dir, "Demo")
        plantilla = os.path.join(temp_dir, ".context-map", "plantillas", "nota-sesion.md")
        assert os.path.exists(plantilla)
        with open(plantilla, encoding="utf-8") as f:
            contenido = f.read()
        assert "preserve: true" in contenido

        nodos = [_nodo("I1", titulo="Bot", concepto="DEVOPS", fecha="2026-08-10T09:00:00")]
        render_nota_dia(temp_dir, "Demo", nodos)
        diario = os.path.join(temp_dir, ".context-map", "vault-Demo", "7.0-MANUAL", "Diario", "2026-08-10.md")
        assert os.path.exists(diario)
        with open(diario, encoding="utf-8") as f:
            nota = f.read()
        assert "Bot" in nota
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_conexiones_ignoran_todos_del_mismo_archivo() -> None:
    """El ruido del scanner (TODOs del mismo archivo) NO crea conexiones."""
    from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo

    a = _nodo("I1", titulo="TODO (core/foo.py:L10): tarea A", concepto="DEVOPS")
    b = _nodo("I2", titulo="TODO (core/foo.py:L20): tarea B", concepto="DEVOPS")
    c = _nodo("I3", titulo="TODO (core/bar.py:L5): tarea C", concepto="DEVOPS")

    cons = conexiones_de_nodo(a, [a, b, c])
    ids = [n.id for n in cons]
    assert "I2" not in ids   # mismo archivo → ruido
    assert "I3" in ids       # distinto archivo, mismo concepto → relación real


def test_titulo_legible_quita_ruido() -> None:
    from context_map.presentation.vault.consolidated.rutas import titulo_legible

    n = _nodo("I1", titulo="TODO (core/foo.py:L10): Narrativa especializada")
    assert titulo_legible(n) == "Narrativa especializada"


def test_proposito_biblia_extrae_identidad() -> None:
    """La biblia extrae tagline + sección ¿Qué es? del README (sin la segunda sección)."""
    from context_map.presentation.vault.consolidated.common import _extract_proposito_biblia

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_biblia_")
    try:
        with open(os.path.join(temp_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write(
                "# Demo\n\n**Tagline del proyecto**\n\n[![badge](url)]\n\n---\n\n"
                "## ¿Qué es?\n\nEsto es el alma del proyecto.\n\n"
                "No es un simple generador: captura el alma.\n\n---\n\n"
                "## Instalación\n\npip install demo\n"
            )
        biblia = _extract_proposito_biblia(temp_dir)
        assert "Tagline del proyecto" in biblia
        assert "Esto es el alma del proyecto" in biblia
        assert "captura el alma" in biblia
        assert "pip install" not in biblia  # segunda sección excluida
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_es_ruido_identidad() -> None:
    """El ruido del scanner no entra a la biblia (1.3-Proposito)."""
    from context_map.presentation.vault.consolidated.secciones_proposito import (
        _es_ruido_identidad,
    )

    metrica = _nodo("B1", tipo="BASE", titulo="Proyecto 'Demo' — 100 archivos, 5000 líneas, entrypoints: 2")
    todo = _nodo("B2", tipo="FUTURO", titulo="TODO (x.py:L1): pendiente")
    entry = _nodo("B3", tipo="BASE", titulo="Entrypoint: main.py")
    real = _nodo("B4", tipo="BASE", titulo="Núcleo de la arquitectura", summary="El dominio central")

    assert _es_ruido_identidad(metrica)
    assert _es_ruido_identidad(todo)
    assert _es_ruido_identidad(entry)
    assert not _es_ruido_identidad(real)


def test_restaurar_paths_legibles() -> None:
    """Los paths aplanados por scans antiguos se reconstruyen legibles."""
    from context_map.core.normalization.standardize import _restaurar_paths_legibles

    legible = _restaurar_paths_legibles(
        "Archivos de alta complejidad context_mapcorenormalizationstandardize.py, context_mapdomainecosystemadaptador.py"
    )
    assert "context_map/core/normalization/standardize.py" in legible
    assert "context_map/domain/ecosystem/adaptador.py" in legible
    assert "context_mapcore" not in legible


def test_todo_codigo_no_es_tarea() -> None:
    """Los TODOs con código crudo NO son tareas del proyecto (filtro de ruido)."""
    from context_map.presentation.vault.consolidated.secciones_backlog import _es_todo_codigo

    crudo = _nodo("F1", tipo="FUTURO", titulo='TODO (x.py:L1): return f"""### 📝 1. Tarea Pendiente')
    crudo2 = _nodo("F2", tipo="FUTURO", titulo="TODO (y.py:L2): if any(kw in text for kw in pendiente_kw)")
    limpio = _nodo("F3", tipo="FUTURO", titulo="TODO (z.py:L3): Narrativa especializada para tareas FUTURAS")

    assert _es_todo_codigo(crudo)
    assert _es_todo_codigo(crudo2)
    assert not _es_todo_codigo(limpio)  # TODO con texto legible SÍ es tarea


def test_narrativa_idea_limpia_ruido() -> None:
    """La narrativa de una idea con TODO(path) sale limpia, no mecánica."""
    from context_map.core.generators import generar_contexto_narrativo

    n = _nodo(
        "I1",
        titulo="TODO (core/foo.py:L10): Narrativa especializada para tareas",
        summary='Pendiente: """Narrativa especializada para tareas FUTURAS."""',
    )
    narrativa = generar_contexto_narrativo(n)
    assert "TODO (core/foo.py" not in narrativa
    assert "Narrativa especializada" in narrativa
    assert '"""' not in narrativa
    # Plano profesional: casillas de gobierno presentes
    assert "¿PARA QUIÉN es?" in narrativa
    assert "¿QUÉ VALOR APORTA?" in narrativa
    assert "¿QUÉ SE ARRIESGA SI NO SE HACE?" in narrativa
    assert "¿CÓMO SE SABE QUE ESTÁ LISTO?" in narrativa
    assert "¿DE QUÉ DEPENDE?" in narrativa
    assert "Pendiente de contexto" in narrativa


def test_servidor_mcp_expone_herramientas() -> None:
    """El servidor MCP registra las tools de ContextMap (sin mcp instalado no falla el import)."""
    from context_map.infrastructure import mcp_server

    assert mcp_server is not None
    # Las tools se definen como funciones en el módulo (decorador condicional)
    for nombre in ("refresh", "scan", "build", "check", "import_git", "context"):
        assert hasattr(mcp_server, nombre), f"falta tool {nombre}"


def test_edges_relaciona_por_menciones_cruzadas() -> None:
    """T12: la historia conecta — un evento que menciona 2+ nodos crea edge 'relaciona'."""
    from context_map.core.models import Event
    from context_map.domain.synchronization.relaciones import crear_edges_por_menciones

    a = _nodo("I1", titulo="Bot contable", concepto="AUTOMATIZACION")
    b = _nodo("I2", titulo="Reporte diario", concepto="REPORTES")
    c = _nodo("I3", titulo="UI de casinos", concepto="UI")

    ev = Event(
        type="IDEA",
        text="Hoy avanzamos el Bot contable y empezamos el Reporte diario",
        timestamp="2026-08-10T10:00:00",
        source="chat",
    )
    nuevos = crear_edges_por_menciones([a, b, c], [], [ev])
    assert len(nuevos) == 1
    assert nuevos[0].kind == "relaciona"
    assert {nuevos[0].source, nuevos[0].target} == {"I1", "I2"}
    assert "mencion cruzada" in nuevos[0].note


def test_edges_relaciona_dedup() -> None:
    """T12: no duplica edges existentes (ni en sentido inverso)."""
    from context_map.core.models import Edge, Event
    from context_map.domain.synchronization.relaciones import crear_edges_por_menciones

    a = _nodo("I1", titulo="Bot contable")
    b = _nodo("I2", titulo="Reporte diario")
    existente = Edge(source="I1", target="I2", kind="relaciona")

    ev = Event(
        type="IDEA",
        text="Bot contable y Reporte diario juntos",
        timestamp="2026-08-10T10:00:00",
        source="chat",
    )
    nuevos = crear_edges_por_menciones([a, b], [existente], [ev])
    assert nuevos == []


if __name__ == "__main__":
    import sys

    tests = [
        test_ruta_archivo_nodo_idea_pendiente,
        test_ruta_archivo_nodo_idea_activa_y_completada,
        test_ruta_archivo_nodo_riesgo_y_agrupados,
        test_conexiones_semanticas_por_concepto_y_fecha,
        test_conexiones_ignoran_nodos_sin_archivo,
        test_conexiones_por_mencion_cruzada,
        test_canvas_es_json_valido_con_archivos_reales,
        test_graph_json_grupos_por_estado,
        test_plantillas_y_nota_del_dia,
        test_conexiones_ignoran_todos_del_mismo_archivo,
        test_titulo_legible_quita_ruido,
        test_restaurar_paths_legibles,
        test_todo_codigo_no_es_tarea,
        test_servidor_mcp_expone_herramientas,
        test_proposito_biblia_extrae_identidad,
        test_es_ruido_identidad,
        test_narrativa_idea_limpia_ruido,
        test_edges_relaciona_por_menciones_cruzadas,
        test_edges_relaciona_dedup,
    ]
    fallos = 0
    for t in tests:
        try:
            t()
            print(f"   OK: {t.__name__} PASO")
        except AssertionError as err:
            fallos += 1
            print(f"   [X] {t.__name__} FALLO: {err}")
    sys.exit(1 if fallos else 0)

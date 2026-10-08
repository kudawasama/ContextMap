"""El diario consolida bloques del scanner en uno solo (R4) y no trunca títulos (R5).

Auditoría 2026-08-14: el diario del 13-08 acumuló 9 bloques "🤖 Ingresados
por el scanner" por builds repetidos del mismo día. Cada anexo debe
CONSOLIDARSE en la sección autogenerada existente, no crear otra.
"""

from __future__ import annotations

from datetime import date

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.canvas import render_nota_dia


def _nodo(titulo: str, fecha: str) -> Node:
    """Crea un nodo BASE con la fecha de creación dada.

    Args:
        titulo (str): Título del nodo.
        fecha (str): Fecha ISO (YYYY-MM-DD) del nodo.

    Returns:
        Node: Nodo listo para renderizar.
    """
    return Node(id=titulo, type="BASE", title=titulo, created_at=f"{fecha}T10:00:00")


def _ruta_diario(tmp_path, hoy: str):
    """Ruta esperada del diario del día en el vault del proyecto."""
    return (
        tmp_path
        / ".context-map"
        / "vault-MiProyecto"
        / "7.0-MANUAL"
        / "Diario"
        / f"{hoy}.md"
    )


def test_anexa_una_sola_seccion_autogenerada(tmp_path):
    """Dos builds del mismo día consolidan en UNA sección autogenerada."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    n1 = _nodo("Primer nodo del día", hoy)
    n2 = _nodo("Segundo nodo del día", hoy)
    render_nota_dia(out, "MiProyecto", [n1])
    render_nota_dia(out, "MiProyecto", [n1, n2])
    ruta = _ruta_diario(tmp_path, hoy)
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("🤖 Ingresados por el scanner") == 1
    assert "Segundo nodo del día" in contenido


def test_no_trunca_titulos_a_60(tmp_path):
    """Un título largo se escribe completo (sin [:60])."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    titulo_largo = "x" * 120
    render_nota_dia(out, "MiProyecto", [_nodo(titulo_largo, hoy)])
    ruta = _ruta_diario(tmp_path, hoy)
    assert titulo_largo in ruta.read_text(encoding="utf-8")


def test_tres_builds_tres_nodos_un_bloque(tmp_path):
    """Tres builds con nodos distintos siguen consolidando en un solo bloque."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    for i in range(3):
        nodos = [_nodo(f"Nodo {j}", hoy) for j in range(i + 1)]
        render_nota_dia(out, "MiProyecto", nodos)
    ruta = _ruta_diario(tmp_path, hoy)
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("🤖 Ingresados por el scanner") == 1
    assert "Nodo 0" in contenido and "Nodo 1" in contenido and "Nodo 2" in contenido


def test_preserva_contenido_del_agente_despues_del_scanner(tmp_path):
    """El contenido vivo del agente (después del bloque scanner) NO se pierde.

    Regresión (2026-09-25): ``render_nota_dia`` tomaba solo lo anterior al
    marcador del scanner y descartaba todo lo que venía después (resumen,
    conexiones, notas manuales) al reescribir la sección autogenerada.
    """
    out = str(tmp_path)
    hoy = date.today().isoformat()
    render_nota_dia(out, "MiProyecto", [_nodo("Nodo A", hoy)])
    ruta = _ruta_diario(tmp_path, hoy)

    # El agente agrega una sección propia DESPUÉS del bloque autogenerado.
    contenido = ruta.read_text(encoding="utf-8")
    contenido += "\n## 🛠️ Resumen del agente\n\nTexto vivo que no debe perderse.\n"
    ruta.write_text(contenido, encoding="utf-8")

    # Nuevo build con otro nodo (fuerza reescritura de la sección scanner).
    render_nota_dia(out, "MiProyecto", [_nodo("Nodo A", hoy), _nodo("Nodo B", hoy)])
    final = ruta.read_text(encoding="utf-8")

    assert "## 🛠️ Resumen del agente" in final, "Se perdió el contenido del agente"
    assert "Texto vivo que no debe perderse." in final
    assert "Nodo B" in final
    assert final.count("🤖 Ingresados por el scanner") == 1


def test_excluye_todos_de_codigo_y_conserva_los_conversados(tmp_path):
    """Los TODO crudos del código NO se vuelcan al diario; los conversados sí.

    Dogfooding 2026-10-08: el diario acumulaba volcados de código (p. ej.
    ``TODO (context_map/x.py:L10): return valor``), que son deuda técnica y
    viven en ``5.0-BACKLOG/5.1-Tareas``. El filtro ``_es_todo_codigo`` que ya
    usaban backlog/historial/ideas faltaba en el generador del diario.
    """
    out = str(tmp_path)
    hoy = date.today().isoformat()
    codigo = Node(
        id="t1",
        type="FUTURO",
        title="TODO (context_map/app.py:L10): return valor  # pendiente de tipar",
        created_at=f"{hoy}T10:00:00",
    )
    prueba = Node(
        id="t2",
        type="FUTURO",
        title="TODO (context_map/__tests__/test_x.py:L5): assert algo",
        created_at=f"{hoy}T10:30:00",
    )
    conversado = Node(
        id="t3",
        type="FUTURO",
        title="Revisar el flujo de captura móvil con el usuario",
        created_at=f"{hoy}T11:00:00",
    )

    render_nota_dia(out, "MiProyecto", [codigo, prueba, conversado])
    contenido = _ruta_diario(tmp_path, hoy).read_text(encoding="utf-8")

    assert "Revisar el flujo de captura móvil" in contenido
    assert "return valor" not in contenido
    assert "assert algo" not in contenido


def test_sin_nodos_utiles_no_crea_diario(tmp_path):
    """Un día con solo TODO de código no genera diario (sin ruido)."""
    out = str(tmp_path)
    hoy = date.today().isoformat()
    solo_codigo = Node(
        id="t1",
        type="FUTURO",
        title="TODO (context_map/app.py:L10): def foo(): pass",
        created_at=f"{hoy}T10:00:00",
    )
    assert render_nota_dia(out, "MiProyecto", [solo_codigo]) is None
    assert not _ruta_diario(tmp_path, hoy).exists()


"""Pruebas de la poda de nodos fantasma del grafo.

Caso real (auditoría 2026-11-03): el escáner analizó los worktrees de
``.work/wt-base`` y ``.work/scratch``; al borrarlos, sus entrypoints, TODOs y
el riesgo de complejidad quedaron en ``state/graph.jsonl`` y el vault seguía
dibujando un riesgo sobre archivos inexistentes.
"""

from __future__ import annotations

import json
import os

from context_map.core.models import Edge, Event, Node
from context_map.domain.scanning.poda import (
    es_nodo_podable,
    evento_de_ruta_muerta,
    podar_estado,
    podar_nodos,
    ruta_existe,
    rutas_en_texto,
    sanear_rutas_fantasma,
)


def _escribir_jsonl(ruta: str, registros: list[dict]) -> None:
    """Escribe una lista de registros como JSONL (utilidad de los tests)."""
    with open(ruta, "w", encoding="utf-8") as f:
        for registro in registros:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def test_evento_de_ruta_muerta_frena_la_reingesta() -> None:
    """Los eventos del escáner sobre archivos borrados no vuelven al grafo."""
    fantasma = Event(
        type="BASE",
        text="Entrypoint: .work/scratch/1e21d95a1807/app.py",
        timestamp="2026-10-20T15:58:47",
        source="scanner",
    )
    vivo = Event(
        type="BASE",
        text="Entrypoint: context_map/domain/scanning/poda.py",
        timestamp="2026-11-03T15:00:00",
        source="scanner",
    )
    chat = Event(
        type="IDEA",
        text="Hablemos de .work/viejo.py",
        timestamp="2026-11-03T15:00:00",
        source="chat",
    )
    sin_rutas = Event(
        type="HITO",
        text="Release publicada",
        timestamp="2026-11-03T15:00:00",
        source="scanner",
    )
    raiz = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )

    assert evento_de_ruta_muerta(fantasma, raiz)
    assert not evento_de_ruta_muerta(vivo, raiz)
    assert not evento_de_ruta_muerta(chat, raiz)
    assert not evento_de_ruta_muerta(sin_rutas, raiz)


def test_rutas_en_texto_extrae_separadores_y_lineas() -> None:
    """Reconoce rutas con `/`, con `\\\\` y con el sufijo `:L28` del escáner."""
    texto = (
        "TODO (.work/wt-base/context_map/cli.py:L28): algo. "
        "Archivo: context_map\\domain\\scanning\\poda.py. "
        "Riesgo: a.py, b/c.ts."
    )
    rutas = rutas_en_texto(texto)
    assert ".work/wt-base/context_map/cli.py" in rutas
    assert "context_map/domain/scanning/poda.py" in rutas
    assert "b/c.ts" in rutas
    assert len(rutas) == len(set(rutas))


def test_ruta_existe_tolera_el_saneado_de_tests(tmp_path) -> None:
    """`context_map/__/tests__/x.py` cuenta como viva si existe `__tests__`."""
    carpeta = tmp_path / "context_map" / "__tests__"
    carpeta.mkdir(parents=True)
    (carpeta / "x.py").write_text("", encoding="utf-8")

    assert ruta_existe("context_map/__/tests__/x.py", str(tmp_path))
    assert not ruta_existe("context_map/__tests__/no_existe.py", str(tmp_path))


def test_es_nodo_podable_solo_para_escanner_con_todas_las_rutas_muertas(tmp_path) -> None:
    """Un nodo del escáner con todas sus rutas muertas es podable; el resto no."""
    (tmp_path / "vivo.py").write_text("", encoding="utf-8")

    fantasma = Node(
        id="BASE.1",
        type="BASE",
        title="Entrypoint: .work/wt-base/app.py",
        source="scanner",
        evidence=["Archivo: .work/wt-base/app.py"],
    )
    vivo = Node(
        id="BASE.2",
        type="BASE",
        title="Entrypoint: vivo.py",
        source="scanner",
        evidence=["Archivo: vivo.py"],
    )
    manual = Node(
        id="IDEA.1",
        type="IDEA",
        title="Idea sobre .work/viejo.py",
        source="chat",
    )
    sin_rutas = Node(id="HITO.1", type="HITO", title="Hito sin rutas", source="scanner")

    assert es_nodo_podable(fantasma, str(tmp_path))
    assert not es_nodo_podable(vivo, str(tmp_path))
    assert not es_nodo_podable(manual, str(tmp_path))
    assert not es_nodo_podable(sin_rutas, str(tmp_path))


def test_sanear_riesgo_quita_fantasmas_y_conserva_vivas(tmp_path) -> None:
    """El riesgo mixto pierde las rutas muertas y mantiene la que existe."""
    (tmp_path / "context_map").mkdir()
    (tmp_path / "context_map" / "wiki.py").write_text("", encoding="utf-8")

    riesgo = Node(
        id="RIESGO.1",
        type="RIESGO",
        title=(
            "Archivos de alta complejidad: .work/wt-base/context_map/wiki.py, "
            "context_map/wiki.py, .work/scratch/app.py"
        ),
        summary="Zona de alta complejidad: .work/wt-base/context_map/wiki.py; context_map/wiki.py.",
        source="scanner",
        evidence=["Archivo: .work/wt-base/context_map/wiki.py", "Archivo: context_map/wiki.py"],
    )

    saneado, fantasmas = sanear_rutas_fantasma(riesgo, str(tmp_path))

    assert len(fantasmas) == 2
    assert ".work" not in saneado.title
    assert ".work" not in saneado.summary
    assert "context_map/wiki.py" in saneado.title
    assert saneado.title.count(",") == 0
    assert saneado.evidence == ["Archivo: context_map/wiki.py"]


def test_podar_nodos_elimina_fantasma_y_sus_aristas(tmp_path) -> None:
    """La poda retira el nodo huérfano, sus aristas, y sanea el riesgo mixto."""
    (tmp_path / "context_map").mkdir()
    (tmp_path / "context_map" / "mcp_server.py").write_text("", encoding="utf-8")

    nodos = [
        Node(
            id="FUTURO.1",
            type="FUTURO",
            title="TODO (.work/wt-base/rutas.py:L143): ruido del scanner",
            source="scanner",
            evidence=["Ubicación: .work/wt-base/rutas.py:L143"],
        ),
        Node(
            id="RIESGO.1",
            type="RIESGO",
            title="Archivos de alta complejidad: .work/wt-base/mcp_server.py, context_map/mcp_server.py",
            source="scanner",
            evidence=["Archivo: .work/wt-base/mcp_server.py", "Archivo: context_map/mcp_server.py"],
        ),
        Node(id="IDEA.9", type="IDEA", title="Idea humana intacta", source="chat"),
    ]
    aristas = [
        Edge(source="IDEA.9", target="FUTURO.1", kind="related_to"),
        Edge(source="IDEA.9", target="RIESGO.1", kind="related_to"),
    ]

    conservados, aristas_ok, resultado = podar_nodos(nodos, aristas, str(tmp_path))

    ids = [n.id for n in conservados]
    assert ids == ["RIESGO.1", "IDEA.9"]
    assert resultado.nodos_eliminados == ["FUTURO.1"]
    assert resultado.nodos_saneados == ["RIESGO.1"]
    assert resultado.aristas_eliminadas == 1
    assert [e.target for e in aristas_ok] == ["RIESGO.1"]
    assert ".work" not in conservados[0].title


def test_podar_estado_es_idempotente_y_persiste(tmp_path) -> None:
    """La poda reescribe el estado una vez y la segunda pasada no hace nada."""
    estado = tmp_path / ".context-map" / "state"
    estado.mkdir(parents=True)
    raiz = tmp_path
    _escribir_jsonl(
        str(estado / "graph.jsonl"),
        [
            Node(
                id="BASE.1",
                type="BASE",
                title="Entrypoint: .work/scratch/app.py",
                source="scanner",
                evidence=["Archivo: .work/scratch/app.py"],
            ).to_dict(),
            Node(id="IDEA.1", type="IDEA", title="Idea sin rutas", source="chat").to_dict(),
        ],
    )
    _escribir_jsonl(
        str(estado / "edges.jsonl"),
        [Edge(source="IDEA.1", target="BASE.1", kind="related_to").to_dict()],
    )

    primero = podar_estado(str(estado), str(raiz))
    assert primero.aplicado
    assert primero.nodos_eliminados == ["BASE.1"]
    assert os.path.isfile(str(estado / "edges.jsonl"))
    assert not os.path.exists(str(estado / "graph.jsonl.tmp-poda"))

    with open(estado / "graph.jsonl", encoding="utf-8") as f:
        restantes = [json.loads(linea)["id"] for linea in f if linea.strip()]
    assert restantes == ["IDEA.1"]

    segundo = podar_estado(str(estado), str(raiz))
    assert not segundo.aplicado

"""Poda de nodos fantasma del grafo (rutas que ya no existen en disco).

Motivo real (auditoría 2026-11-03): el escáner analizó los worktrees de
``.work/wt-base`` y ``.work/scratch`` mientras existían. Al borrarlos, sus
nodos (entrypoints, TODOs y el riesgo de complejidad) se quedaron para
siempre en ``state/graph.jsonl``: el grafo es acumulativo y nadie los retiraba,
así que el vault dibujaba un riesgo sobre archivos inexistentes.

La poda es **conservadora** por diseño:

- Solo toca nodos ``source == "scanner"`` del mundo de código (``namespace
  code``): lo que escribió un agente, un chat o el usuario jamás se borra.
- Un nodo se elimina únicamente si **todas** sus rutas citadas están muertas;
  si sobrevive alguna, el nodo se conserva y se **sanean** las menciones
  fantasma (solo en RIESGO, donde las rutas son una lista literal).
- La existencia se comprueba con variantes tolerantes, porque los títulos
  pasan por ``_safe_filename``/``_titulo_limpio`` (``context_map/__tests__``
  se escribe ``context_map/__/tests__`` en algunos campos).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field

from context_map.core.models import Edge, Event, Node

logger = logging.getLogger(__name__)

EXTENSIONES_RUTA = (
    "py|pyi|ts|tsx|js|jsx|mjs|cjs|json|jsonl|md|markdown|yaml|yml|toml|cfg|ini"
    "|html|css|scss|sass|sql|sh|ps1|bat|txt|canvas|vue|svelte|java|kt|go|rs|rb|php|c|h|cpp|hpp|cs"
)
"""Extensiones que identifican una ruta de archivo real dentro de un texto."""

_PATRON_RUTA = re.compile(
    rf"(?:[A-Za-z]:)?[A-Za-z0-9_.\-]*[\\/][A-Za-z0-9_.\-\\/ ]*\.(?:{EXTENSIONES_RUTA})\b"
)
"""Captura rutas con al menos un separador (`/` o `\\`) y extensión conocida."""

_LINEA_CODIGO = re.compile(r":L\d+$")
"""Sufijo de ubicación `:L28` que añade el escáner a los TODOs."""


@dataclass
class ResultadoPoda:
    """Resumen de lo que la poda cambió en el grafo.

    Attributes:
        nodos_eliminados (list[str]): IDs de nodos fantasma retirados.
        nodos_saneados (list[str]): IDs de nodos conservados con rutas muertas
            eliminadas de su texto.
        aristas_eliminadas (int): Aristas retiradas por apuntar a nodos podados.
        aplicado (bool): True si hubo algún cambio persistido en disco.
    """

    nodos_eliminados: list[str] = field(default_factory=list)
    nodos_saneados: list[str] = field(default_factory=list)
    aristas_eliminadas: int = 0
    aplicado: bool = False


def _normalizar_ruta(texto: str) -> str:
    """Normaliza una ruta citada en el grafo para poder comprobarla en disco.

    Args:
        texto (str): Ruta tal cual aparece en el nodo.

    Returns:
        str: Ruta relativa con separadores ``/``, sin prefijo ``./`` ni sufijo
        ``:L28``.
    """
    ruta = texto.strip().strip("`'\"()[]{};,").strip()
    ruta = ruta.replace("\\", "/")
    ruta = _LINEA_CODIGO.sub("", ruta)
    while ruta.startswith("./"):
        ruta = ruta[2:]
    return ruta


def _variantes(ruta: str) -> list[str]:
    """Variantes tolerantes de una ruta (el vault sanea los `__dunder__`).

    ``_safe_filename`` convierte ``context_map/__tests__/x.py`` en
    ``context_map/__/tests__/x.py`` dentro de títulos y evidencias. La
    variante inversa fusiona un segmento que empieza por ``__`` con el
    siguiente, que es exactamente el mangle que introduce el vault.

    Args:
        ruta (str): Ruta ya normalizada.

    Returns:
        list[str]: Variantes a probar contra el sistema de archivos.
    """
    variantes = [ruta]
    partes = ruta.split("/")
    fusion: list[str] = []
    for parte in partes:
        if fusion and fusion[-1] == "__":
            fusion[-1] = f"__{parte}"
        else:
            fusion.append(parte)
    desmangle = "/".join(fusion)
    if desmangle != ruta:
        variantes.append(desmangle)
    return variantes


def rutas_en_texto(texto: str) -> list[str]:
    """Extrae las rutas de archivo citadas en un texto, sin duplicados.

    Args:
        texto (str): Texto del nodo (título, resumen o una evidencia).

    Returns:
        list[str]: Rutas normalizadas en orden de aparición.
    """
    if not texto:
        return []
    vistas: list[str] = []
    for bruta in _PATRON_RUTA.findall(texto):
        ruta = _normalizar_ruta(bruta)
        if ruta and ruta not in vistas:
            vistas.append(ruta)
    return vistas


def ruta_existe(ruta: str, raiz: str) -> bool:
    """Comprueba si una ruta citada existe hoy en el proyecto.

    Args:
        ruta (str): Ruta normalizada (relativa al proyecto).
        raiz (str): Directorio raíz del proyecto.

    Returns:
        bool: True si alguna variante tolerante existe como archivo o carpeta.
    """
    return any(
        os.path.exists(os.path.join(raiz, variante)) for variante in _variantes(ruta)
    )


def rutas_del_nodo(node: Node) -> list[str]:
    """Reúne todas las rutas citadas por un nodo (título, resumen y evidencias).

    Args:
        node (Node): Nodo del grafo.

    Returns:
        list[str]: Rutas normalizadas sin duplicados.
    """
    vistas: list[str] = []
    for texto in [node.title, node.summary, *node.evidence]:
        for ruta in rutas_en_texto(texto):
            if ruta not in vistas:
                vistas.append(ruta)
    return vistas


def es_nodo_podable(node: Node, raiz: str) -> bool:
    """Indica si un nodo quedó huérfano (todas sus rutas ya no existen).

    Un nodo sin rutas citadas nunca se poda: no hay evidencia de que haya
    quedado obsoleto. Los nodos que no vienen del escáner tampoco se tocan.

    Args:
        node (Node): Nodo candidato.
        raiz (str): Directorio raíz del proyecto.

    Returns:
        bool: True si es del escáner, cita rutas y ninguna sigue viva.
    """
    if node.source != "scanner" or node.namespace != "code":
        return False
    rutas = rutas_del_nodo(node)
    if not rutas:
        return False
    return not any(ruta_existe(ruta, raiz) for ruta in rutas)


def _limpiar_separadores(texto: str) -> str:
    """Colapsa separadores sobrantes tras quitar un elemento de una lista.

    Args:
        texto (str): Texto ya saneado.

    Returns:
        str: Texto sin ``, ,``, ``; ;`` ni comas colgando.
    """
    limpio = re.sub(r"\s*[,;]\s*(?=[,;])", "", texto)
    limpio = re.sub(r"[:;]\s*[,;]\s*", ": ", limpio)
    limpio = re.sub(r"\s*[,;]\s*$", "", limpio)
    limpio = re.sub(r"\s{2,}", " ", limpio)
    limpio = re.sub(r"\(\s*[,;]\s*", "(", limpio)
    return limpio.strip()


def _sanear_texto(texto: str, raiz: str) -> tuple[str, int]:
    """Reescribe las listas de rutas de un texto conservando solo las vivas.

    Trabaja por **grupos** de rutas contiguas (separadas solo por comas o
    puntos y coma) y reconstruye el grupo con las supervivientes, manteniendo
    el separador original. Así el saneo no deja comas ni dos puntos colgando.

    Args:
        texto (str): Texto con rutas embebidas (título, resumen o evidencia).
        raiz (str): Directorio raíz del proyecto.

    Returns:
        tuple[str, int]: Texto saneado y número de rutas fantasma retiradas.
    """
    coincidencias = list(_PATRON_RUTA.finditer(texto))
    if not coincidencias:
        return texto, 0

    grupos: list[list[re.Match[str]]] = [[coincidencias[0]]]
    for previa, actual in zip(coincidencias, coincidencias[1:], strict=False):
        entre = texto[previa.end():actual.start()]
        if re.fullmatch(r"[\s,;]*", entre):
            grupos[-1].append(actual)
        else:
            grupos.append([actual])

    piezas: list[str] = []
    posicion = 0
    quitadas = 0
    for grupo in grupos:
        inicio, fin = grupo[0].start(), grupo[-1].end()
        vivas = [
            m for m in grupo
            if ruta_existe(_normalizar_ruta(m.group(0)), raiz)
        ]
        quitadas += len(grupo) - len(vivas)
        piezas.append(texto[posicion:inicio])
        if vivas:
            separador = "; "
            if len(vivas) > 1:
                tramo = texto[vivas[0].end():vivas[1].start()]
                separador = ", " if "," in tramo else "; "
            piezas.append(separador.join(m.group(0).strip() for m in vivas))
        posicion = fin
    piezas.append(texto[posicion:])
    return _limpiar_separadores("".join(piezas)), quitadas


def sanear_rutas_fantasma(node: Node, raiz: str) -> tuple[Node, list[str]]:
    """Quita de un RIESGO las rutas que ya no existen, conservando las vivas.

    Solo se aplica a nodos RIESGO (donde las rutas son una lista literal); en
    otros tipos el texto puede citar rutas de ejemplo dentro de una frase y
    saneado perdería significado.

    Args:
        node (Node): Nodo candidato (se devuelve intacto si no es RIESGO).
        raiz (str): Directorio raíz del proyecto.

    Returns:
        tuple[Node, list[str]]: El nodo (copia si cambió) y las rutas quitadas.
    """
    if node.type != "RIESGO":
        return node, []
    fantasmas = [
        ruta for ruta in rutas_del_nodo(node) if not ruta_existe(ruta, raiz)
    ]
    if not fantasmas:
        return node, []

    nuevo = Node.from_dict(node.to_dict())
    nuevo.title, _ = _sanear_texto(nuevo.title, raiz)
    nuevo.summary, _ = _sanear_texto(nuevo.summary, raiz)

    evidencias: list[str] = []
    for evidencia in nuevo.evidence:
        saneada, quitadas = _sanear_texto(evidencia, raiz)
        if quitadas and not rutas_en_texto(saneada):
            continue  # la evidencia solo hablaba de archivos que ya no están
        evidencias.append(saneada)
    nuevo.evidence = evidencias

    return nuevo, fantasmas


def evento_de_ruta_muerta(event: Event, raiz: str) -> bool:
    """Indica si un evento del escáner solo cita rutas que ya no existen.

    Evita el bucle de los nodos fantasma: `raw/events.jsonl` es memoria histórica
    y conserva eventos de archivos borrados (los worktrees de `.work/`), así que
    sin este filtro cada build los convertía en nodos y la poda tenía que
    retirarlos otra vez.

    Args:
        event (Event): Evento del flujo de ingesta.
        raiz (str): Directorio raíz del proyecto.

    Returns:
        bool: True si el evento es del escáner y ninguna de sus rutas vive.
    """
    if getattr(event, "source", "") != "scanner":
        return False
    rutas = rutas_en_texto(event.text)
    if not rutas:
        return False
    return not any(ruta_existe(ruta, raiz) for ruta in rutas)


def podar_nodos(
    nodes: list[Node],
    edges: list[Edge],
    raiz: str,
) -> tuple[list[Node], list[Edge], ResultadoPoda]:
    """Aplica poda y saneo en memoria sobre un grafo ya cargado.

    Args:
        nodes (list[Node]): Nodos del grafo.
        edges (list[Edge]): Aristas del grafo.
        raiz (str): Directorio raíz del proyecto.

    Returns:
        tuple[list[Node], list[Edge], ResultadoPoda]: Grafo podado y resumen.
    """
    resultado = ResultadoPoda()
    conservados: list[Node] = []
    for node in nodes:
        if es_nodo_podable(node, raiz):
            resultado.nodos_eliminados.append(node.id)
            continue
        saneado, fantasmas = sanear_rutas_fantasma(node, raiz)
        if fantasmas:
            resultado.nodos_saneados.append(node.id)
            logger.debug("Nodo %s: %d ruta(s) fantasma saneadas", node.id, len(fantasmas))
        conservados.append(saneado)

    eliminados = set(resultado.nodos_eliminados)
    if eliminados:
        edges_conservadas = [
            e for e in edges if e.source not in eliminados and e.target not in eliminados
        ]
        resultado.aristas_eliminadas = len(edges) - len(edges_conservadas)
        edges = edges_conservadas

    resultado.aplicado = bool(resultado.nodos_eliminados or resultado.nodos_saneados)
    return conservados, edges, resultado


def _escribir_jsonl_atomico(ruta: str, registros: list[dict]) -> None:
    """Reescribe un JSONL de forma atómica (temporal + ``os.replace``).

    Args:
        ruta (str): Ruta destino del archivo JSONL.
        registros (list[dict]): Registros a persistir.
    """
    temporal = f"{ruta}.tmp-poda"
    with open(temporal, "w", encoding="utf-8") as f:
        for registro in registros:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
    os.replace(temporal, ruta)


def podar_estado(state_dir: str, raiz: str) -> ResultadoPoda:
    """Poda el estado persistido (``graph.jsonl`` y ``edges.jsonl``).

    Es idempotente: si no hay nodos fantasma no reescribe nada.

    Args:
        state_dir (str): Directorio de estado (``.context-map/state``).
        raiz (str): Directorio raíz del proyecto.

    Returns:
        ResultadoPoda: Resumen de la poda (``aplicado`` indica si escribió).
    """
    from context_map.core.storage import load_jsonl

    grafo = os.path.join(state_dir, "graph.jsonl")
    if not os.path.isfile(grafo):
        return ResultadoPoda()
    aristas_path = os.path.join(state_dir, "edges.jsonl")

    nodes = [Node.from_dict(r) for r in load_jsonl(grafo)]
    edges = [Edge.from_dict(r) for r in load_jsonl(aristas_path)]
    conservados, edges_nuevas, resultado = podar_nodos(nodes, edges, raiz)
    if not resultado.aplicado:
        return resultado

    _escribir_jsonl_atomico(grafo, [n.to_dict() for n in conservados])
    if resultado.aristas_eliminadas:
        _escribir_jsonl_atomico(aristas_path, [e.to_dict() for e in edges_nuevas])
    return resultado

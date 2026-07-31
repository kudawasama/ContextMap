"""Modelos del dominio de mapa mental.


Contiene las clases fundamentales:
- `Node`: Nodo del grafo conceptual del proyecto.
- `Edge`: Relación dirigida entre nodos.
- `Event`: Entrada externa normalizada proveniente de chats o JSONL.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

NODE_TYPES: set[str] = {"IDEA", "BASE", "PRUEBA", "FUTURO", "CORRECCION", "RIESGO", "CAMBIO", "HITO"}


def _now() -> str:
    """Devuelve timestamp ISO-8601 compacto para trazabilidad temporal.

    Returns:
        str: Cadena de texto con la fecha y hora actual en formato ISO-8601.
    """
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Node:
    """Nodo del mapa conceptual del proyecto.

    Representa una unidad de significado: una idea, base, prueba, riesgo, etc.

    Attributes:
        id (str): Identificador único del nodo.
        type (str): Tipo del nodo (debe pertenecer a NODE_TYPES).
        title (str): Título representativo del nodo.
        summary (str): Descripción o resumen detallado.
        version (int): Versión del nodo.
        status (str): Estado del nodo ('vigente', 'completado', 'pendiente', etc.).
        tags (List[str]): Etiquetas de categorización.
        source (str): Origen del nodo ('git', 'chat', 'scanner', etc.).
        created_at (str): Timestamp de creación.
        updated_at (str): Timestamp de última actualización.
        depends_on (List[str]): Identificadores de nodos de los que depende.
        blocks (List[str]): Identificadores de nodos que bloquea.
        supersedes (Optional[str]): Identificador del nodo al que reemplaza.
        related_to (List[str]): Identificadores de nodos relacionados.
        evidence (List[str]): Evidencias asociadas (rutas de archivo, líneas, clases).
        classification (str): ID de clasificación semántica ('feature', 'fix', 'refactor', etc.).
    """

    id: str
    type: str
    title: str
    summary: str = ""
    version: int = 1
    status: str = "vigente"
    tags: list[str] = field(default_factory=list)
    source: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    depends_on: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    supersedes: str | None = None
    related_to: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    classification: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serializa el nodo a un diccionario para persistencia en formato JSON/JSONL.

        Returns:
            Dict[str, Any]: Diccionario con todos los atributos del nodo.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Node:
        """Construye e hidrata una instancia de Node a partir de un diccionario.

        Args:
            data (Dict[str, Any]): Diccionario con los datos del nodo.

        Returns:
            Node: Instancia reconstruida del nodo.
        """
        return Node(**data)


@dataclass
class Edge:
    """Arista dirigida entre dos nodos del grafo.

    Attributes:
        source (str): ID del nodo origen.
        target (str): ID del nodo destino.
        kind (str): Tipo de relación ('depends_on', 'blocks', 'supersedes', 'related_to').
        note (str): Nota contextual aclaratoria sobre la relación.
    """

    source: str
    target: str
    kind: str
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serializa la arista a un diccionario.

        Returns:
            Dict[str, Any]: Diccionario con los datos de la arista.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Edge:
        """Construye una arista desde un diccionario.

        Args:
            data (Dict[str, Any]): Diccionario con la información de la arista.

        Returns:
            Edge: Instancia reconstruida de Edge.
        """
        return Edge(**data)


@dataclass
class Event:
    """Evento de entrada normalizado.

    Estructura intermedia para chats exportados, JSONL o eventos de agentes.

    Attributes:
        type (str): Tipo de evento.
        text (str): Contenido textual del evento.
        timestamp (str): Marca temporal del evento.
        source (str): Fuente origen del evento.
        tags (List[str]): Etiquetas asociadas.
        meta (Dict[str, Any]): Metadatos adicionales.
    """

    type: str
    text: str
    timestamp: str
    source: str = ""
    tags: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serializa el evento a diccionario.

        Returns:
            Dict[str, Any]: Diccionario del evento.
        """
        return asdict(self)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Event:
        """Crea una instancia de Event a partir de un diccionario.

        Args:
            data (Dict[str, Any]): Diccionario con datos del evento.

        Returns:
            Event: Instancia reconstruida de Event.
        """
        return Event(**data)

from __future__ import annotations

"""Modelos del dominio de mapa mental.

- `Event`: entrada externa proveniente de chats o JSONL.
- `Node`: nodo del grafo conceptual del proyecto.
- `Edge`: relación dirigida entre nodos.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, List, Dict, Any


NODE_TYPES = {"IDEA", "BASE", "PRUEBA", "FUTURO", "CORRECCION", "RIESGO", "CAMBIO", "HITO"}


def _now() -> str:
    """Devuelve timestamp ISO-8601 compacto para trazabilidad."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Node:
    """Nodo del mapa conceptual del proyecto.

    Representa una unidad de significado: una idea, base, prueba, riesgo, etc.
    """

    id: str
    type: str
    title: str
    summary: str = ""
    version: int = 1
    status: str = "vigente"
    tags: List[str] = field(default_factory=list)
    source: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    depends_on: List[str] = field(default_factory=list)
    blocks: List[str] = field(default_factory=list)
    supersedes: Optional[str] = None
    related_to: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialización para persistencia JSONL."""
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Node":
        """Hidratación desde JSON."""
        return Node(**data)


@dataclass
class Edge:
    """Arista dirigida entre nodos.

    Tipos esperados:
    - `depends_on`
    - `blocks`
    - `supersedes`
    - `related_to`
    """

    source: str
    target: str
    kind: str
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Edge":
        return Edge(**data)


@dataclass
class Event:
    """Evento de entrada normalizado.

    Es la estructura puente para chats exportados, JSONL generado por
    agentes externos o tooling propio.
    """

    type: str
    text: str
    timestamp: str
    source: str = ""
    tags: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Event":
        return Event(**data)

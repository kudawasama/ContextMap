"""Integración con sesiones de Hermes.

Lee el historial de conversaciones y extrae contexto automáticamente.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field


@dataclass
class Mensaje:
    """Un mensaje de la sesión."""
    id: int
    rol: str  # user, assistant, tool
    contenido: str
    timestamp: str = ""
    herramienta: str = ""  # Si es tool call


@dataclass
class Sesion:
    """Una sesión de Hermes."""
    id: str
    titulo: str
    fecha_inicio: str
    mensajes: list[Mensaje] = field(default_factory=list)


def _encontrar_db_sessions() -> str | None:
    """Busca la base de datos de sesiones de Hermes."""
    # Rutas comunes donde Hermes guarda sesiones
    rutas_posibles = [
        os.path.expanduser("~/.hermes/sessions.db"),
        os.path.expanduser("~/AppData/Local/hermes/sessions.db"),
        os.path.expanduser("~/.config/hermes/sessions.db"),
    ]

    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            return ruta

    return None


def leer_sesiones(
    db_path: str | None = None,
    limite: int = 10,
    desde: str | None = None,
) -> list[Sesion]:
    """Lee sesiones de la base de datos de Hermes.

    Args:
        db_path: Ruta a la DB (auto-detecta si es None)
        limite: Máximo de sesiones
        desde: Fecha desde (YYYY-MM-DD)

    Returns:
        Lista de sesiones con mensajes
    """
    if db_path is None:
        db_path = _encontrar_db_sessions()

    if not db_path or not os.path.exists(db_path):
        return []

    sesiones = []

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Buscar sesiones
        query = "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
        if limite:
            query += f" LIMIT {limite}"

        cursor.execute(query)
        filas = cursor.fetchall()

        for fila in filas:
            sesion = Sesion(
                id=str(fila[0]),
                titulo=fila[1] or "Sin título",
                fecha_inicio=fila[2] or "",
            )

            # Leer mensajes de esta sesión
            cursor.execute(
                "SELECT id, role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at",
                (fila[0],)
            )
            mensajes = cursor.fetchall()

            for msg in mensajes:
                sesion.mensajes.append(Mensaje(
                    id=msg[0],
                    rol=msg[1] or "unknown",
                    contenido=msg[2] or "",
                    timestamp=msg[3] or "",
                ))

            sesiones.append(sesion)

        conn.close()

    except Exception as e:
        print(f"Error leyendo sesiones: {e}")

    return sesiones


def extraer_contexto_sesion(sesion: Sesion) -> list[dict]:
    """Extrae contexto relevante de una sesión.

    Returns:
        Lista de diccionarios con tipo, texto, tags
    """
    eventos = []

    for msg in sesion.mensajes:
        if msg.rol == "user":
            # Mensajes del usuario suelen tener peticiones/decisiones
            texto = msg.contenido[:200]
            if any(kw in texto.lower() for kw in ["decid", "quiero", "vamos a", "hagamos"]):
                eventos.append({
                    "type": "IDEA",
                    "text": texto,
                    "source": "chat",
                    "tags": ["decisión", sesion.titulo[:30]],
                })

        elif msg.rol == "assistant":
            # Respuestas del asistente pueden tener análisis
            texto = msg.contenido[:200]
            if any(kw in texto.lower() for kw in ["riesgo", "problema", "cuidado", "atención"]):
                eventos.append({
                    "type": "RIESGO",
                    "text": texto,
                    "source": "chat",
                    "tags": ["análisis", sesion.titulo[:30]],
                })
            elif any(kw in texto.lower() for kw in ["implementar", "crear", "agregar", "nueva"]):
                eventos.append({
                    "type": "IDEA",
                    "text": texto,
                    "source": "chat",
                    "tags": ["implementación", sesion.titulo[:30]],
                })

        elif msg.rol == "tool":
            # Tool calls pueden indicar acciones tomadas
            if msg.herramienta in ["git_commit", "write_file", "patch"]:
                eventos.append({
                    "type": "CAMBIO",
                    "text": f"Herramienta {msg.herramienta} ejecutada",
                    "source": "chat",
                    "tags": ["acción", msg.herramienta],
                })

    return eventos


def importar_sesiones(
    db_path: str | None = None,
    limite: int = 5,
    output_path: str = ".context-map/raw/events.jsonl",
) -> int:
    """Importa sesiones de Hermes como eventos.

    Returns:
        Número de eventos importados
    """
    sesiones = leer_sesiones(db_path, limite)
    eventos_totales = []

    for sesion in sesiones:
        eventos = extraer_contexto_sesion(sesion)
        eventos_totales.extend(eventos)

    # Guardar
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Leer existentes para evitar duplicados
    existentes = set()
    if os.path.exists(output_path):
        with open(output_path, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        obj = json.loads(linea)
                        existentes.add(obj.get("text", "")[:80])
                    except Exception:
                        pass

    # Filtrar nuevos
    nuevos = []
    for e in eventos_totales:
        if e["text"][:80] not in existentes:
            nuevos.append(e)

    # Guardar
    with open(output_path, "a", encoding="utf-8") as f:
        for e in nuevos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return len(nuevos)

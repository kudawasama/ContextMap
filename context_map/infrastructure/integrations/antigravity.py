"""Integración con chats de Antigravity IDE y Antigravity 2.0.

Lee el historial de conversaciones de Antigravity IDE desde:
- ~/.gemini/antigravity-ide/brain/{conversation-id}/.system_generated/messages/*.json
- ~/.gemini/antigravity-ide/conversations/{conversation-id}.db

Y de Antigravity 2.0 desde:
- ~/.gemini/antigravity/ (similar estructura)
"""

from __future__ import annotations

import os
import json
import sqlite3
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from context_map.core.models import Event


@dataclass
class MensajeAntigravity:
    """Representa un mensaje de Antigravity IDE."""
    id: str
    conversation_id: str
    sender: str
    content: str
    timestamp: str
    title: str = ""
    tool_name: str = ""
    tool_args: str = ""


@dataclass
class ConversacionAntigravity:
    """Representa una conversación completa."""
    id: str
    mensajes: List[MensajeAntigravity]
    fecha_inicio: str = ""
    fecha_fin: str = ""
    proyecto: str = ""


def _obtener_ruta_antigravity(ide: bool = True) -> str:
    """Obtiene la ruta base de Antigravity."""
    home = os.path.expanduser("~")
    if ide:
        return os.path.join(home, ".gemini", "antigravity-ide")
    else:
        return os.path.join(home, ".gemini", "antigravity")


def _listar_conversaciones(ruta_base: str) -> List[str]:
    """Lista los IDs de conversaciones disponibles."""
    brain_dir = os.path.join(ruta_base, "brain")
    if not os.path.exists(brain_dir):
        return []

    conversaciones = []
    for item in os.listdir(brain_dir):
        item_path = os.path.join(brain_dir, item)
        if os.path.isdir(item_path):
            # Verificar que tiene mensajes
            msgs_dir = os.path.join(item_path, ".system_generated", "messages")
            if os.path.exists(msgs_dir):
                conversaciones.append(item)

    return conversaciones


def _leer_mensajes_json(conversation_id: str, ruta_brain: str) -> List[MensajeAntigravity]:
    """Lee mensajes desde archivos JSON."""
    mensajes = []
    msgs_dir = os.path.join(ruta_brain, conversation_id, ".system_generated", "messages")

    if not os.path.exists(msgs_dir):
        return mensajes

    for filename in os.listdir(msgs_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(msgs_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Extraer información del mensaje
            msg = MensajeAntigravity(
                id=data.get("id", ""),
                conversation_id=data.get("recipient", conversation_id),
                sender=data.get("sender", ""),
                content=data.get("content", ""),
                timestamp=data.get("timestamp", ""),
                title=data.get("renderDetails", {}).get("messageTitle", ""),
            )

            # Extraer info de herramienta si existe
            source = data.get("sourceMetadata", {})
            if "tool" in source:
                tool = source["tool"]
                msg.tool_name = tool.get("toolCall", {}).get("name", "")
                msg.tool_args = tool.get("toolCall", {}).get("argumentsJson", "")

            if msg.content or msg.title:
                mensajes.append(msg)

        except (json.JSONDecodeError, Exception) as e:
            continue

    return sorted(mensajes, key=lambda m: m.timestamp)


def _leer_conversacion_sqlite(db_path: str) -> List[MensajeAntigravity]:
    """Lee mensajes desde una base de datos SQLite."""
    mensajes = []

    if not os.path.exists(db_path):
        return mensajes

    try:
        conn = sqlite3.connect(db_path)

        # Verificar si existe la tabla steps
        tables = [t[0] for t in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()]

        if "steps" not in tables:
            conn.close()
            return mensajes

        # Leer steps (pasos de la conversación)
        rows = conn.execute("""
            SELECT idx, step_type, status, task_details, step_payload
            FROM steps
            ORDER BY idx
        """).fetchall()

        for row in rows:
            idx, step_type, status, task_details, step_payload = row

            # Los datos están en formato BLOB (protobuf), intentar extraer texto
            content = ""
            if task_details:
                try:
                    # Intentar decodificar como UTF-8
                    content = task_details.decode("utf-8", errors="ignore")
                except:
                    pass

            if step_payload:
                try:
                    content += step_payload.decode("utf-8", errors="ignore")
                except:
                    pass

            if content:
                msg = MensajeAntigravity(
                    id=f"step-{idx}",
                    conversation_id="",
                    sender="antigravity" if step_type == 1 else "user",
                    content=content[:1000],  # Limitar tamaño
                    timestamp="",
                    title=f"Step {idx}",
                )
                mensajes.append(msg)

        conn.close()

    except Exception as e:
        pass

    return mensajes


def leer_conversaciones_antigravity(
    ide: bool = True,
    limite: int = 10
) -> List[ConversacionAntigravity]:
    """Lee conversaciones de Antigravity IDE o 2.0.

    Args:
        ide: True para Antigravity IDE, False para Antigravity 2.0
        limite: Máximo de conversaciones a leer
    """
    ruta_base = _obtener_ruta_antigravity(ide)
    if not os.path.exists(ruta_base):
        return []

    brain_dir = os.path.join(ruta_base, "brain")
    conversations_dir = os.path.join(ruta_base, "conversations")

    conversaciones = []

    # Listar conversaciones desde brain/
    if os.path.exists(brain_dir):
        for item in os.listdir(brain_dir)[:limite]:
            item_path = os.path.join(brain_dir, item)
            if not os.path.isdir(item_path):
                continue

            # Leer mensajes JSON
            mensajes = _leer_mensajes_json(item, brain_dir)

            # Si no hay mensajes JSON, intentar SQLite
            if not mensajes and os.path.exists(conversations_dir):
                db_path = os.path.join(conversations_dir, f"{item}.db")
                if os.path.exists(db_path):
                    mensajes = _leer_conversacion_sqlite(db_path)

            if mensajes:
                # Obtener fechas
                timestamps = [m.timestamp for m in mensajes if m.timestamp]
                fecha_inicio = min(timestamps) if timestamps else ""
                fecha_fin = max(timestamps) if timestamps else ""

                # Determinar proyecto del contexto
                proyecto = _detectar_proyecto(mensajes)

                conv = ConversacionAntigravity(
                    id=item,
                    mensajes=mensajes,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin,
                    proyecto=proyecto,
                )
                conversaciones.append(conv)

    return conversaciones


def _detectar_proyecto(mensajes: List[MensajeAntigravity]) -> str:
    """Detecta el proyecto del contexto de la conversación."""
    for msg in mensajes:
        # Buscar rutas de proyecto en los argumentos de herramientas
        if msg.tool_args:
            try:
                args = json.loads(msg.tool_args)
                cwd = args.get("Cwd", "")
                if cwd:
                    # Extraer nombre del proyecto
                    parts = cwd.replace("\\", "/").split("/")
                    if len(parts) >= 2:
                        return parts[-1]
            except:
                pass

        # Buscar en el contenido
        if "CotanoPet" in msg.content:
            return "CotanoPet"
        elif "Bot_AX" in msg.content:
            return "Bot_AX_Contable"
        elif "AlgorFut" in msg.content:
            return "AlgorFut"
        elif "ContextMap" in msg.content or "context-map" in msg.content:
            return "ContextMap"

    return ""


def clasificar_mensaje(msg: MensajeAntigravity) -> str:
    """Clasifica un mensaje de Antigravity."""
    content_lower = msg.content.lower()
    title_lower = msg.title.lower()

    # Clasificar por tipo de acción
    if msg.tool_name == "run_command":
        return "COMANDO"
    elif msg.tool_name in ("write_file", "create_file"):
        return "CREACION"
    elif msg.tool_name in ("edit_file", "patch"):
        return "EDICION"
    elif msg.tool_name in ("read_file", "search"):
        return "LECTURA"
    elif "error" in content_lower or "fallo" in content_lower:
        return "ERROR"
    elif "fix" in content_lower or "correc" in content_lower:
        return "CORRECCION"
    elif "feat" in content_lower or "add" in content_lower:
        return "IDEA"
    elif "test" in content_lower:
        return "PRUEBA"
    elif "todo" in content_lower or "pendiente" in content_lower:
        return "FUTURO"
    else:
        return "CAMBIO"


def es_mensaje_ruido(msg: MensajeAntigravity) -> bool:
    """Determina si un mensaje es ruido (no informativo)."""
    content_lower = msg.content.lower() if msg.content else ""
    title_lower = msg.title.lower() if msg.title else ""

    # Patrones de ruido
    ruido = [
        "checking if",
        "notice all your",
        "the agent",
        "background tasks",
        "validation log",
        "has been stopped",
        "has completed",
        "without warnings",
        "conversa",  # Mensajes truncados
    ]

    for patron in ruido:
        if patron in content_lower or patron in title_lower:
            return True

    # Mensajes muy cortos (menos de 10 chars)
    if msg.content and len(msg.content.strip()) < 10:
        return True

    # Detectar caracteres de control (datos corruptos)
    if msg.content:
        control_chars = sum(1 for c in msg.content if ord(c) < 32 or ord(c) > 126)
        if control_chars > 5:
            return True

    # Títulos vacíos o con solo espacios
    if not msg.title or not msg.title.strip():
        return True

    return False


def importar_antigravity(
    ide: bool = True,
    limite: int = 5,
    output_path: str = None,
) -> int:
    """Importa conversaciones de Antigravity como eventos.

    Args:
        ide: True para Antigravity IDE, False para 2.0
        limite: Máximo de conversaciones
        output_path: Ruta donde guardar events.jsonl

    Returns:
        Número de eventos importados
    """
    conversaciones = leer_conversaciones_antigravity(ide, limite)
    eventos = []

    nombre_herramienta = "Antigravity IDE" if ide else "Antigravity 2.0"

    for conv in conversaciones:
        # Evento BASE de la conversación
        eventos.append(Event(
            type="BASE",
            text=f"Conversación en {nombre_herramienta}: {conv.proyecto or 'general'} "
                 f"({len(conv.mensajes)} mensajes)",
            timestamp=conv.fecha_inicio,
            source="antigravity-ide" if ide else "antigravity-2",
            tags=["antigravity", conv.proyecto.lower()] if conv.proyecto else ["antigravity"],
        ))

        # Clasificar y agregar eventos por mensaje significativo
        for msg in conv.mensajes[:20]:  # Últimos 20 mensajes
            # Filtrar ruido
            if es_mensaje_ruido(msg):
                continue

            tipo = clasificar_mensaje(msg)

            # Crear evento con contexto
            texto = msg.content[:200] if msg.content else msg.title
            if msg.tool_name:
                texto = f"[{msg.tool_name}] {texto}"

            eventos.append(Event(
                type=tipo,
                text=texto,
                timestamp=msg.timestamp,
                source="antigravity-ide" if ide else "antigravity-2",
                tags=["antigravity", tipo.lower()],
                meta={
                    "conversation_id": conv.id,
                    "tool": msg.tool_name,
                    "project": conv.proyecto,
                },
            ))

    # Guardar eventos
    if output_path and eventos:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as f:
            for evento in eventos:
                f.write(json.dumps({
                    "type": evento.type,
                    "text": evento.text,
                    "timestamp": evento.timestamp,
                    "source": evento.source,
                    "tags": evento.tags,
                }) + "\n")

    return len(eventos)

"""Integración con chats de Antigravity IDE y Antigravity 2.0.

Lee el historial de conversaciones de Antigravity IDE desde:
- ~/.gemini/antigravity-ide/brain/{conversation-id}/.system_generated/messages/*.json
- ~/.gemini/antigravity-ide/conversations/{conversation-id}.db

Y de Antigravity 2.0 desde:
- ~/.gemini/antigravity/ (similar estructura)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass

from context_map.core.models import Event

logger = logging.getLogger(__name__)


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
    mensajes: list[MensajeAntigravity]
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


def _listar_conversaciones(ruta_base: str) -> list[str]:
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


def _leer_mensajes_json(conversation_id: str, ruta_brain: str) -> list[MensajeAntigravity]:
    """Lee mensajes desde archivos JSON."""
    mensajes: list[MensajeAntigravity] = []
    msgs_dir = os.path.join(ruta_brain, conversation_id, ".system_generated", "messages")

    if not os.path.exists(msgs_dir):
        return mensajes

    for filename in os.listdir(msgs_dir):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join(msgs_dir, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
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

        except Exception as err:
            logger.debug("Mensaje Antigravity no procesable: %s", err)
            continue

    return sorted(mensajes, key=lambda m: m.timestamp)


def _decodificar_blob(datos: object) -> str:
    """Decodifica un BLOB en texto UTF-8 (tolerante a errores).

    Args:
        datos (object): BLOB o None.

    Returns:
        str: Texto decodificado, o string vacío si no hay datos.
    """
    if not datos:
        return ""
    try:
        return datos.decode("utf-8", errors="ignore")
    except Exception as err:
        logger.debug("No se pudo decodificar BLOB: %s", err)
        return ""


def _es_mensaje_step(row) -> MensajeAntigravity | None:
    """Convierte una fila de ``steps`` en un MensajeAntigravity.

    Args:
        row: Fila con (idx, step_type, status, task_details, step_payload).

    Returns:
        MensajeAntigravity | None: Mensaje si la fila tiene contenido, o None.
    """
    idx, step_type, status, task_details, step_payload = row
    content = _decodificar_blob(task_details) + _decodificar_blob(step_payload)
    if not content:
        return None
    return MensajeAntigravity(
        id=f"step-{idx}",
        conversation_id="",
        sender="antigravity" if step_type == 1 else "user",
        content=content[:1000],  # Limitar tamaño
        timestamp="",
        title=f"Step {idx}",
    )


def _leer_conversacion_sqlite(db_path: str) -> list[MensajeAntigravity]:
    """Lee mensajes desde una base de datos SQLite."""
    mensajes: list[MensajeAntigravity] = []

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
            msg = _es_mensaje_step(row)
            if msg:
                mensajes.append(msg)

        conn.close()

    except Exception as err:
        logger.warning("No se pudo leer la base SQLite %s: %s", db_path, err)

    return mensajes


def _cargar_mensajes_conversacion(
    item: str,
    brain_dir: str,
    conversations_dir: str,
) -> list[MensajeAntigravity]:
    """Carga los mensajes de una conversación (JSON, con fallback SQLite).

    Args:
        item (str): Id de la conversación (carpeta en brain/).
        brain_dir (str): Directorio ``brain`` de Antigravity.
        conversations_dir (str): Directorio ``conversations`` de Antigravity.

    Returns:
        list[MensajeAntigravity]: Mensajes encontrados (JSON o SQLite).
    """
    mensajes = _leer_mensajes_json(item, brain_dir)
    if mensajes or not os.path.exists(conversations_dir):
        return mensajes
    db_path = os.path.join(conversations_dir, f"{item}.db")
    if os.path.exists(db_path):
        return _leer_conversacion_sqlite(db_path)
    return mensajes


def _construir_conversacion(item: str, mensajes: list[MensajeAntigravity]) -> ConversacionAntigravity:
    """Construye una ConversacionAntigravity desde sus mensajes.

    Args:
        item (str): Id de la conversación.
        mensajes (list[MensajeAntigravity]): Mensajes de la conversación.

    Returns:
        ConversacionAntigravity: Conversación con fechas y proyecto detectados.
    """
    timestamps = [m.timestamp for m in mensajes if m.timestamp]
    fecha_inicio = min(timestamps) if timestamps else ""
    fecha_fin = max(timestamps) if timestamps else ""
    proyecto = _detectar_proyecto(mensajes)
    return ConversacionAntigravity(
        id=item,
        mensajes=mensajes,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        proyecto=proyecto,
    )


def leer_conversaciones_antigravity(
    ide: bool = True,
    limite: int = 10
) -> list[ConversacionAntigravity]:
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

            # Leer mensajes JSON (con fallback SQLite)
            mensajes = _cargar_mensajes_conversacion(item, brain_dir, conversations_dir)

            if mensajes:
                conversaciones.append(_construir_conversacion(item, mensajes))

    return conversaciones


def _detectar_proyecto(mensajes: list[MensajeAntigravity]) -> str:
    """Detecta el proyecto del contexto de la conversación."""
    for msg in mensajes:
        # Buscar rutas de proyecto en los argumentos de herramientas
        proyecto_tool = _proyecto_desde_tool(msg)
        if proyecto_tool:
            return proyecto_tool

        # Buscar en el contenido
        proyecto_contenido = _proyecto_desde_contenido(msg.content)
        if proyecto_contenido:
            return proyecto_contenido

    return ""


_PROYECTOS_CONOCIDOS: list[tuple[str, str]] = [
    ("CotanoPet", "CotanoPet"),
    ("Bot_AX", "Bot_AX_Contable"),
    ("AlgorFut", "AlgorFut"),
]


def _proyecto_desde_contenido(contenido: str) -> str:
    """Detecta un proyecto conocido mencionado en el contenido del mensaje.

    Args:
        contenido (str): Contenido del mensaje.

    Returns:
        str: Nombre del proyecto detectado, o string vacío.
    """
    if not contenido:
        return ""
    for marca, proyecto in _PROYECTOS_CONOCIDOS:
        if marca in contenido:
            return proyecto
    if "ContextMap" in contenido or "context-map" in contenido:
        return "ContextMap"
    return ""


def _proyecto_desde_tool(msg: MensajeAntigravity) -> str:
    """Extrae el proyecto desde el argumento ``Cwd`` de una herramienta.

    Args:
        msg (MensajeAntigravity): Mensaje a analizar.

    Returns:
        str: Nombre del proyecto desde Cwd, o string vacío.
    """
    if not msg.tool_args:
        return ""
    try:
        args = json.loads(msg.tool_args)
        cwd = args.get("Cwd", "")
        if cwd:
            parts = cwd.replace("\\", "/").split("/")
            if len(parts) >= 2:
                return str(parts[-1])
    except (json.JSONDecodeError, ValueError, TypeError) as err:
        logger.debug("Tool args no parseables: %s", err)
    return ""


# Reglas de clasificación por tipo de acción: (criterio, tipo) evaluadas en orden.
_REGLAS_CLASIFICACION: list[tuple[str, str]] = [
    ("run_command", "COMANDO"),
    ("write_file", "CREACION"),
    ("create_file", "CREACION"),
    ("edit_file", "EDICION"),
    ("patch", "EDICION"),
    ("read_file", "LECTURA"),
    ("search", "LECTURA"),
]

# Reglas de clasificación por contenido: (marcas de texto, tipo).
_REGLAS_CLASIFICACION_CONTENIDO: list[tuple[tuple[str, ...], str]] = [
    (("error", "fallo"), "ERROR"),
    (("fix", "correc"), "CORRECCION"),
    (("feat", "add"), "IDEA"),
    (("test",), "PRUEBA"),
    (("todo", "pendiente"), "FUTURO"),
]


def clasificar_mensaje(msg: MensajeAntigravity) -> str:
    """Clasifica un mensaje de Antigravity por tipo de acción.

    Args:
        msg (MensajeAntigravity): Mensaje a clasificar.

    Returns:
        str: Tipo semántico del mensaje (COMANDO, CREACION, EDICION...).
    """
    content_lower = msg.content.lower()

    # Clasificar por tool_name primero (tabla de reglas)
    for tool, tipo in _REGLAS_CLASIFICACION:
        if msg.tool_name == tool:
            return tipo

    # Clasificar por contenido (tabla de marcas de texto)
    for marcas, tipo in _REGLAS_CLASIFICACION_CONTENIDO:
        if any(marca in content_lower for marca in marcas):
            return tipo
    return "CAMBIO"


_PATRONES_RUIDO: list[str] = [
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


def _ruido_por_patron(content_lower: str, title_lower: str) -> bool:
    """True si el mensaje contiene algún patrón de ruido conocido.

    Args:
        content_lower (str): Contenido en minúsculas.
        title_lower (str): Título en minúsculas.

    Returns:
        bool: True si coincide algún patrón.
    """
    return any(p in content_lower or p in title_lower for p in _PATRONES_RUIDO)


def _es_contenido_corrupto(content: str) -> bool:
    """True si el contenido tiene demasiados caracteres de control (datos corruptos).

    Args:
        content (str): Contenido del mensaje.

    Returns:
        bool: True si el contenido parece corrupto.
    """
    if not content:
        return False
    control_chars = sum(1 for c in content if ord(c) < 32 or ord(c) > 126)
    return control_chars > 5


def es_mensaje_ruido(msg: MensajeAntigravity) -> bool:
    """Determina si un mensaje es ruido (no informativo).

    Args:
        msg (MensajeAntigravity): Mensaje a evaluar.

    Returns:
        bool: True si el mensaje debe descartarse como ruido.
    """
    content_lower = msg.content.lower() if msg.content else ""
    title_lower = msg.title.lower() if msg.title else ""

    if _ruido_por_patron(content_lower, title_lower):
        return True
    if msg.content and len(msg.content.strip()) < 10:
        return True  # Mensajes muy cortos (menos de 10 chars)
    if _es_contenido_corrupto(msg.content):
        return True  # Detectar caracteres de control (datos corruptos)
    return bool(not msg.title or not msg.title.strip())  # Títulos vacíos


def _evento_conversacion(conv: ConversacionAntigravity, ide: bool) -> Event:
    """Crea el evento BASE de una conversación de Antigravity.

    Args:
        conv (ConversacionAntigravity): Conversación importada.
        ide (bool): True si es Antigravity IDE, False si es 2.0.

    Returns:
        Event: Evento BASE con la información de la conversación.
    """
    nombre_herramienta = "Antigravity IDE" if ide else "Antigravity 2.0"
    return Event(
        type="BASE",
        text=f"Conversación en {nombre_herramienta}: {conv.proyecto or 'general'} "
             f"({len(conv.mensajes)} mensajes)",
        timestamp=conv.fecha_inicio,
        source="antigravity-ide" if ide else "antigravity-2",
        tags=["antigravity", conv.proyecto.lower()] if conv.proyecto else ["antigravity"],
    )


def _eventos_mensajes(conv: ConversacionAntigravity, ide: bool) -> list[Event]:
    """Convierte los mensajes significativos de una conversación en eventos.

    Descarta ruido y clasifica cada mensaje por tipo de acción; cada evento
    conserva el id de conversación, la herramienta y el proyecto en ``meta``.

    Args:
        conv (ConversacionAntigravity): Conversación importada.
        ide (bool): True si es Antigravity IDE, False si es 2.0.

    Returns:
        list[Event]: Eventos por mensaje significativo.
    """
    eventos: list[Event] = []
    for msg in conv.mensajes[:20]:  # Últimos 20 mensajes
        if es_mensaje_ruido(msg):
            continue

        tipo = clasificar_mensaje(msg)
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
    return eventos


def importar_antigravity(
    ide: bool = True,
    limite: int = 5,
    output_path: str | None = None,
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

    for conv in conversaciones:
        # Evento BASE de la conversación
        eventos.append(_evento_conversacion(conv, ide))
        # Clasificar y agregar eventos por mensaje significativo
        eventos.extend(_eventos_mensajes(conv, ide))

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

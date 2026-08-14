"""Integración con sesiones de Hermes.

Lee el historial de conversaciones y extrae contexto automáticamente.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


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
    cwd: str = ""
    git_repo_root: str = ""


def _encontrar_db_sessions() -> str | None:
    """Busca la base de datos de sesiones de Hermes.

    Hermes guarda las sesiones en ``state.db`` (no ``sessions.db``) dentro de
    su HERMES_HOME. En Windows el home está en ``%LOCALAPPDATA%/hermes``; en
    Unix en ``~/.hermes``. También revisa los homes de perfiles
    (``profiles/<nombre>/state.db``).

    Returns:
        str | None: Ruta a la DB de sesiones o None.
    """
    import glob

    candidatos = [
        os.path.expanduser("~/.hermes/state.db"),
        os.path.expanduser("~/AppData/Local/hermes/state.db"),
        os.path.expanduser("~/.config/hermes/state.db"),
        # compatibilidad con la convención vieja sessions.db
        os.path.expanduser("~/.hermes/sessions.db"),
        os.path.expanduser("~/AppData/Local/hermes/sessions.db"),
        os.path.expanduser("~/.config/hermes/sessions.db"),
    ]
    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta

    # homes de perfiles: <root>/profiles/<nombre>/state.db
    for patron in (
        os.path.expanduser("~/.hermes/profiles/*/state.db"),
        os.path.expanduser("~/AppData/Local/hermes/profiles/*/state.db"),
        os.path.expanduser("~/.config/hermes/profiles/*/state.db"),
    ):
        coincidencias = glob.glob(patron)
        if coincidencias:
            return coincidencias[0]

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

        # Detectar columnas reales (state.db moderno: started_at/timestamp;
        # convención vieja: created_at)
        cols_sessions = [r[1] for r in cursor.execute("PRAGMA table_info(sessions)")]
        cols_messages = [r[1] for r in cursor.execute("PRAGMA table_info(messages)")]
        col_fecha_s = "started_at" if "started_at" in cols_sessions else ("created_at" if "created_at" in cols_sessions else "id")
        col_fecha_m = "timestamp" if "timestamp" in cols_messages else ("created_at" if "created_at" in cols_messages else "id")

        # Buscar sesiones (incluye cwd/git_repo_root para filtrar por proyecto)
        cols_con = [c for c in cols_sessions if c in ("cwd", "git_repo_root")]
        cols_sel = ", ".join(cols_con)
        query = (
            f"SELECT id, title, {col_fecha_s}"
            + (f", {cols_sel}" if cols_sel else "")
            + f" FROM sessions ORDER BY {col_fecha_s} DESC"
        )
        if limite:
            query += f" LIMIT {limite}"

        cursor.execute(query)
        filas = cursor.fetchall()

        for fila in filas:
            sesion = Sesion(
                id=str(fila[0]),
                titulo=fila[1] or "Sin título",
                fecha_inicio=str(fila[2] or ""),
            )
            if cols_con:
                sesion.cwd = str(fila[3] or "")
                if len(cols_con) > 1:
                    sesion.git_repo_root = str(fila[4] or "")

            # Leer mensajes de esta sesión
            cursor.execute(
                f"SELECT id, role, content, {col_fecha_m} FROM messages WHERE session_id = ? ORDER BY {col_fecha_m}",
                (fila[0],)
            )
            mensajes = cursor.fetchall()

            for msg in mensajes:
                sesion.mensajes.append(Mensaje(
                    id=msg[0],
                    rol=msg[1] or "unknown",
                    contenido=msg[2] or "",
                    timestamp=str(msg[3] or ""),
                ))

            sesiones.append(sesion)

        conn.close()

    except Exception as e:
        logger.warning("Error leyendo sesiones de Hermes: %s", e)

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
            texto_low = texto.lower()
            # Patrones de CIERRE (R6, auditoría 2026-08-14): mensajes que
            # declaran una decisión tomada, un cambio implementado o una
            # lección aprendida se clasifican con tipos específicos, ANTES
            # de los genéricos (p. ej. "implementado" también contiene
            # "implementar" y caería en IDEA).
            if any(kw in texto_low for kw in ["lección", "leccion", "aprendizaje"]):
                eventos.append({
                    "type": "LECCION",
                    "text": texto,
                    "source": "chat",
                    "tags": ["lección", sesion.titulo[:30]],
                })
            elif any(kw in texto_low for kw in [
                "quedó implementado", "quedo implementado", "commit ",
                "pusheado", "desplegado", "verificado en producción",
            ]):
                eventos.append({
                    "type": "CORRECCION",
                    "text": texto,
                    "source": "chat",
                    "tags": ["implementación", sesion.titulo[:30]],
                })
            elif any(kw in texto_low for kw in [
                "regla definitiva", "decisión", "decision", "confirmado por el usuario",
                "el usuario rechazó", "el usuario rechazo", "acordamos", "acordado",
            ]):
                eventos.append({
                    "type": "DECISION",
                    "text": texto,
                    "source": "chat",
                    "tags": ["decisión", sesion.titulo[:30]],
                })
            elif any(kw in texto_low for kw in ["riesgo", "problema", "cuidado", "atención"]):
                eventos.append({
                    "type": "RIESGO",
                    "text": texto,
                    "source": "chat",
                    "tags": ["análisis", sesion.titulo[:30]],
                })
            elif any(kw in texto_low for kw in ["implementar", "crear", "agregar", "nueva"]):
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
    project: str = "",
) -> int:
    """Importa sesiones de Hermes como eventos.

    Args:
        db_path (str | None): Ruta a la DB de sesiones (None = autodetecta).
        limite (int): Máximo de sesiones a leer.
        output_path (str): Archivo de eventos de salida.
        project (str): Nombre del proyecto — si se pasa, solo se importan
            sesiones cuyo cwd/git_repo_root/título lo mencionen (evita
            contaminar el vault con sesiones de otros proyectos).

    Returns:
        Número de eventos importados
    """
    sesiones = leer_sesiones(db_path, limite)
    if project:
        p = project.lower()
        sesiones = [
            s for s in sesiones
            if p in f"{s.cwd} {s.git_repo_root} {s.titulo}".lower()
        ]
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
                    except Exception as err:
                        logger.debug("Línea no JSON en %s: %s", output_path, err)

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

"""Integración con sesiones de Hermes.

Lee el historial de conversaciones y extrae contexto automáticamente.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime

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


def _a_iso(valor: object) -> str:
    """Normaliza una fecha de Hermes a ISO-8601.

    El ``state.db`` moderno guarda ``sessions.started_at`` y
    ``messages.timestamp`` como epoch Unix (segundos, a veces con decimales).
    El importador los propagaba en crudo, así que los eventos derivados de las
    conversaciones quedaban sin fecha: 305 de los 313 eventos sin fecha de la
    BD personal venían de aquí, y sin fecha el historial por día no los ve.

    Args:
        valor (object): Epoch (numérico o texto) o fecha ISO.

    Returns:
        str: Fecha ISO-8601 con segundos, o cadena vacía si no es interpretable.
    """
    if valor is None or valor == "":
        return ""
    texto = str(valor).strip()
    try:
        return datetime.fromtimestamp(float(texto)).isoformat(timespec="seconds")
    except (OverflowError, OSError, ValueError):
        pass
    try:
        return datetime.fromisoformat(texto.replace("Z", "+00:00")).isoformat(timespec="seconds")
    except ValueError:
        logger.debug("Fecha no interpretable de Hermes: %r", valor)
        return ""


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
        params: list[int] = []
        if limite:
            query += " LIMIT ?"
            params.append(int(limite))

        cursor.execute(query, tuple(params))
        filas = cursor.fetchall()

        for fila in filas:
            sesion = Sesion(
                id=str(fila[0]),
                titulo=fila[1] or "Sin título",
                fecha_inicio=_a_iso(fila[2]),
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
                    timestamp=_a_iso(msg[3]),
                ))

            sesiones.append(sesion)

        conn.close()

    except Exception as e:
        logger.warning("Error leyendo sesiones de Hermes: %s", e)

    return sesiones


def extraer_contexto_sesion(sesion: Sesion) -> list[dict]:
    """Extrae contexto relevante de una sesión.

    Cada evento hereda la fecha del mensaje que lo originó (o la de inicio de la
    sesión). Sin ella, el evento queda fuera de todo historial por día.

    Returns:
        Lista de diccionarios con tipo, texto, timestamp, source y tags.
    """
    eventos: list[dict[str, object]] = []

    for msg in sesion.mensajes:
        inicio = len(eventos)
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

        # Fecha del mensaje (o de la sesión) para todo lo que generó este mensaje
        fecha = msg.timestamp or sesion.fecha_inicio
        for evento in eventos[inicio:]:
            evento["timestamp"] = fecha

    return eventos


def _leer_alias_proyecto(ruta_raiz: str) -> list[str]:
    """Lee alias de nombres o carpetas configurados para el proyecto.

    Busca en ``.context-map/config.json`` el campo ``alias`` o ``alias_carpetas``.
    Si no existe o no se puede leer, devuelve lista vacía.

    Args:
        ruta_raiz: Ruta del directorio raíz del proyecto.

    Returns:
        list[str]: Lista de alias en minúsculas.
    """
    if not ruta_raiz:
        return []
    cfg_path = os.path.join(ruta_raiz, ".context-map", "config.json")
    if not os.path.isfile(cfg_path):
        return []
    try:
        with open(cfg_path, encoding="utf-8") as f:
            data = json.load(f)
        aliases = data.get("alias") or data.get("alias_carpetas") or data.get("aliases") or []
        if isinstance(aliases, str):
            return [aliases.strip()]
        return [str(a).strip() for a in aliases if str(a).strip()]
    except Exception:
        return []


def sesion_es_del_proyecto(
    sesion: Sesion,
    proyecto: str = "",
    ruta_raiz: str = "",
    alias: list[str] | None = None,
) -> bool:
    """Indica si una sesión de Hermes pertenece a un proyecto concreto.

    Predicado compartido por el importador (``importar_sesiones``) y por la
    señal de frescura (``signals.sesiones_posteriores``). Permite asociar sesiones
    por coincidencia de ruta, nombre de proyecto o alias históricos (T2.6).

    Args:
        sesion (Sesion): Sesión leída de Hermes.
        proyecto (str): Nombre del proyecto (se busca en cwd, repo y título).
        ruta_raiz (str): Ruta del proyecto; habilita la comparación por ruta.
        alias (list[str] | None): Lista opcional de alias de nombres/carpetas.

    Returns:
        bool: True si la sesión pertenece al proyecto.
    """
    cwd = str(getattr(sesion, "cwd", "") or "")
    repo = str(getattr(sesion, "git_repo_root", "") or "")
    titulo = str(getattr(sesion, "titulo", "") or "")

    if ruta_raiz:
        raiz = os.path.normcase(os.path.abspath(ruta_raiz))
        for valor in (cwd, repo):
            if not valor:
                continue
            ruta = os.path.normcase(os.path.abspath(valor))
            if ruta == raiz or ruta.startswith(raiz + os.sep):
                return True

    nombres_candidatos: list[str] = []
    if proyecto:
        nombres_candidatos.append(proyecto.lower())

    if alias:
        nombres_candidatos.extend([a.lower() for a in alias if a])
    elif ruta_raiz:
        for a in _leer_alias_proyecto(ruta_raiz):
            nombres_candidatos.append(a.lower())

    for nom in nombres_candidatos:
        if any(nom in valor.lower() for valor in (cwd, repo, titulo)):
            return True

    return not proyecto and not ruta_raiz and not alias


def importar_sesiones(
    db_path: str | None = None,
    limite: int = 5,
    output_path: str = ".context-map/raw/events.jsonl",
    project: str = "",
    target_dir: str = ".",
    alias: list[str] | None = None,
) -> int:
    """Importa sesiones de Hermes como eventos.

    Args:
        db_path (str | None): Ruta a la DB de sesiones (None = autodetecta).
        limite (int): Máximo de sesiones a leer.
        output_path (str): Archivo de eventos de salida.
        project (str): Nombre del proyecto para filtrar sesiones.
        target_dir (str): Directorio del proyecto para resolver rutas y alias.
        alias (list[str] | None): Alias opcionales para matching de sesiones.

    Returns:
        int: Número de eventos importados.
    """
    sesiones = leer_sesiones(db_path, limite)
    if project or target_dir:
        sesiones = [
            s
            for s in sesiones
            if sesion_es_del_proyecto(s, project, target_dir, alias=alias)
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

"""Base de datos personal de ContextMap (SQLite + FTS5).

Capa consolidada y transportable de contexto: un único archivo ``.db`` que
acumula eventos, lecciones, decisiones y sesiones de TODOS los proyectos
registrados, independiente del vault Obsidian de cada proyecto.

Características de diseño:

- **Transportable**: la BD vive por defecto en el disco F: (``/mnt/fdrive``
  en Linux, ``F:\\`` en Windows) o en un pendrive; se usa desde la ruta que
  sea y se copia/desmonta como un solo archivo.
- **Idempotente**: cada registro se identifica por hash SHA-256 de su
  contenido; re-sincronizar nunca duplica.
- **Consultable**: índice FTS5 (búsqueda full-text) sobre eventos, lecciones
  y decisiones para responder consultas con pocos tokens.
- **Dos capas**: los archivos ``.context-map/`` de cada proyecto siguen
  siendo la fuente de verdad local; esta BD es el filtro + almacenaje global.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constantes y resolución de rutas
# ---------------------------------------------------------------------------

ENV_DB_PATH: str = "CTXMAP_PERSONAL_DB"
"""Variable de entorno que sobreescribe la ruta por defecto de la BD."""

FALLBACK_DIR: str = ".context-map/personal"
"""Directorio de respaldo cuando no hay disco F: ni pendrive montado."""


def resolver_ruta_bd(db_path: str | None = None) -> str:
    """Resuelve la ruta de la base de datos personal por jerarquía.

    Orden de prioridad:
    1. Argumento explícito ``--db`` (pendrive, ruta custom).
    2. Variable de entorno ``CTXMAP_PERSONAL_DB``.
    3. Disco F: montado (``/mnt/fdrive`` en Linux, ``F:\\`` en Windows).
    4. Respaldo local ``~/.context-map/personal/personal.db``.

    Args:
        db_path: Ruta explícita proporcionada por el usuario (o None).

    Returns:
        str: Ruta absoluta al archivo de base de datos.
    """
    if db_path:
        return os.path.abspath(os.path.expanduser(db_path))

    env = os.environ.get(ENV_DB_PATH)
    if env:
        return os.path.abspath(os.path.expanduser(env))

    if os.name == "nt":  # Windows: disco F:
        if os.path.exists("F:\\") and os.access("F:\\", os.W_OK):
            return "F:\\context-map\\personal.db"
    else:  # Linux/macOS: montaje típico del F: compartido
        for mount in ("/mnt/fdrive", "/media/fdrive", "/run/media/fdrive"):
            # Un mount activo es escribible por el usuario; un directorio
            # vacío root:root (sin montaje) NO — se evita el falso positivo.
            if os.path.isdir(mount) and os.access(mount, os.W_OK):
                return os.path.join(mount, "context-map", "personal.db")

    home = os.path.expanduser("~")
    return os.path.join(home, FALLBACK_DIR, "personal.db")


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------


@dataclass
class Leccion:
    """Lección de conocimiento accionable (formato 8.0-KNOWLEDGE).

    Attributes:
        leccion: Enunciado de la lección aprendida.
        como_se_resolvio: Cómo se resolvió el problema.
        prompt: Prompt específico que funcionó.
        instruccion: Instrucción específica derivada.
        conexiones: Notas de contexto o enlaces relacionados.
        proyecto: Nombre del proyecto de origen (opcional).
        tags: Etiquetas de categorización.
    """

    leccion: str
    como_se_resolvio: str = ""
    prompt: str = ""
    instruccion: str = ""
    conexiones: str = ""
    proyecto: str | None = None
    tags: list[str] = field(default_factory=list)


@dataclass
class Decision:
    """Decisión de diseño o de negocio registrada en la BD personal.

    Attributes:
        decision: Qué se decidió.
        contexto: Por qué y bajo qué circunstancias.
        proyecto: Nombre del proyecto de origen (opcional).
        timestamp: Marca temporal ISO de la decisión.
    """

    decision: str
    contexto: str = ""
    proyecto: str | None = None
    timestamp: str = ""


@dataclass
class ResultadoBusqueda:
    """Resultado individual de una búsqueda FTS5.

    Attributes:
        tabla: Tabla donde se encontró (eventos, lecciones, decisiones).
        texto: Fragmento de texto que coincidió.
        proyecto: Proyecto asociado (o None para personal).
        puntaje: Relevancia BM25 otorgada por FTS5.
    """

    tabla: str
    texto: str
    proyecto: str | None
    puntaje: float


# ---------------------------------------------------------------------------
# Clase principal
# ---------------------------------------------------------------------------


class PersonalDB:
    """Base de datos personal consolidada de ContextMap.

    Gestiona el ciclo de vida del archivo SQLite: creación del esquema,
    registro de proyectos, carga idempotente de eventos, alta de lecciones
    y decisiones, y búsqueda full-text (FTS5).

    Attributes:
        ruta: Ruta absoluta del archivo de base de datos.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """Inicializa la conexión y garantiza el esquema.

        Args:
            db_path: Ruta explícita a la BD (None = resolver por jerarquía).
        """
        self.ruta = resolver_ruta_bd(db_path)
        os.makedirs(os.path.dirname(self.ruta), exist_ok=True)
        self._conn = sqlite3.connect(self.ruta)
        self._conn.row_factory = sqlite3.Row
        self._crear_esquema()

    # -- Esquema ------------------------------------------------------------

    def _crear_esquema(self) -> None:
        """Crea las tablas y el índice FTS5 si no existen."""
        self._conn.executescript(
            """
            PRAGMA journal_mode=DELETE;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS proyectos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                ruta TEXT DEFAULT '',
                ultimo_sync TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
                tipo TEXT NOT NULL,
                texto TEXT NOT NULL,
                timestamp TEXT DEFAULT '',
                fuente TEXT DEFAULT '',
                hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS lecciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
                leccion TEXT NOT NULL,
                como_se_resolvio TEXT DEFAULT '',
                prompt TEXT DEFAULT '',
                instruccion TEXT DEFAULT '',
                conexiones TEXT DEFAULT '',
                tags TEXT DEFAULT '[]',
                hash TEXT NOT NULL UNIQUE
            );

            CREATE TABLE IF NOT EXISTS decisiones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proyecto_id INTEGER REFERENCES proyectos(id) ON DELETE CASCADE,
                decision TEXT NOT NULL,
                contexto TEXT DEFAULT '',
                timestamp TEXT DEFAULT '',
                hash TEXT NOT NULL UNIQUE
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS eventos_fts USING fts5(
                texto,
                tipo,
                content='eventos',
                content_rowid='id'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS lecciones_fts USING fts5(
                leccion,
                como_se_resolvio,
                instruccion,
                content='lecciones',
                content_rowid='id'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS decisiones_fts USING fts5(
                decision,
                contexto,
                content='decisiones',
                content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS eventos_ai AFTER INSERT ON eventos BEGIN
                INSERT INTO eventos_fts(rowid, texto, tipo)
                VALUES (new.id, new.texto, new.tipo);
            END;
            CREATE TRIGGER IF NOT EXISTS eventos_ad AFTER DELETE ON eventos BEGIN
                INSERT INTO eventos_fts(eventos_fts, rowid, texto, tipo)
                VALUES ('delete', old.id, old.texto, old.tipo);
            END;

            CREATE TRIGGER IF NOT EXISTS lecciones_ai AFTER INSERT ON lecciones BEGIN
                INSERT INTO lecciones_fts(rowid, leccion, como_se_resolvio, instruccion)
                VALUES (new.id, new.leccion, new.como_se_resolvio, new.instruccion);
            END;
            CREATE TRIGGER IF NOT EXISTS lecciones_ad AFTER DELETE ON lecciones BEGIN
                INSERT INTO lecciones_fts(lecciones_fts, rowid, leccion, como_se_resolvio, instruccion)
                VALUES ('delete', old.id, old.leccion, old.como_se_resolvio, old.instruccion);
            END;

            CREATE TRIGGER IF NOT EXISTS decisiones_ai AFTER INSERT ON decisiones BEGIN
                INSERT INTO decisiones_fts(rowid, decision, contexto)
                VALUES (new.id, new.decision, new.contexto);
            END;
            CREATE TRIGGER IF NOT EXISTS decisiones_ad AFTER DELETE ON decisiones BEGIN
                INSERT INTO decisiones_fts(decisiones_fts, rowid, decision, contexto)
                VALUES ('delete', old.id, old.decision, old.contexto);
            END;
            """
        )
        self._conn.commit()

    # -- Utilidades internas ------------------------------------------------

    @staticmethod
    def _hash(*partes: Any) -> str:
        """Calcula el hash SHA-256 estable de las partes dadas.

        Args:
            *partes: Valores que identifican unívocamente el registro.

        Returns:
            str: Hash hexadecimal de 64 caracteres.
        """
        crudo = "|".join(str(p) for p in partes)
        return hashlib.sha256(crudo.encode("utf-8")).hexdigest()

    def _id_proyecto(self, nombre: str) -> int | None:
        """Devuelve el ID de un proyecto registrado (o None).

        Args:
            nombre: Nombre del proyecto.

        Returns:
            int | None: ID numérico del proyecto o None si no existe.
        """
        fila = self._conn.execute(
            "SELECT id FROM proyectos WHERE nombre = ?", (nombre,)
        ).fetchone()
        return int(fila["id"]) if fila else None

    def cerrar(self) -> None:
        """Cierra la conexión con la base de datos."""
        self._conn.close()

    def __enter__(self) -> PersonalDB:
        """Soporte de contexto para uso con ``with``."""
        return self

    def __exit__(self, *exc: Any) -> None:
        """Cierra la conexión al salir del bloque ``with``."""
        self.cerrar()

    # -- Registro de proyectos ----------------------------------------------

    def registrar_proyecto(self, nombre: str, ruta: str = "") -> int:
        """Registra un proyecto en la BD personal (upsert).

        Args:
            nombre: Nombre único del proyecto.
            ruta: Ruta del proyecto en disco.

        Returns:
            int: ID del proyecto (nuevo o existente).
        """
        pid = self._id_proyecto(nombre)
        if pid is not None:
            self._conn.execute(
                "UPDATE proyectos SET ruta = ?, ultimo_sync = datetime('now') WHERE id = ?",
                (ruta, pid),
            )
            self._conn.commit()
            return pid

        cur = self._conn.execute(
            "INSERT INTO proyectos (nombre, ruta, ultimo_sync) VALUES (?, ?, datetime('now'))",
            (nombre, ruta),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def listar_proyectos(self) -> list[str]:
        """Lista los nombres de proyectos registrados.

        Returns:
            list[str]: Nombres de proyectos ordenados alfabéticamente.
        """
        filas = self._conn.execute(
            "SELECT nombre FROM proyectos ORDER BY nombre"
        ).fetchall()
        return [str(f["nombre"]) for f in filas]

    # -- Carga de eventos ---------------------------------------------------

    def cargar_eventos(
        self,
        proyecto: str,
        eventos: list[dict[str, Any]],
    ) -> int:
        """Inserta eventos de un proyecto de forma idempotente.

        Args:
            proyecto: Nombre del proyecto al que pertenecen los eventos.
            eventos: Lista de diccionarios con ``type``, ``text``,
                ``timestamp``, ``source`` y opcionalmente ``tags``.

        Returns:
            int: Cantidad de eventos nuevos insertados.
        """
        pid = self.registrar_proyecto(proyecto)
        nuevos = 0
        for ev in eventos:
            tipo = str(ev.get("type") or "EVENTO")
            texto = str(ev.get("text") or "")
            ts = str(ev.get("timestamp") or "")
            fuente = str(ev.get("source") or "")
            if not texto:
                continue
            hash_id = self._hash(proyecto, tipo, texto, ts, fuente)
            try:
                self._conn.execute(
                    "INSERT INTO eventos (proyecto_id, tipo, texto, timestamp, fuente, hash) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (pid, tipo, texto, ts, fuente, hash_id),
                )
                nuevos += 1
            except sqlite3.IntegrityError:
                continue  # Ya existe: idempotencia
        self._conn.commit()
        return nuevos

    # -- Lecciones y decisiones ---------------------------------------------

    def agregar_leccion(self, leccion: Leccion) -> bool:
        """Guarda una lección en la BD (idempotente).

        Args:
            leccion: Lección estructurada a guardar.

        Returns:
            bool: True si se insertó, False si ya existía.
        """
        pid = self._id_proyecto(leccion.proyecto) if leccion.proyecto else None
        hash_id = self._hash(
            "leccion", leccion.proyecto or "", leccion.leccion,
            leccion.como_se_resolvio, leccion.prompt,
        )
        try:
            self._conn.execute(
                "INSERT INTO lecciones "
                "(proyecto_id, leccion, como_se_resolvio, prompt, instruccion, conexiones, tags, hash) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    pid,
                    leccion.leccion,
                    leccion.como_se_resolvio,
                    leccion.prompt,
                    leccion.instruccion,
                    leccion.conexiones,
                    json.dumps(leccion.tags, ensure_ascii=False),
                    hash_id,
                ),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def agregar_decision(self, decision: Decision) -> bool:
        """Guarda una decisión en la BD (idempotente).

        Args:
            decision: Decisión estructurada a guardar.

        Returns:
            bool: True si se insertó, False si ya existía.
        """
        pid = self._id_proyecto(decision.proyecto) if decision.proyecto else None
        hash_id = self._hash(
            "decision", decision.proyecto or "", decision.decision, decision.contexto,
        )
        try:
            self._conn.execute(
                "INSERT INTO decisiones (proyecto_id, decision, contexto, timestamp, hash) "
                "VALUES (?, ?, ?, ?, ?)",
                (pid, decision.decision, decision.contexto, decision.timestamp, hash_id),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    # -- Búsqueda full-text -------------------------------------------------

    def buscar(
        self,
        consulta: str,
        proyecto: str | None = None,
        limite: int = 10,
    ) -> list[ResultadoBusqueda]:
        """Busca en eventos, lecciones y decisiones con FTS5.

        Args:
            consulta: Términos de búsqueda (sintaxis FTS5: AND/OR/"").
            proyecto: Filtra por proyecto si se indica.
            limite: Máximo de resultados por tabla.

        Returns:
            list[ResultadoBusqueda]: Resultados ordenados por relevancia.
        """
        resultados: list[ResultadoBusqueda] = []
        pid = self._id_proyecto(proyecto) if proyecto else None

        consultas: list[tuple[str, str, str, str]] = [
            # (tabla, tabla_fts, columna_texto, columna_proyecto)
            ("eventos", "eventos_fts", "texto", "proyecto_id"),
            ("lecciones", "lecciones_fts", "leccion", "proyecto_id"),
            ("decisiones", "decisiones_fts", "decision", "proyecto_id"),
        ]

        for tabla, fts, col_texto, col_proy in consultas:
            try:
                sql = (
                    f"SELECT e.id, e.{col_texto} AS texto, e.{col_proy} AS proyecto_id, "
                    f"bm25({fts}) AS puntaje "
                    f"FROM {fts} JOIN {tabla} e ON e.id = {fts}.rowid "
                    f"WHERE {fts} MATCH ?"
                )
                params: list[Any] = [consulta]
                if pid is not None:
                    sql += f" AND e.{col_proy} = ?"
                    params.append(pid)
                sql += " ORDER BY puntaje LIMIT ?"
                params.append(limite)

                for fila in self._conn.execute(sql, params).fetchall():
                    nombre_proy = None
                    proy_id = fila["proyecto_id"]
                    if proy_id is not None:
                        proy = self._conn.execute(
                            "SELECT nombre FROM proyectos WHERE id = ?",
                            (proy_id,),
                        ).fetchone()
                        nombre_proy = str(proy["nombre"]) if proy else None
                    puntaje_raw = fila["puntaje"]
                    resultados.append(
                        ResultadoBusqueda(
                            tabla=tabla,
                            texto=str(fila["texto"])[:300],
                            proyecto=nombre_proy,
                            puntaje=float(puntaje_raw) if puntaje_raw is not None else 0.0,
                        )
                    )
            except sqlite3.OperationalError:
                logger.debug("Consulta FTS sin resultados válidos: %s", consulta)

        resultados.sort(key=lambda r: r.puntaje)
        return resultados

    # -- Estadísticas -------------------------------------------------------

    def estadisticas(self) -> dict[str, int]:
        """Devuelve conteos de la BD para el resumen de sync.

        Returns:
            dict[str, int]: Conteos por tabla.
        """
        conteos: dict[str, int] = {}
        for tabla in ("proyectos", "eventos", "lecciones", "decisiones"):
            fila = self._conn.execute(f"SELECT COUNT(*) AS n FROM {tabla}").fetchone()
            conteos[tabla] = int(fila["n"])
        return conteos

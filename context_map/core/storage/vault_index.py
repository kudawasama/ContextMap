"""Índice FTS5 derivado del vault Obsidian (búsqueda rápida).

El índice es un artefacto **derivado y reproducible**: la fuente de verdad
siguen siendo los archivos ``.md`` del vault. La base de datos se regenera en
cada ``build``/``refresh`` y no se versiona (ver ``.gitignore``).

Se reutiliza el patrón de ``core.personal.bd`` (SQLite + FTS5) para mantener
consistencia con la memoria personal multi-proyecto.
"""

from __future__ import annotations

import os
import re
import sqlite3
from typing import Iterable

__all__ = ["abrir_indice", "indexar_vault", "buscar", "ESQUEMA"]

ESQUEMA: str = """
PRAGMA journal_mode=DELETE;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS notas (
    ruta TEXT PRIMARY KEY,
    titulo TEXT NOT NULL DEFAULT '',
    seccion TEXT DEFAULT '',
    tipo TEXT DEFAULT '',
    estado TEXT DEFAULT '',
    contenido TEXT NOT NULL DEFAULT ''
);

CREATE VIRTUAL TABLE IF NOT EXISTS notas_fts USING fts5(
    titulo,
    contenido,
    content='notas',
    content_rowid='rowid'
);

CREATE TRIGGER IF NOT EXISTS notas_ai AFTER INSERT ON notas BEGIN
    INSERT INTO notas_fts(rowid, titulo, contenido)
    VALUES (new.rowid, new.titulo, new.contenido);
END;

CREATE TRIGGER IF NOT EXISTS notas_ad AFTER DELETE ON notas BEGIN
    INSERT INTO notas_fts(notas_fts, rowid, titulo, contenido)
    VALUES ('delete', old.rowid, old.titulo, old.contenido);
END;

CREATE TRIGGER IF NOT EXISTS notas_au AFTER UPDATE ON notas BEGIN
    INSERT INTO notas_fts(notas_fts, rowid, titulo, contenido)
    VALUES ('delete', old.rowid, old.titulo, old.contenido);
    INSERT INTO notas_fts(rowid, titulo, contenido)
    VALUES (new.rowid, new.titulo, new.contenido);
END;
"""


def _parsear_frontmatter(texto: str) -> tuple[dict[str, str], str]:
    """Extrae metadatos simples del bloque ``--- ... ---`` y el cuerpo.

    Parser tolerante (sin dependencia de ``yaml``): solo pares ``clave: valor``
    en una sola línea. Si no hay bloque, todo es cuerpo.

    Args:
        texto (str): Contenido completo del archivo Markdown.

    Returns:
        tuple[dict[str, str], str]: (metadatos normalizados a minúsculas, cuerpo).
    """
    meta: dict[str, str] = {}
    if not texto.startswith("---"):
        return meta, texto
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return meta, texto
    for linea in partes[1].splitlines():
        if ":" in linea:
            clave, valor = linea.split(":", 1)
            clave = clave.strip().lower()
            valor = valor.strip().strip('"').strip("'")
            if clave:
                meta[clave] = valor
    return meta, partes[2].lstrip("\n")


def _listar_markdown(vault_dir: str) -> Iterable[str]:
    """Rutas absolutas de todos los ``.md`` bajo ``vault_dir`` (recursivo)."""
    for raiz, _dirs, archivos in os.walk(vault_dir):
        for nombre in archivos:
            if nombre.lower().endswith(".md"):
                yield os.path.join(raiz, nombre)


def abrir_indice(ruta_db: str) -> sqlite3.Connection:
    """Abre (o crea) la base de datos del índice y asegura el esquema.

    Args:
        ruta_db (str): Ruta al archivo ``.db`` (se crean los directorios padres).

    Returns:
        sqlite3.Connection: Conexión con ``row_factory = sqlite3.Row``.
    """
    os.makedirs(os.path.dirname(os.path.abspath(ruta_db)), exist_ok=True)
    conn = sqlite3.connect(ruta_db)
    conn.row_factory = sqlite3.Row
    conn.executescript(ESQUEMA)
    conn.commit()
    return conn


def indexar_vault(conn: sqlite3.Connection, vault_dir: str) -> int:
    """Reconstruye el índice a partir del vault (borra e reinserta).

    Args:
        conn (sqlite3.Connection): Conexión abierta con ``abrir_indice``.
        vault_dir (str): Directorio raíz del vault Obsidian.

    Returns:
        int: Número de notas indexadas.
    """
    conn.execute("DELETE FROM notas")
    if not os.path.isdir(vault_dir):
        conn.commit()
        return 0

    filas: list[tuple[str, str, str, str, str, str]] = []
    for ruta_abs in _listar_markdown(vault_dir):
        try:
            with open(ruta_abs, encoding="utf-8") as f:
                texto = f.read()
        except OSError:
            continue
        meta, cuerpo = _parsear_frontmatter(texto)
        relativa = os.path.relpath(ruta_abs, vault_dir).replace(os.sep, "/")
        titulo = meta.get("title") or meta.get("titulo") or os.path.splitext(
            os.path.basename(ruta_abs)
        )[0]
        seccion = meta.get("section") or meta.get("seccion") or meta.get(
            "categoria", ""
        )
        tipo = meta.get("type") or meta.get("tipo") or ""
        estado = meta.get("status") or meta.get("estado") or ""
        filas.append((relativa, titulo, seccion, tipo, estado, cuerpo.strip()))

    conn.executemany(
        "INSERT INTO notas (ruta, titulo, seccion, tipo, estado, contenido) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        filas,
    )
    conn.commit()
    return len(filas)


def buscar(
    conn: sqlite3.Connection,
    consulta: str,
    seccion: str | None = None,
    tipo: str | None = None,
    limite: int = 20,
) -> list[sqlite3.Row]:
    """Búsqueda full-text sobre el índice del vault.

    Args:
        conn (sqlite3.Connection): Conexión abierta.
        consulta (str): Términos FTS5 (AND/OR/``"frase"``).
        seccion (str | None): Filtra por sección (exacto, case-insensitive).
        tipo (str | None): Filtra por tipo (exacto, case-insensitive).
        limite (int): Máximo de resultados.

    Returns:
        list[sqlite3.Row]: Filas con ``ruta, titulo, seccion, tipo, estado,
        snippet`` ordenadas por relevancia (BM25).
    """
    if not consulta.strip():
        return []
    sql = (
        "SELECT n.ruta, n.titulo, n.seccion, n.tipo, n.estado, "
        "snippet(notas_fts, 1, '[', ']', ' … ', 12) AS snippet "
        "FROM notas_fts f JOIN notas n ON n.rowid = f.rowid "
        "WHERE notas_fts MATCH ?"
    )
    params: list[object] = [consulta]
    if seccion:
        sql += " AND lower(n.seccion) = lower(?)"
        params.append(seccion)
    if tipo:
        sql += " AND lower(n.tipo) = lower(?)"
        params.append(tipo)
    sql += " ORDER BY bm25(notas_fts) LIMIT ?"
    params.append(limite)
    try:
        return list(conn.execute(sql, params).fetchall())
    except sqlite3.OperationalError:
        return []

"""Tests del índice FTS5 derivado del vault Obsidian."""

from __future__ import annotations

import os
import sqlite3
import tempfile

from context_map.core.storage.vault_index import (
    abrir_indice,
    buscar,
    indexar_vault,
)


def _crear_vault(tmp: str) -> str:
    vault = os.path.join(tmp, "vault")
    os.makedirs(vault, exist_ok=True)
    notas = {
        "1.0-Proposito/prop.md": (
            "---\ntitle: Propósito\ntipo: BASE\nseccion: 1.0\nestado: activo\n---\n"
            "ContextMap es la memoria viva del proyecto.\n"
        ),
        "2.0-Ideas/idea.md": (
            "---\ntitle: Idea cache\ntipo: IDEA\nseccion: 2.0\n---\n"
            "Mejorar la cache del brief para reducir tokens.\n"
        ),
        "4.0-Riesgos/riesgo.md": (
            "---\ntitle: Riesgo de disco\ntipo: RIESGO\nseccion: 4.0\n---\n"
            "El historial creció a 148 GB y llenó el disco.\n"
        ),
        "sin-frontmatter.md": "Texto suelto sin metadatos del vault.\n",
    }
    for rel, contenido in notas.items():
        ruta = os.path.join(vault, rel)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
    return vault


def test_abrir_indice_crea_esquema() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "state", "vault_index.db")
        conn = abrir_indice(db)
        try:
            tablas = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')"
            ).fetchall()}
            assert "notas" in tablas
            assert "notas_fts" in tablas
        finally:
            conn.close()


def test_indexar_vault_cuenta_y_parsea() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = _crear_vault(tmp)
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            n = indexar_vault(conn, vault)
            assert n == 4
            filas = conn.execute("SELECT ruta, titulo, tipo, seccion FROM notas").fetchall()
            rutas = {r["ruta"] for r in filas}
            assert "1.0-Proposito/prop.md" in rutas
            assert "sin-frontmatter.md" in rutas
            idea = [r for r in filas if r["ruta"] == "2.0-Ideas/idea.md"][0]
            assert idea["titulo"] == "Idea cache"
            assert idea["tipo"] == "IDEA"
            assert idea["seccion"] == "2.0"
            # sin frontmatter: título por nombre de archivo, campos vacíos
            suelta = [r for r in filas if r["ruta"] == "sin-frontmatter.md"][0]
            assert suelta["titulo"] == "sin-frontmatter"
            assert suelta["tipo"] == ""
        finally:
            conn.close()


def test_indexar_vault_vacio() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        os.makedirs(vault, exist_ok=True)
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            assert indexar_vault(conn, vault) == 0
            assert conn.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 0
        finally:
            conn.close()


def test_indexar_vault_inexistente() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            assert indexar_vault(conn, os.path.join(tmp, "no-existe")) == 0
        finally:
            conn.close()


def test_buscar_texto_libre() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = _crear_vault(tmp)
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            indexar_vault(conn, vault)
            res = buscar(conn, "disco")
            assert len(res) == 1
            assert res[0]["ruta"] == "4.0-Riesgos/riesgo.md"
            assert "disco" in res[0]["snippet"].lower() or "Disco" in res[0]["snippet"]
        finally:
            conn.close()


def test_buscar_filtros_seccion_y_tipo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = _crear_vault(tmp)
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            indexar_vault(conn, vault)
            # "memoria" solo aparece en la nota BASE de la sección 1.0
            res = buscar(conn, "memoria", seccion="1.0")
            assert len(res) == 1
            assert res[0]["tipo"] == "BASE"
            # filtrar por tipo IDEA
            res2 = buscar(conn, "cache", tipo="IDEA")
            assert len(res2) == 1
            assert res2[0]["ruta"] == "2.0-Ideas/idea.md"
            # filtro que no coincide
            assert buscar(conn, "cache", tipo="RIESGO") == []
        finally:
            conn.close()


def test_buscar_vacio_y_sin_resultados() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        os.makedirs(vault, exist_ok=True)
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            indexar_vault(conn, vault)
            assert buscar(conn, "") == []
            assert buscar(conn, "   ") == []
            assert buscar(conn, "terminoquenoexiste") == []
        finally:
            conn.close()


def test_reindexado_reemplaza_contenido() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        vault = os.path.join(tmp, "vault")
        os.makedirs(vault, exist_ok=True)
        ruta = os.path.join(vault, "nota.md")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("---\ntitle: Nota\ntipo: BASE\n---\ncontenido original\n")
        db = os.path.join(tmp, "vault_index.db")
        conn = abrir_indice(db)
        try:
            indexar_vault(conn, vault)
            assert buscar(conn, "original")
            # modificar y reindexar
            with open(ruta, "w", encoding="utf-8") as f:
                f.write("---\ntitle: Nota\ntipo: BASE\n---\ncontenido nuevo\n")
            indexar_vault(conn, vault)
            assert buscar(conn, "nuevo")
            assert not buscar(conn, "original")
            assert conn.execute("SELECT COUNT(*) FROM notas").fetchone()[0] == 1
        finally:
            conn.close()

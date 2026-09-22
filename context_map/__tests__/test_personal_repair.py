"""Tests unitarios e integrados para el módulo de saneamiento y reparación (Repair)."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from unittest.mock import patch

from context_map.application.commands.personal import cmd_personal
from context_map.core.personal import PersonalDB
from context_map.core.personal.repair import (
    _fusionar_proyectos_duplicados,
    _purgar_eventos_ruido,
    formatear_repair_texto,
    reparar_bd_personal,
)
from context_map.infrastructure import mcp_server


def _crear_bd_temporal() -> tuple[PersonalDB, str]:
    """Crea una base de datos personal temporal."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_repair_test_")
    db = PersonalDB(os.path.join(temp_dir, "personal.db"))
    return db, temp_dir


def test_purga_eventos_ruido() -> None:
    """Verifica que se purguen archivos del sistema, paths de vendor y TODOs falsos."""
    db, temp_dir = _crear_bd_temporal()
    try:
        db.cargar_eventos(
            "MiApp",
            [
                {"type": "IDEA", "text": "Idea real y legítima", "timestamp": "2026-09-01", "source": "chat:1.md"},
                {"type": "IDEA", "text": "[", "timestamp": "", "source": "chat:desktop.ini"},
                {"type": "RIESGO", "text": "Alta complejidad: .vercel/cache/fastapi.py", "timestamp": "", "source": "scan"},
                {"type": "FUTURO", "text": "TODO (app.py:L10): todos los módulos cargados", "timestamp": "", "source": "scan"},
                {"type": "FUTURO", "text": "TODO (app.py:L20): # TODO: refactorizar base", "timestamp": "", "source": "scan"},
            ],
            ruta="/proyectos/miapp",
        )

        # 1. Dry run no debe borrar nada
        purgados_dry = _purgar_eventos_ruido(db, dry_run=True)
        assert purgados_dry == 3  # desktop.ini, .vercel, TODO sin comentario

        cursor = db._conn.cursor()
        cursor.execute("SELECT count(*) FROM eventos")
        assert cursor.fetchone()[0] == 5

        # 2. Ejecución real
        purgados_real = _purgar_eventos_ruido(db, dry_run=False)
        assert purgados_real == 3

        cursor.execute("SELECT count(*) FROM eventos")
        assert cursor.fetchone()[0] == 2

        # Quedan solo los 2 legítimos
        textos = [f[0] for f in cursor.execute("SELECT texto FROM eventos").fetchall()]
        assert "Idea real y legítima" in textos
        assert "TODO (app.py:L20): # TODO: refactorizar base" in textos
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fusion_proyectos_duplicados() -> None:
    """Verifica que proyectos con el mismo nombre normalizado se fusionen."""
    db, temp_dir = _crear_bd_temporal()
    try:
        # Registrar duplicados
        db.cargar_eventos("Mitos y Leyendas", [{"type": "IDEA", "text": "E1", "timestamp": "", "source": "s"}], ruta="/proyectos/myl")
        db.cargar_eventos("Mitos-y-Leyendas", [{"type": "IDEA", "text": "E2", "timestamp": "", "source": "s"}], ruta="")

        assert len(db.listar_proyectos()) == 2

        fusiones = _fusionar_proyectos_duplicados(db, dry_run=False)
        assert len(fusiones) == 1
        assert "Mitos-y-Leyendas" in fusiones[0]

        # Solo debe quedar un proyecto
        proyectos = db.listar_proyectos()
        assert len(proyectos) == 1
        assert proyectos[0] == "Mitos y Leyendas"

        # Los eventos se reasignaron al canónico
        cursor = db._conn.cursor()
        cursor.execute("SELECT count(*) FROM eventos")
        assert cursor.fetchone()[0] == 2
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_reparacion_integral_e_idempotencia() -> None:
    """Verifica que correr repair integral sea 100% idempotente."""
    db, temp_dir = _crear_bd_temporal()
    try:
        # Estado inicial sucio
        db.registrar_proyecto("ProyectoVacio", "/ruta/vacio")
        db.cargar_eventos("Duplicado 1", [{"type": "IDEA", "text": "E1", "timestamp": "", "source": "s"}], ruta="/ruta/d")
        db.cargar_eventos("Duplicado-1", [{"type": "IDEA", "text": "E2", "timestamp": "", "source": "s"}], ruta="")
        db.cargar_eventos("Basura", [{"type": "IDEA", "text": "[", "timestamp": "", "source": "chat:desktop.ini"}], ruta="")

        # Corrida 1: Realiza reparaciones
        rep1 = reparar_bd_personal(
            db=db,
            dry_run=False,
            merge_duplicados=True,
            fill_ruta=False,
            drop_vacios=True,
            purge_ruido=True,
            vacuum=True,
        )

        assert len(rep1.duplicados_fusionados) == 1
        assert len(rep1.proyectos_vacios_eliminados) >= 1  # ProyectoVacio (y Basura si quedó vacío tras purgar)
        assert rep1.eventos_ruido_purgados >= 1
        assert rep1.fts_reconstruido is True
        assert rep1.vacuum_ejecutado is True

        txt1 = formatear_repair_texto(rep1)
        assert "REPARACIÓN Y SANEAMIENTO" in txt1

        # Corrida 2: Idempotente (0 cambios pendientes)
        rep2 = reparar_bd_personal(
            db=db,
            dry_run=False,
            merge_duplicados=True,
            fill_ruta=False,
            drop_vacios=True,
            purge_ruido=True,
            vacuum=True,
        )

        assert len(rep2.duplicados_fusionados) == 0
        assert len(rep2.proyectos_vacios_eliminados) == 0
        assert rep2.eventos_ruido_purgados == 0
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cli_personal_repair(capsys) -> None:
    """Verifica la invocación de repair desde la CLI."""
    db, temp_dir = _crear_bd_temporal()
    db_path = db.ruta
    db.cerrar()

    class Args:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    try:
        # CLI repair dry-run
        args = Args(
            personal_cmd="repair",
            dry_run=True,
            all=True,
            merge_duplicados=False,
            fill_ruta=False,
            drop_vacios=False,
            purge_ruido=False,
            vacuum=False,
            rutas="",
            json=False,
            db=db_path,
        )
        cmd_personal(args)
        captured = capsys.readouterr()
        assert "SIMULACIÓN" in captured.out

        # CLI repair json
        args_json = Args(
            personal_cmd="repair",
            dry_run=True,
            all=True,
            merge_duplicados=False,
            fill_ruta=False,
            drop_vacios=False,
            purge_ruido=False,
            vacuum=False,
            rutas="",
            json=True,
            db=db_path,
        )
        cmd_personal(args_json)
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert "eventos_ruido_purgados" in data
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mcp_tool_personal_repair() -> None:
    """Verifica la tool MCP personal_repair con y sin confirmación."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_mcp_repair_")
    db_file = os.path.join(temp_dir, "personal.db")
    db_init = PersonalDB(db_file)
    db_init.cerrar()

    try:
        with patch("context_map.core.personal.PersonalDB", side_effect=lambda: PersonalDB(db_file)):
            # Sin confirmación para repair real falla por seguridad
            res_err = mcp_server.personal_repair(dry_run=False, confirm=False)
            assert "ERROR" in res_err

            # Dry-run funciona sin confirmación
            res_dry = mcp_server.personal_repair(dry_run=True)
            assert "SIMULACIÓN" in res_dry

            # Confirmación aplicada
            res_ok = mcp_server.personal_repair(dry_run=False, confirm=True)
            assert "REPARACIÓN Y SANEAMIENTO" in res_ok
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

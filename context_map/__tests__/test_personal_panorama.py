"""Tests unitarios e integrados para el módulo de Panorama y Timeline Personal."""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

from context_map.application.commands.personal import (
    cmd_personal,
)
from context_map.core.personal import PersonalDB
from context_map.core.personal.panorama import (
    _calcular_dias_inactivo,
    _determinar_semaforo,
    construir_panorama,
    construir_timeline,
    formatear_panorama_texto,
    formatear_timeline_texto,
)
from context_map.infrastructure import mcp_server


def _crear_bd_temporal() -> tuple[PersonalDB, str]:
    """Crea una base de datos personal temporal para pruebas."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_panorama_test_")
    db = PersonalDB(os.path.join(temp_dir, "personal.db"))
    return db, temp_dir


def _crear_hermes_db_temporal(temp_dir: str) -> str:
    """Crea una base de datos SQLite sintética de sesiones de Hermes."""
    db_path = os.path.join(temp_dir, "hermes_state.db")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            started_at TEXT,
            cwd TEXT,
            git_repo_root TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TEXT
        )
        """
    )

    hace_2_dias = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")
    hace_10_dias = (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds")

    cur.execute(
        "INSERT INTO sessions VALUES ('s1', 'Refactorizar Auth', ?, '/proyectos/app1', '/proyectos/app1')",
        (hace_2_dias,),
    )
    cur.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES ('s1', 'user', 'Hola', ?)",
        (hace_2_dias,),
    )
    cur.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES ('s1', 'assistant', 'Listo el auth', ?)",
        (hace_2_dias,),
    )

    cur.execute(
        "INSERT INTO sessions VALUES ('s2', 'Revisión mensual', ?, '/proyectos/app2', '/proyectos/app2')",
        (hace_10_dias,),
    )
    cur.execute(
        "INSERT INTO messages (session_id, role, content, timestamp) VALUES ('s2', 'user', 'Revisar logs', ?)",
        (hace_10_dias,),
    )

    conn.commit()
    conn.close()
    return db_path


def test_calculo_dias_inactivo_y_semaforo() -> None:
    """Valida la función matemática de inactividad y asignación de semáforos."""
    ahora = datetime(2026, 9, 22, 12, 0, 0)

    # Días inactivos
    assert _calcular_dias_inactivo("2026-09-20T10:00:00", ahora) == 2
    assert _calcular_dias_inactivo("2026-09-01", ahora) == 21
    assert _calcular_dias_inactivo("", ahora) is None
    assert _calcular_dias_inactivo("invalido", ahora) is None

    # Semáforo
    assert _determinar_semaforo(0, 0, None) == "vacio"
    assert _determinar_semaforo(10, 0, 3) == "activo"
    assert _determinar_semaforo(10, 0, 7) == "activo"
    assert _determinar_semaforo(10, 0, 8) == "tibio"
    assert _determinar_semaforo(10, 0, 21) == "tibio"
    assert _determinar_semaforo(10, 0, 22) == "dormido"
    assert _determinar_semaforo(10, 0, None) == "dormido"


def test_construir_panorama_con_proyectos_y_sesiones() -> None:
    """Verifica que el panorama consolide proyectos, métricas, riesgos y sesiones reales."""
    db, temp_dir = _crear_bd_temporal()
    hermes_path = _crear_hermes_db_temporal(temp_dir)
    ahora = datetime.now()

    try:
        # 1. Proyecto Activo con Riesgos y Pendientes
        hace_1_dia = (ahora - timedelta(days=1)).isoformat(timespec="seconds")
        db.cargar_eventos(
            "App1",
            [
                {"type": "BASE", "text": "Modulo core", "timestamp": hace_1_dia, "source": "s1"},
                {"type": "RIESGO", "text": "Riesgo de seguridad en auth", "timestamp": hace_1_dia, "source": "s1"},
                {"type": "FUTURO", "text": "TODO: agregar rate limiting", "timestamp": hace_1_dia, "source": "s1"},
            ],
            ruta="/proyectos/app1",
        )

        # 2. Proyecto Dormido
        hace_30_dias = (ahora - timedelta(days=30)).isoformat(timespec="seconds")
        db.cargar_eventos(
            "App2",
            [
                {"type": "BASE", "text": "Modulo antiguo", "timestamp": hace_30_dias, "source": "s2"},
            ],
            ruta="/proyectos/app2",
        )

        # 3. Proyecto Vacío
        db.registrar_proyecto("AppVacia", "/proyectos/vacio")

        # Generar panorama
        rep = construir_panorama(
            db=db,
            dias=14,
            hermes_db_path=hermes_path,
            referencia_tiempo=ahora,
        )

        assert rep.resumen_semaforo["activo"] >= 1
        assert rep.resumen_semaforo["vacio"] >= 1
        assert len(rep.proyectos) == 3

        # Proyecto activo
        p_app1 = next(p for p in rep.proyectos if p.nombre == "App1")
        assert p_app1.semaforo == "activo"
        assert len(p_app1.riesgos_vigentes) == 1
        assert len(p_app1.pendientes_vigentes) == 1
        assert p_app1.sesiones_recientes >= 1

        # Sesiones reales identificadas
        assert len(rep.sesiones) >= 1
        assert any(s.proyecto == "App1" for s in rep.sesiones)

        # Foco sugerido incluye App1 por tener riesgos/pendientes
        assert any("App1" in f for f in rep.foco_sugerido)

        # Validar formato de texto
        txt = formatear_panorama_texto(rep)
        assert "PANORAMA MULTI-PROYECTO" in txt
        assert "App1" in txt
        assert "🟢 Activo" in txt
        assert "Refactorizar Auth" in txt

        # Validar to_dict
        d = rep.to_dict()
        assert d["dias_analizados"] == 14
        assert len(d["proyectos"]) == 3
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_construir_timeline() -> None:
    """Verifica que el timeline unifique cronológicamente eventos y sesiones."""
    db, temp_dir = _crear_bd_temporal()
    hermes_path = _crear_hermes_db_temporal(temp_dir)
    ahora = datetime.now()

    try:
        hace_1_dia = (ahora - timedelta(days=1)).isoformat(timespec="seconds")
        db.cargar_eventos(
            "App1",
            [
                {"type": "CAMBIO", "text": "Actualización de dependencias", "timestamp": hace_1_dia, "source": "git"},
            ],
            ruta="/proyectos/app1",
        )

        items = construir_timeline(
            db=db,
            dias=30,
            hermes_db_path=hermes_path,
            referencia_tiempo=ahora,
        )

        assert len(items) >= 2  # 1 evento + 2 sesiones hermes
        tipos = {it.tipo for it in items}
        assert "CAMBIO" in tipos
        assert "SESION" in tipos

        txt = formatear_timeline_texto(items)
        assert "LÍNEA TEMPORAL DE ACTIVIDAD" in txt
        assert "Actualización de dependencias" in txt
        assert "Refactorizar Auth" in txt
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cli_subcomandos_panorama_y_timeline(capsys) -> None:
    """Verifica la invocación de comandos CLI y salida JSON."""
    db, temp_dir = _crear_bd_temporal()
    db_path = db.ruta
    db.cerrar()

    class Args:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    try:
        # CLI panorama normal
        args_pano = Args(
            personal_cmd="panorama",
            dias=14,
            proyecto=None,
            solo_sesiones=False,
            json=False,
            db=db_path,
        )
        with patch("context_map.core.personal.panorama.leer_sesiones", return_value=[]):
            cmd_personal(args_pano)
            captured = capsys.readouterr()
            assert "PANORAMA MULTI-PROYECTO" in captured.out

        # CLI panorama json
        args_pano_json = Args(
            personal_cmd="panorama",
            dias=7,
            proyecto=None,
            solo_sesiones=False,
            json=True,
            db=db_path,
        )
        with patch("context_map.core.personal.panorama.leer_sesiones", return_value=[]):
            cmd_personal(args_pano_json)
            captured = capsys.readouterr()
            data = json.loads(captured.out)
            assert "resumen_semaforo" in data

        # CLI timeline normal
        args_time = Args(
            personal_cmd="timeline",
            dias=30,
            proyecto=None,
            json=False,
            db=db_path,
        )
        with patch("context_map.core.personal.panorama.leer_sesiones", return_value=[]):
            cmd_personal(args_time)
            captured = capsys.readouterr()
            assert "LÍNEA TEMPORAL" in captured.out
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_mcp_tools_panorama_y_timeline() -> None:
    """Verifica que las tools MCP personal_panorama y personal_timeline respondan adecuadamente."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_mcp_pano_")
    db_file = os.path.join(temp_dir, "personal.db")
    # Inicializar el esquema
    db_init = PersonalDB(db_file)
    db_init.cerrar()

    try:
        with (
            patch("context_map.core.personal.PersonalDB", side_effect=lambda: PersonalDB(db_file)),
            patch("context_map.core.personal.panorama.leer_sesiones", return_value=[]),
        ):
            res_pano = mcp_server.personal_panorama(dias=14)
            assert "PANORAMA MULTI-PROYECTO" in res_pano
            res_json = mcp_server.personal_panorama(dias=14, json_output=True)
            assert '"resumen_semaforo"' in res_json

            res_time = mcp_server.personal_timeline(dias=30)
            assert "LÍNEA TEMPORAL" in res_time
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

"""Tests del módulo personal: base de datos consolidada y transportable."""

from __future__ import annotations

import os
import shutil
import tempfile

from context_map.application.commands.personal import sincronizar_proyecto_automatico
from context_map.core.personal import (
    FALLBACK_DIR,
    Decision,
    Leccion,
    PersonalDB,
    resolver_ruta_bd,
)


def _db_temporal(prefix: str = "ctxmap_personal_test_") -> tuple[PersonalDB, str]:
    """Crea una BD personal en un directorio temporal.

    Args:
        prefix: Prefijo del directorio temporal.

    Returns:
        tuple[PersonalDB, str]: (instancia de BD, ruta del directorio temp).
    """
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    db = PersonalDB(os.path.join(temp_dir, "personal.db"))
    return db, temp_dir


def test_crea_esquema_y_tablas() -> None:
    """Verifica que el esquema SQLite se crea con todas las tablas."""
    db, temp_dir = _db_temporal()
    try:
        tablas = {
            str(fila["name"])
            for fila in db._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert {"proyectos", "eventos", "lecciones", "decisiones"} <= tablas
        # Índices FTS5 presentes
        assert "eventos_fts" in tablas
        assert "lecciones_fts" in tablas
        assert "decisiones_fts" in tablas
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_registrar_proyecto_idempotente() -> None:
    """Verifica que registrar el mismo proyecto no duplica."""
    db, temp_dir = _db_temporal()
    try:
        pid1 = db.registrar_proyecto("CotanoPet", "/ruta/a/cotanopet")
        pid2 = db.registrar_proyecto("CotanoPet", "/ruta/actualizada")
        assert pid1 == pid2
        assert db.listar_proyectos() == ["CotanoPet"]
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cargar_eventos_idempotente() -> None:
    """Verifica que re-cargar los mismos eventos no duplica."""
    db, temp_dir = _db_temporal()
    try:
        eventos = [
            {"type": "IDEA", "text": "Sincronizar vault en F:", "timestamp": "2026-08-13T10:00:00", "source": "test"},
            {"type": "RIESGO", "text": "Tokens caducados", "timestamp": "2026-08-13T10:05:00", "source": "test"},
        ]
        nuevos1 = db.cargar_eventos("ContextMap", eventos)
        nuevos2 = db.cargar_eventos("ContextMap", eventos)
        nuevos3 = db.cargar_eventos("ContextMap", [eventos[0]])  # solo 1 repetido
        assert nuevos1 == 2
        assert nuevos2 == 0  # idempotencia total
        assert nuevos3 == 0
        stats = db.estadisticas()
        assert stats["eventos"] == 2
        assert stats["proyectos"] == 1
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agregar_leccion_y_decision_idempotente() -> None:
    """Verifica que lecciones y decisiones no se duplican."""
    db, temp_dir = _db_temporal()
    try:
        db.registrar_proyecto("mi-app-utm", "")
        leccion = Leccion(
            leccion="Los tokens ghp_ caducan",
            como_se_resolvio="Renovar en GitHub",
            proyecto="mi-app-utm",
            tags=["git", "tokens"],
        )
        assert db.agregar_leccion(leccion) is True
        assert db.agregar_leccion(leccion) is False  # duplicado

        decision = Decision(
            decision="Usar SQLite para la BD personal",
            contexto="Transportable y sin dependencias",
            proyecto="mi-app-utm",
        )
        assert db.agregar_decision(decision) is True
        assert db.agregar_decision(decision) is False

        stats = db.estadisticas()
        assert stats["lecciones"] == 1
        assert stats["decisiones"] == 1
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_busqueda_fts5() -> None:
    """Verifica la búsqueda full-text sobre eventos y lecciones."""
    db, temp_dir = _db_temporal()
    try:
        db.cargar_eventos(
            "ContextMap",
            [
                {"type": "IDEA", "text": "Vault Obsidian con topología en árbol", "timestamp": "", "source": "t"},
                {"type": "BASE", "text": "Persistencia JSONL con append atómico", "timestamp": "", "source": "t"},
            ],
        )
        db.agregar_leccion(
            Leccion(leccion="BitLocker del disco F: necesita recovery key", proyecto="ContextMap")
        )

        resultados = db.buscar("obsidian")
        assert len(resultados) >= 1
        assert resultados[0].tabla == "eventos"
        assert "Obsidian" in resultados[0].texto

        resultados_bitlocker = db.buscar("bitlocker")
        assert len(resultados_bitlocker) == 1
        assert resultados_bitlocker[0].tabla == "lecciones"

        # Filtro por proyecto
        db.cargar_eventos(
            "OtroProyecto",
            [{"type": "IDEA", "text": "Obsidian como herramienta de notas", "timestamp": "", "source": "t"}],
        )
        filtrados = db.buscar("obsidian", proyecto="ContextMap")
        assert all(r.proyecto == "ContextMap" for r in filtrados)
    finally:
        db.cerrar()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_resolver_ruta_bd_prioridad_env(monkeypatch) -> None:
    """Verifica que la variable de entorno tiene prioridad sobre el default.

    Compara contra ``os.path.abspath`` para ser cross-platform: en Linux
    ``/tmp/custom.db`` se mantiene, en Windows se resuelve a ``C:\\tmp\\custom.db``.
    """
    monkeypatch.delenv("CTXMAP_PERSONAL_DB", raising=False)
    ruta = resolver_ruta_bd("/tmp/custom.db")
    assert ruta == os.path.abspath("/tmp/custom.db")

    monkeypatch.setenv("CTXMAP_PERSONAL_DB", "/mnt/pendrive/personal.db")
    ruta_env = resolver_ruta_bd()
    assert ruta_env == os.path.abspath("/mnt/pendrive/personal.db")


def test_resolver_ruta_bd_ignora_mount_no_escribible(tmp_path, monkeypatch) -> None:
    """Verifica que un dir vacío sin montaje NO se confunde con F: activo."""
    monkeypatch.delenv("CTXMAP_PERSONAL_DB", raising=False)

    # Crear un falso mount root:root sin permisos de escritura
    falso_mount = tmp_path / "fdrive_vacio"
    falso_mount.mkdir()
    os.chmod(falso_mount, 0o555)

    # La función itera mounts fijos; forzamos que ninguno sea escribible
    original_access = os.access

    def _acceso_fake(path: str, mode: int) -> bool:
        if str(path) in ("/mnt/fdrive", "/media/fdrive", "/run/media/fdrive"):
            return False
        return original_access(path, mode)

    monkeypatch.setattr(os, "access", _acceso_fake)
    ruta = resolver_ruta_bd()
    # Sin F: accesible -> cae al fallback local
    assert str(ruta).endswith(os.path.join(FALLBACK_DIR, "personal.db"))
    os.chmod(falso_mount, 0o755)


def test_sincronizar_proyecto_automatico_tolerante(tmp_path, monkeypatch) -> None:
    """Verifica que la consolidación automática no rompe sin .context-map."""
    # Sin carpeta .context-map -> debe ser silenciosa y no lanzar
    vacio = tmp_path / "sin-contexto"
    vacio.mkdir()
    sincronizar_proyecto_automatico("Vacio", str(vacio))  # no debe lanzar

    # Con .context-map con eventos -> consolida en BD temporal
    proyecto = tmp_path / "proyecto"
    raw = proyecto / ".context-map" / "raw"
    chats = proyecto / ".context-map" / "chats"
    raw.mkdir(parents=True)
    chats.mkdir(parents=True)
    (raw / "events.jsonl").write_text(
        '{"type": "IDEA", "text": "Evento de prueba", "timestamp": "2026-08-13T10:00:00", "source": "t"}\n',
        encoding="utf-8",
    )

    ruta_db = str(tmp_path / "personal.db")
    monkeypatch.setenv("CTXMAP_PERSONAL_DB", ruta_db)

    # Evitar montajes F: en CI: forzar env ya está hecho
    sincronizar_proyecto_automatico("Proyecto", str(proyecto))

    db = PersonalDB(ruta_db)
    try:
        stats = db.estadisticas()
        assert stats["proyectos"] == 1
        assert stats["eventos"] == 1
    finally:
        db.cerrar()


def test_nombre_proyecto_usa_vault(tmp_path) -> None:
    """Deriva el nombre del proyecto desde vault-<X> (no de la carpeta local)."""
    from context_map.application.commands.personal import _nombre_proyecto_por_ruta

    # Con vault-<Nombre>: usa el nombre del vault (consistente entre PCs)
    con_vault = tmp_path / "carpeta-local"
    (con_vault / ".context-map" / "vault-MiProyecto").mkdir(parents=True)
    assert _nombre_proyecto_por_ruta(str(con_vault)) == "MiProyecto"

    # Sin vault: fallback a la carpeta
    sin_vault = tmp_path / "carpeta-sola"
    sin_vault.mkdir(exist_ok=True)
    assert _nombre_proyecto_por_ruta(str(sin_vault)) == "carpeta-sola"


def test_sync_personal_rutas_adicionales(tmp_path, monkeypatch) -> None:
    """El flag --rutas permite añadir carpetas fuera de las bases por defecto."""
    from argparse import Namespace

    import context_map.application.commands.personal as personal_mod
    from context_map.application.commands.personal import _cmd_personal_sync
    from context_map.core.personal import PersonalDB

    proyecto = tmp_path / "MiProyectoGDrive"
    (proyecto / ".context-map" / "raw").mkdir(parents=True)
    (proyecto / ".context-map" / "chats").mkdir(parents=True)
    (proyecto / ".context-map" / "raw" / "events.jsonl").write_text(
        '{"type": "IDEA", "text": "Evento rutas", "timestamp": "2026-08-13T10:00:00", "source": "t"}\n',
        encoding="utf-8",
    )

    ruta_db = str(tmp_path / "personal-rutas.db")
    # Sin bases por defecto: solo la ruta extra del flag
    monkeypatch.setattr(personal_mod, "_bases_por_defecto", lambda: [])
    _cmd_personal_sync(Namespace(todos=True, target=".", rutas=str(proyecto), db=ruta_db))

    db = PersonalDB(ruta_db)
    try:
        stats = db.estadisticas()
        assert stats["proyectos"] == 1
        assert stats["eventos"] == 1
    finally:
        db.cerrar()


def test_export_sin_wikilinks_fantasma(tmp_path) -> None:
    """El vault personal no debe enlazar [[proyectos]] que no existen como notas."""
    from argparse import Namespace

    from context_map.application.commands.personal import _cmd_personal_export
    from context_map.core.personal import PersonalDB

    ruta_db = str(tmp_path / "personal-export.db")
    db = PersonalDB(ruta_db)
    try:
        db.cargar_eventos(
            "ProyectoX",
            [{"type": "IDEA", "text": "Algo", "timestamp": "", "source": "t"}],
        )
    finally:
        db.cerrar()

    destino = str(tmp_path / "vault-personal")
    _cmd_personal_export(Namespace(destino=destino, db=ruta_db))

    with open(os.path.join(destino, "00-INDICE.md"), encoding="utf-8") as f:
        contenido = f.read()
    assert "[[ProyectoX" not in contenido, "wikilink a nota inexistente (nodo fantasma)"
    assert "ProyectoX" in contenido


def test_mcp_personal_query_funcional(tmp_path, monkeypatch) -> None:
    """La tool MCP personal_query consulta la BD personal (FTS5)."""
    from context_map.infrastructure.mcp_server import personal_query

    ruta_db = str(tmp_path / "personal-mcp.db")
    monkeypatch.setenv("CTXMAP_PERSONAL_DB", ruta_db)

    from context_map.core.personal import PersonalDB

    db = PersonalDB(ruta_db)
    try:
        db.cargar_eventos(
            "MiProyecto",
            [{"type": "IDEA", "text": "Obsidian como herramienta de notas", "timestamp": "", "source": "t"}],
        )
    finally:
        db.cerrar()

    salida = personal_query("obsidian")
    assert "obsidian" in salida.lower() or "Obsidian" in salida
    assert "MiProyecto" in salida
    # Sin coincidencias: mensaje claro
    assert "sin resultados" in personal_query("zzznoexiste")


def test_agents_md_incluye_contexto_global_personal(tmp_path) -> None:
    """Las reglas agénticas enseñan a consultar la BD personal (multi-IDE)."""
    from context_map.domain.ecosystem.adaptador import _generar_agents_md
    from context_map.domain.ecosystem.detector import detectar_ecosistema

    eco = detectar_ecosistema(str(tmp_path))
    contenido = _generar_agents_md("DemoProj", eco, "2026-08-13")
    assert "Contexto GLOBAL personal" in contenido
    assert "personal query" in contenido

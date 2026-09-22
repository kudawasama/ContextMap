"""Módulo de saneamiento, auto-reparación e higiene de la BD Personal.

Proporciona operaciones idempotentes para:
- Fusionar proyectos duplicados por divergencia de nomenclatura (ej. guiones vs espacios).
- Rellenar rutas locales faltantes de proyectos registrados.
- Eliminar proyectos vacíos o artefactos residuales de tests.
- Purgar eventos de ruido histórico (falsos positivos de TODO, caches de despliegue, desktop.ini).
- Reconstruir índices full-text (FTS5) y optimizar el almacenamiento SQLite (VACUUM).
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from context_map.core.personal.bd import PersonalDB

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modelos de reporte
# ---------------------------------------------------------------------------


@dataclass
class RepairReport:
    """Reporte estructurado con el resultado del saneamiento de la BD.

    Attributes:
        dry_run: Si fue una simulación sin escrituras en disco.
        duplicados_fusionados: Nombres de proyectos fusionados en registros canónicos.
        rutas_rellenadas: Pares (nombre_proyecto, ruta_asignada).
        proyectos_vacios_eliminados: Nombres de proyectos eliminados por carecer de contenido.
        eventos_ruido_purgados: Cantidad total de eventos basura eliminados.
        fts_reconstruido: Si se reconstruyeron los índices FTS5.
        vacuum_ejecutado: Si se ejecutó VACUUM para compactar la base de datos.
    """

    dry_run: bool = False
    duplicados_fusionados: list[str] = field(default_factory=list)
    rutas_rellenadas: list[tuple[str, str]] = field(default_factory=list)
    proyectos_vacios_eliminados: list[str] = field(default_factory=list)
    eventos_ruido_purgados: int = 0
    fts_reconstruido: bool = False
    vacuum_ejecutado: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serializa el reporte a un diccionario.

        Returns:
            dict[str, Any]: Representación serializable.
        """
        return asdict(self)


# ---------------------------------------------------------------------------
# Funciones auxiliares de saneamiento
# ---------------------------------------------------------------------------


def _normalizar_identidad(nombre: str) -> str:
    """Calcula la clave canónica de identidad de un proyecto."""
    if not nombre:
        return ""
    limpio = nombre.lower().replace("-", " ").replace("_", " ")
    return " ".join(limpio.split())


def _purgar_eventos_ruido(db: PersonalDB, dry_run: bool = False) -> int:
    """Identifica y elimina eventos de ruido histórico persistidos.

    Patrones purgados:
    - Eventos con fuente 'chat:desktop.ini' o 'chat:thumbs.db'.
    - Eventos de rutas vendorizadas o caches de despliegue (.vercel, .next, archive-v0).
    - TODOs falsos provenientes de substrings en código (ej. logger.debug, todos los).

    Args:
        db: Base de datos personal conectada.
        dry_run: Si es True, solo cuenta sin borrar.

    Returns:
        int: Cantidad de eventos purgados o identificados.
    """
    cursor = db._conn.cursor()

    # 1. Archivos del sistema y binarios ingeridos
    condiciones = [
        "fuente LIKE '%desktop.ini%'",
        "fuente LIKE '%thumbs.db%'",
        "texto LIKE '%.vercel/%'",
        "texto LIKE '%.next/%'",
        "texto LIKE '%archive-v0/%'",
        "texto = '['",
        "texto = ''",
    ]

    query_conteo = f"SELECT count(*) FROM eventos WHERE {' OR '.join(condiciones)}"
    cursor.execute(query_conteo)
    total_ruido = cursor.fetchone()[0]

    # 2. TODOs falsos históricos (tipo FUTURO que no contengan TODO/FIXME/HACK en comentario)
    cursor.execute("SELECT id, texto FROM eventos WHERE tipo = 'FUTURO'")
    filas_futuro = cursor.fetchall()
    re_marcador_real = re.compile(r"(?:#|//|/\*|<!--|--)\s*(?:TODO|FIXME|HACK|XXX)\b", re.I)
    ids_falsos_todo: list[int] = []

    for fila in filas_futuro:
        txt = fila[1] or ""
        # Si el texto dice "TODO (...):" pero en el cuerpo del código no hay un marcador real
        if "TODO (" in txt:
            cuerpo = txt.split("):", 1)[-1] if "):" in txt else txt
            if not re_marcador_real.search(cuerpo):
                ids_falsos_todo.append(fila[0])

    total_purgados = total_ruido + len(ids_falsos_todo)

    if not dry_run and total_purgados > 0:
        cursor.execute(f"DELETE FROM eventos WHERE {' OR '.join(condiciones)}")
        if ids_falsos_todo:
            placeholders = ",".join(["?"] * len(ids_falsos_todo))
            cursor.execute(f"DELETE FROM eventos WHERE id IN ({placeholders})", ids_falsos_todo)
        db._conn.commit()

    return total_purgados


def _fusionar_proyectos_duplicados(db: PersonalDB, dry_run: bool = False) -> list[str]:
    """Fusiona filas de proyectos que representan la misma entidad.

    Args:
        db: Base de datos personal conectada.
        dry_run: Si es True, solo reporta los candidatos.

    Returns:
        list[str]: Lista de descripciones de fusiones realizadas.
    """
    cursor = db._conn.cursor()
    cursor.execute("SELECT id, nombre, ruta FROM proyectos ORDER BY id ASC")
    filas = cursor.fetchall()

    grupos: dict[str, list[dict[str, Any]]] = {}
    for f in filas:
        clave = _normalizar_identidad(f["nombre"])
        grupos.setdefault(clave, []).append({"id": f["id"], "nombre": f["nombre"], "ruta": f["ruta"]})

    fusiones: list[str] = []

    for _clave, lista in grupos.items():
        if len(lista) <= 1:
            continue

        # Seleccionar el canónico: preferir el que tenga nombre con espacios o con ruta
        canonico = sorted(
            lista,
            key=lambda x: (bool(x["ruta"]), " " in x["nombre"], -len(x["nombre"])),
            reverse=True,
        )[0]
        id_canonico = canonico["id"]
        nombre_canonico = canonico["nombre"]

        for item in lista:
            if item["id"] == id_canonico:
                continue

            id_duplicado = item["id"]
            nombre_duplicado = item["nombre"]
            msg = f"{nombre_duplicado} (id={id_duplicado}) → {nombre_canonico} (id={id_canonico})"
            fusiones.append(msg)

            if not dry_run:
                # Reasignar eventos ignorando duplicados por hash único
                cursor.execute(
                    "UPDATE OR IGNORE eventos SET proyecto_id = ? WHERE proyecto_id = ?",
                    (id_canonico, id_duplicado),
                )
                cursor.execute(
                    "UPDATE OR IGNORE lecciones SET proyecto_id = ? WHERE proyecto_id = ?",
                    (id_canonico, id_duplicado),
                )
                cursor.execute(
                    "UPDATE OR IGNORE decisiones SET proyecto_id = ? WHERE proyecto_id = ?",
                    (id_canonico, id_duplicado),
                )
                # Eliminar el proyecto duplicado sobrante
                cursor.execute("DELETE FROM proyectos WHERE id = ?", (id_duplicado,))

    if not dry_run and fusiones:
        db._conn.commit()

    return fusiones


def _eliminar_proyectos_vacios(db: PersonalDB, dry_run: bool = False) -> list[str]:
    """Elimina proyectos registrados que no contienen eventos ni lecciones.

    Args:
        db: Base de datos personal conectada.
        dry_run: Si es True, solo reporta.

    Returns:
        list[str]: Nombres de proyectos vacíos eliminados.
    """
    cursor = db._conn.cursor()
    cursor.execute("SELECT id, nombre FROM proyectos")
    filas = cursor.fetchall()

    eliminados: list[str] = []
    for f in filas:
        p_id, p_nombre = f[0], f[1]
        cursor.execute("SELECT count(*) FROM eventos WHERE proyecto_id = ?", (p_id,))
        n_ev = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM lecciones WHERE proyecto_id = ?", (p_id,))
        n_lec = cursor.fetchone()[0]

        if n_ev == 0 and n_lec == 0:
            eliminados.append(p_nombre)
            if not dry_run:
                cursor.execute("DELETE FROM proyectos WHERE id = ?", (p_id,))

    if not dry_run and eliminados:
        db._conn.commit()

    return eliminados


def _rellenar_rutas_faltantes(
    db: PersonalDB,
    dry_run: bool = False,
    rutas_candidatas: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Intenta localizar en disco y registrar la ruta de proyectos sin ruta.

    Args:
        db: Base de datos personal conectada.
        dry_run: Si es True, solo reporta.
        rutas_candidatas: Rutas base donde buscar repositorios.

    Returns:
        list[tuple[str, str]]: Lista de (nombre_proyecto, ruta_encontrada).
    """
    cursor = db._conn.cursor()
    cursor.execute("SELECT id, nombre, ruta FROM proyectos WHERE ruta = '' OR ruta IS NULL")
    filas_sin_ruta = cursor.fetchall()
    if not filas_sin_ruta:
        return []

    from context_map.application.commands.personal import (
        _bases_por_defecto,
        _descubrir_proyectos,
    )

    bases = _bases_por_defecto()
    if rutas_candidatas:
        bases.extend(rutas_candidatas)

    # Descubrir proyectos en disco
    mapeo_disco: dict[str, str] = {}
    for base in bases:
        if os.path.isdir(base):
            for proy_nom, proy_ruta in _descubrir_proyectos(base):
                clave = _normalizar_identidad(proy_nom)
                mapeo_disco.setdefault(clave, proy_ruta)

    rellenadas: list[tuple[str, str]] = []
    for f in filas_sin_ruta:
        p_id, p_nombre = f[0], f[1]
        clave = _normalizar_identidad(p_nombre)
        ruta_hallada = mapeo_disco.get(clave)
        if ruta_hallada:
            rellenadas.append((p_nombre, ruta_hallada))
            if not dry_run:
                cursor.execute(
                    "UPDATE proyectos SET ruta = ? WHERE id = ?",
                    (ruta_hallada, p_id),
                )

    if not dry_run and rellenadas:
        db._conn.commit()

    return rellenadas


# ---------------------------------------------------------------------------
# Operación principal de reparación
# ---------------------------------------------------------------------------


def reparar_bd_personal(
    db: PersonalDB,
    dry_run: bool = False,
    merge_duplicados: bool = True,
    fill_ruta: bool = True,
    drop_vacios: bool = True,
    purge_ruido: bool = True,
    vacuum: bool = True,
    rutas_busqueda: list[str] | None = None,
) -> RepairReport:
    """Ejecuta el saneamiento integral e idempotente de la BD personal.

    Args:
        db: Instancia conectada a la base de datos personal.
        dry_run: Modo simulación sin modificar datos.
        merge_duplicados: Fusionar registros duplicados por nombre.
        fill_ruta: Autocompletar rutas vacías descubiertas en disco.
        drop_vacios: Eliminar proyectos sin eventos ni lecciones.
        purge_ruido: Eliminar eventos de falso positivo y archivos de sistema.
        vacuum: Reconstruir índices FTS5 y ejecutar VACUUM de SQLite.
        rutas_busqueda: Rutas adicionales para descubrimiento de repositorios.

    Returns:
        RepairReport: Resumen detallado de las operaciones efectuadas.
    """
    report = RepairReport(dry_run=dry_run)

    # 1. Purgar eventos de ruido
    if purge_ruido:
        report.eventos_ruido_purgados = _purgar_eventos_ruido(db, dry_run=dry_run)

    # 2. Fusionar proyectos duplicados
    if merge_duplicados:
        report.duplicados_fusionados = _fusionar_proyectos_duplicados(db, dry_run=dry_run)

    # 3. Eliminar proyectos vacíos
    if drop_vacios:
        report.proyectos_vacios_eliminados = _eliminar_proyectos_vacios(db, dry_run=dry_run)

    # 4. Rellenar rutas faltantes
    if fill_ruta:
        report.rutas_rellenadas = _rellenar_rutas_faltantes(
            db, dry_run=dry_run, rutas_candidatas=rutas_busqueda
        )

    # 5. Reconstrucción de FTS5 y VACUUM
    if vacuum and not dry_run:
        try:
            db._conn.execute("INSERT INTO eventos_fts(eventos_fts) VALUES('rebuild')")
            db._conn.execute("INSERT INTO lecciones_fts(lecciones_fts) VALUES('rebuild')")
            db._conn.execute("INSERT INTO decisiones_fts(decisiones_fts) VALUES('rebuild')")
            db._conn.commit()
            report.fts_reconstruido = True
        except Exception as err:
            logger.debug("Reconstrucción FTS5 omitida: %s", err)

        try:
            db._conn.commit()
            old_iso = db._conn.isolation_level
            db._conn.isolation_level = None
            db._conn.execute("VACUUM")
            db._conn.isolation_level = old_iso
            report.vacuum_ejecutado = True
        except Exception as err:
            logger.debug("VACUUM omitido: %s", err)

    return report


def formatear_repair_texto(report: RepairReport) -> str:
    """Genera la salida legible para consola del resultado de repair.

    Args:
        report: RepairReport generado.

    Returns:
        str: Texto estructurado con viñetas y métricas.
    """
    lineas: list[str] = []
    modo_txt = " [DRY-RUN - SIMULACIÓN]" if report.dry_run else ""
    lineas.append("=" * 76)
    lineas.append(f"🛠️ REPARACIÓN Y SANEAMIENTO DE BD PERSONAL{modo_txt}")
    lineas.append("=" * 76)

    # 1. Ruido purgado
    lineas.append(f"🧹 Eventos de ruido purgados: {report.eventos_ruido_purgados}")

    # 2. Duplicados fusionados
    if report.duplicados_fusionados:
        lineas.append(f"🔀 Proyectos duplicados fusionados ({len(report.duplicados_fusionados)}):")
        for f in report.duplicados_fusionados:
            lineas.append(f"   • {f}")
    else:
        lineas.append("🔀 Proyectos duplicados: 0 (todo limpio)")

    # 3. Proyectos vacíos
    if report.proyectos_vacios_eliminados:
        lineas.append(f"🗑️ Proyectos vacíos eliminados ({len(report.proyectos_vacios_eliminados)}):")
        for v in report.proyectos_vacios_eliminados:
            lineas.append(f"   • {v}")
    else:
        lineas.append("🗑️ Proyectos vacíos: 0")

    # 4. Rutas rellenadas
    if report.rutas_rellenadas:
        lineas.append(f"📍 Rutas de proyectos rellenadas ({len(report.rutas_rellenadas)}):")
        for nom, r in report.rutas_rellenadas:
            lineas.append(f"   • {nom} → {r}")
    else:
        lineas.append("📍 Rutas rellenadas: 0 (rutas ya pobladas o sin match en disco)")

    # 5. Mantenimiento SQLite
    if not report.dry_run:
        lineas.append(f"⚡ Índices FTS5 reconstruidos: {'Sí' if report.fts_reconstruido else 'No'}")
        lineas.append(f"📦 VACUUM y compactación ejecutada: {'Sí' if report.vacuum_ejecutado else 'No'}")

    lineas.append("=" * 76)
    return "\n".join(lineas)

"""Lógica pura de generación de Panorama y Timeline Multi-Proyecto.

Proporciona agregación, análisis de semáforos de actividad, detección de sesiones
reales (Hermes), extracción de eventos con fecha y resumen de foco para la
gestión integral de múltiples repositorios gobernados por ContextMap.
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from typing import Any

from context_map.core.personal.bd import PersonalDB
from context_map.infrastructure.integrations.hermes import leer_sesiones

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Modelos de datos
# ---------------------------------------------------------------------------


@dataclass
class SesionActividad:
    """Representa una sesión interactiva real de trabajo (ej. Hermes).

    Attributes:
        fecha: Fecha en formato YYYY-MM-DD.
        proyecto: Nombre del proyecto asociado.
        titulo: Título o intención de la sesión.
        mensajes: Cantidad total de interacciones/mensajes.
        timestamp: Marca de tiempo ISO completa de inicio.
    """

    fecha: str
    proyecto: str
    titulo: str
    mensajes: int
    timestamp: str = ""


@dataclass
class ProyectoPanorama:
    """Diagnóstico y estado consolidado de un proyecto.

    Attributes:
        nombre: Nombre del proyecto.
        ruta: Ruta local del proyecto en disco.
        ultimo_sync: Fecha del último sync registrado en BD.
        ultima_actividad: Fecha más reciente de trabajo real detectada.
        dias_inactivo: Días transcurridos desde la última actividad (o None).
        semaforo: Estado de actividad ('activo', 'tibio', 'dormido', 'vacio').
        total_eventos: Cantidad de eventos registrados.
        total_lecciones: Cantidad de lecciones en 8.0-KNOWLEDGE.
        total_decisiones: Cantidad de decisiones registradas.
        riesgos_vigentes: Lista de riesgos críticos identificados.
        pendientes_vigentes: Lista de tareas pendientes o TODOs prioritarios.
        sesiones_recientes: Cantidad de sesiones de trabajo en la ventana analizada.
    """

    nombre: str
    ruta: str = ""
    ultimo_sync: str = ""
    ultima_actividad: str = ""
    dias_inactivo: int | None = None
    semaforo: str = "dormido"
    total_eventos: int = 0
    total_lecciones: int = 0
    total_decisiones: int = 0
    riesgos_vigentes: list[str] = field(default_factory=list)
    pendientes_vigentes: list[str] = field(default_factory=list)
    sesiones_recientes: int = 0


@dataclass
class TimelineItem:
    """Elemento individual de la línea temporal unificada.

    Attributes:
        fecha: Fecha en formato YYYY-MM-DD.
        timestamp: Marca de tiempo ISO.
        proyecto: Nombre del proyecto.
        tipo: Tipo de hito ('SESION', 'IDEA', 'CORRECCION', 'CAMBIO', 'LECCION', 'DECISION').
        descripcion: Resumen legible de la actividad.
        fuente: Origen del evento (ej. 'hermes:state.db', 'vault', 'scanner').
    """

    fecha: str
    timestamp: str
    proyecto: str
    tipo: str
    descripcion: str
    fuente: str = ""


@dataclass
class PanoramaReport:
    """Reporte consolidado del panorama multi-proyecto.

    Attributes:
        fecha_generacion: Marca de tiempo ISO de la generación.
        dias_analizados: Ventana temporal en días.
        proyectos: Lista de proyectos analizados con sus semáforos.
        sesiones: Lista de sesiones de trabajo en la ventana analizada.
        foco_sugerido: Recomendaciones de proyectos que requieren atención.
        resumen_semaforo: Conteo de proyectos por categoría de semáforo.
    """

    fecha_generacion: str
    dias_analizados: int
    proyectos: list[ProyectoPanorama] = field(default_factory=list)
    sesiones: list[SesionActividad] = field(default_factory=list)
    foco_sugerido: list[str] = field(default_factory=list)
    resumen_semaforo: dict[str, int] = field(
        default_factory=lambda: {"activo": 0, "tibio": 0, "dormido": 0, "vacio": 0}
    )

    def to_dict(self) -> dict[str, Any]:
        """Convierte el reporte a un diccionario serializable para JSON.

        Returns:
            dict[str, Any]: Estructura de datos completa del reporte.
        """
        return asdict(self)


# ---------------------------------------------------------------------------
# Utilidades de clasificación y coincidencia
# ---------------------------------------------------------------------------


def _normalizar_clave(texto: str) -> str:
    """Normaliza un texto para comparaciones de identidad de proyectos.

    Args:
        texto: Nombre, ruta o título a normalizar.

    Returns:
        str: Cadena en minúsculas sin guiones ni caracteres redundantes.
    """
    if not texto:
        return ""
    limpio = texto.lower().replace("-", " ").replace("_", " ")
    return " ".join(limpio.split())


def _coincide_sesion_con_proyecto(
    cwd: str,
    git_root: str,
    titulo: str,
    nombre_proy: str,
    ruta_proy: str,
) -> bool:
    """Determina si una sesión de trabajo pertenece a un proyecto específico.

    Args:
        cwd: Directorio de trabajo de la sesión.
        git_root: Raíz de git de la sesión.
        titulo: Título de la sesión.
        nombre_proy: Nombre del proyecto en la BD.
        ruta_proy: Ruta registrada del proyecto en la BD.

    Returns:
        bool: True si la sesión corresponde al proyecto.
    """
    if ruta_proy:
        r_norm = os.path.normcase(os.path.realpath(ruta_proy))
        if cwd and os.path.normcase(os.path.realpath(cwd)).startswith(r_norm):
            return True
        if git_root and os.path.normcase(os.path.realpath(git_root)).startswith(r_norm):
            return True

    clave_proy = _normalizar_clave(nombre_proy)
    if not clave_proy:
        return False

    if cwd and clave_proy in _normalizar_clave(cwd):
        return True
    if git_root and clave_proy in _normalizar_clave(git_root):
        return True
    return bool(titulo and clave_proy in _normalizar_clave(titulo))


def _calcular_dias_inactivo(fecha_iso: str, ahora: datetime) -> int | None:
    """Calcula los días transcurridos desde una fecha ISO hasta hoy.

    Args:
        fecha_iso: Cadena con fecha ISO o YYYY-MM-DD.
        ahora: Fecha y hora de referencia.

    Returns:
        int | None: Cantidad de días enteros o None si no hay fecha válida.
    """
    if not fecha_iso:
        return None
    try:
        dt = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00"))
        # Si dt tiene tzinfo y ahora no, o viceversa, normalizamos a naive
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        delta = ahora - dt
        return max(0, delta.days)
    except Exception:
        pass

    try:
        dt = datetime.strptime(fecha_iso[:10], "%Y-%m-%d")
        delta = ahora - dt
        return max(0, delta.days)
    except Exception:
        return None


def _determinar_semaforo(
    total_eventos: int,
    total_lecciones: int,
    dias_inactivo: int | None,
) -> str:
    """Calcula el estado del semáforo según la inactividad y contenido.

    Args:
        total_eventos: Total de eventos en BD.
        total_lecciones: Total de lecciones en BD.
        dias_inactivo: Días transcurridos sin actividad.

    Returns:
        str: 'activo' (<=7d), 'tibio' (<=21d), 'dormido' (>21d), 'vacio' (0 contenido).
    """
    if total_eventos == 0 and total_lecciones == 0:
        return "vacio"
    if dias_inactivo is None:
        return "dormido"
    if dias_inactivo <= 7:
        return "activo"
    if dias_inactivo <= 21:
        return "tibio"
    return "dormido"


# ---------------------------------------------------------------------------
# Construcción del Panorama y Timeline
# ---------------------------------------------------------------------------


def construir_panorama(
    db: PersonalDB,
    dias: int = 14,
    proyecto: str | None = None,
    solo_sesiones: bool = False,
    hermes_db_path: str | None = None,
    referencia_tiempo: datetime | None = None,
) -> PanoramaReport:
    """Construye el reporte consolidado de panorama multi-proyecto.

    Args:
        db: Instancia conectada a la base de datos personal.
        dias: Ventana temporal en días para análisis de actividad.
        proyecto: Filtrar reporte por un proyecto específico (opcional).
        solo_sesiones: Si es True, omite métricas de eventos y enfoca solo en sesiones.
        hermes_db_path: Ruta a la base de datos de Hermes (None = resolver).
        referencia_tiempo: Fecha de referencia para pruebas temporales.

    Returns:
        PanoramaReport: Objeto con toda la información analizada.
    """
    ahora = referencia_tiempo or datetime.now()
    limite_dt = ahora - timedelta(days=dias)
    limite_iso = limite_dt.strftime("%Y-%m-%d")

    # 1. Obtener proyectos registrados
    cursor = db._conn.cursor()
    cursor.execute("SELECT id, nombre, ruta, ultimo_sync FROM proyectos ORDER BY nombre ASC")
    filas_proyectos = cursor.fetchall()

    if proyecto:
        clave_filtro = _normalizar_clave(proyecto)
        filas_proyectos = [
            f for f in filas_proyectos if _normalizar_clave(f["nombre"]) == clave_filtro
        ]

    # 2. Leer sesiones reales de Hermes
    sesiones_hermes = leer_sesiones(db_path=hermes_db_path, limite=200)
    sesiones_por_proy: dict[str, list[SesionActividad]] = {}
    todas_sesiones: list[SesionActividad] = []

    for s in sesiones_hermes:
        fecha_s = s.fecha_inicio[:10] if s.fecha_inicio else ""
        if not fecha_s:
            continue
        if fecha_s < limite_iso:
            continue

        # Asociar sesión al proyecto correspondiente
        proy_asociado: str | None = None
        for p in filas_proyectos:
            if _coincide_sesion_con_proyecto(
                s.cwd, s.git_repo_root, s.titulo, p["nombre"], p["ruta"]
            ):
                proy_asociado = p["nombre"]
                break

        if not proy_asociado and not proyecto:
            # Si no coincide con ninguno registrado pero tiene título relevante
            proy_asociado = os.path.basename(s.cwd or s.git_repo_root) or "Global"

        if proyecto and proy_asociado != proyecto:
            continue

        item_sesion = SesionActividad(
            fecha=fecha_s,
            proyecto=proy_asociado or "Desconocido",
            titulo=s.titulo,
            mensajes=len(s.mensajes),
            timestamp=s.fecha_inicio,
        )
        todas_sesiones.append(item_sesion)
        if proy_asociado:
            sesiones_por_proy.setdefault(proy_asociado, []).append(item_sesion)

    # 3. Analizar métricas de cada proyecto
    proyectos_panorama: list[ProyectoPanorama] = []
    conteos_semaforo = {"activo": 0, "tibio": 0, "dormido": 0, "vacio": 0}
    foco_sugerido: list[str] = []

    for p in filas_proyectos:
        p_id = p["id"]
        p_nombre = p["nombre"]
        p_ruta = p["ruta"]
        p_sync = p["ultimo_sync"]

        # Conteo de eventos y lecciones
        cursor.execute("SELECT count(*) FROM eventos WHERE proyecto_id = ?", (p_id,))
        total_ev = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM lecciones WHERE proyecto_id = ?", (p_id,))
        total_lec = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM decisiones WHERE proyecto_id = ?", (p_id,))
        total_dec = cursor.fetchone()[0]

        # Obtener fecha más reciente de eventos válidos
        cursor.execute(
            "SELECT max(timestamp) FROM eventos WHERE proyecto_id = ? AND timestamp != ''",
            (p_id,),
        )
        max_ts_ev = cursor.fetchone()[0] or ""

        # Sesiones de hermes para este proyecto
        ses_proy = sesiones_por_proy.get(p_nombre, [])
        max_ts_ses = max([s.timestamp for s in ses_proy], default="")

        # Última actividad consolidada: priorizar trabajo real (sesiones y eventos fechados)
        # sobre la fecha técnica de sincronización de la BD (ultimo_sync)
        fechas_reales = [f for f in (max_ts_ses, max_ts_ev) if f]
        ultima_act = max(fechas_reales) if fechas_reales else p_sync

        dias_inactivo = _calcular_dias_inactivo(ultima_act, ahora)
        semaforo = _determinar_semaforo(total_ev, total_lec, dias_inactivo)
        conteos_semaforo[semaforo] += 1

        # Extraer riesgos vigentes
        cursor.execute(
            "SELECT texto FROM eventos WHERE proyecto_id = ? AND tipo = 'RIESGO' "
            "ORDER BY id DESC LIMIT 3",
            (p_id,),
        )
        riesgos = [row[0] for row in cursor.fetchall()]

        # Extraer pendientes / TODOs vigentes
        cursor.execute(
            "SELECT texto FROM eventos WHERE proyecto_id = ? AND tipo = 'FUTURO' "
            "ORDER BY id DESC LIMIT 3",
            (p_id,),
        )
        pendientes = [row[0] for row in cursor.fetchall()]

        item_p = ProyectoPanorama(
            nombre=p_nombre,
            ruta=p_ruta,
            ultimo_sync=p_sync,
            ultima_actividad=ultima_act,
            dias_inactivo=dias_inactivo,
            semaforo=semaforo,
            total_eventos=total_ev,
            total_lecciones=total_lec,
            total_decisiones=total_dec,
            riesgos_vigentes=riesgos,
            pendientes_vigentes=pendientes,
            sesiones_recientes=len(ses_proy),
        )
        proyectos_panorama.append(item_p)

        # Determinar foco sugerido: proyectos tibios con riesgos o tareas pendientes
        if semaforo in ("activo", "tibio") and (riesgos or pendientes):
            foco_sugerido.append(
                f"{p_nombre} ({semaforo}, {len(pendientes)} pendientes, {len(riesgos)} riesgos)"
            )

    # Ordenar proyectos: activos primero, luego tibios, dormidos y vacíos
    orden_sem = {"activo": 0, "tibio": 1, "dormido": 2, "vacio": 3}
    proyectos_panorama.sort(
        key=lambda x: (orden_sem.get(x.semaforo, 99), x.dias_inactivo or 9999)
    )

    return PanoramaReport(
        fecha_generacion=ahora.isoformat(timespec="seconds"),
        dias_analizados=dias,
        proyectos=proyectos_panorama,
        sesiones=todas_sesiones,
        foco_sugerido=foco_sugerido,
        resumen_semaforo=conteos_semaforo,
    )


def construir_timeline(
    db: PersonalDB,
    dias: int = 30,
    proyecto: str | None = None,
    hermes_db_path: str | None = None,
    referencia_tiempo: datetime | None = None,
) -> list[TimelineItem]:
    """Genera una línea temporal unificada de sesiones y eventos con fecha.

    Args:
        db: Instancia conectada a la base de datos personal.
        dias: Días hacia atrás a incluir.
        proyecto: Filtrar por proyecto específico (opcional).
        hermes_db_path: Ruta a la BD de Hermes (None = resolver).
        referencia_tiempo: Fecha de referencia para pruebas temporales.

    Returns:
        list[TimelineItem]: Lista ordenada cronológicamente de actividades.
    """
    ahora = referencia_tiempo or datetime.now()
    limite_dt = ahora - timedelta(days=dias)
    limite_iso = limite_dt.strftime("%Y-%m-%d")

    items: list[TimelineItem] = []

    # 1. Sesiones de Hermes
    sesiones = leer_sesiones(db_path=hermes_db_path, limite=300)
    for s in sesiones:
        f_inicio = s.fecha_inicio
        fecha = f_inicio[:10] if f_inicio else ""
        if not fecha or fecha < limite_iso:
            continue

        proy = os.path.basename(s.cwd or s.git_repo_root) or "Global"
        if proyecto and _normalizar_clave(proyecto) != _normalizar_clave(proy):
            continue

        items.append(
            TimelineItem(
                fecha=fecha,
                timestamp=f_inicio,
                proyecto=proy,
                tipo="SESION",
                descripcion=f"{s.titulo} ({len(s.mensajes)} msgs)",
                fuente="hermes:state.db",
            )
        )

    # 2. Eventos con fecha en la BD personal
    cursor = db._conn.cursor()
    query = """
        SELECT p.nombre, e.tipo, e.texto, e.timestamp, e.fuente
        FROM eventos e
        JOIN proyectos p ON e.proyecto_id = p.id
        WHERE e.timestamp != '' AND e.timestamp >= ?
    """
    params: list[Any] = [limite_iso]
    if proyecto:
        query += " AND lower(p.nombre) = lower(?)"
        params.append(proyecto)

    cursor.execute(query, tuple(params))
    for row in cursor.fetchall():
        ts = row["timestamp"]
        items.append(
            TimelineItem(
                fecha=ts[:10],
                timestamp=ts,
                proyecto=row["nombre"],
                tipo=row["tipo"],
                descripcion=row["texto"][:120],
                fuente=row["fuente"] or "events.jsonl",
            )
        )

    # Ordenar cronológicamente descendente (más reciente primero)
    items.sort(key=lambda x: (x.timestamp or x.fecha), reverse=True)
    return items


# ---------------------------------------------------------------------------
# Formateadores de Texto para CLI y Agentes
# ---------------------------------------------------------------------------


def formatear_panorama_texto(report: PanoramaReport) -> str:
    """Genera la visualización en texto plano y tablas para la consola.

    Args:
        report: PanoramaReport generado.

    Returns:
        str: Texto formateado con semáforos, tablas de proyectos y sesiones.
    """
    lineas: list[str] = []
    lineas.append("=" * 76)
    lineas.append(f"🌐 PANORAMA MULTI-PROYECTO — Últimos {report.dias_analizados} días")
    lineas.append("=" * 76)

    # Resumen de semáforo
    res = report.resumen_semaforo
    lineas.append(
        f"📊 Estado: 🟢 {res['activo']} Activos (≤7d)  |  "
        f"🟡 {res['tibio']} Tibios (≤21d)  |  "
        f"🔴 {res['dormido']} Dormidos (>21d)  |  "
        f"⚪ {res['vacio']} Vacíos"
    )
    lineas.append("-" * 76)

    # Tabla de Proyectos
    lineas.append(
        f"{'Proyecto':<22} {'Semáforo':<10} {'Inactivo':<10} {'Eventos':<8} {'Lecc/Dec':<10} {'Sesiones':<8}"
    )
    lineas.append("-" * 76)

    icono_sem = {
        "activo": "🟢 Activo",
        "tibio": "🟡 Tibio",
        "dormido": "🔴 Dormido",
        "vacio": "⚪ Vacío",
    }

    for p in report.proyectos:
        inactivo_txt = f"{p.dias_inactivo}d" if p.dias_inactivo is not None else "—"
        lecc_dec = f"{p.total_lecciones}/{p.total_decisiones}"
        nombre_trunc = p.nombre[:20] + ".." if len(p.nombre) > 22 else p.nombre
        lineas.append(
            f"{nombre_trunc:<22} {icono_sem.get(p.semaforo, p.semaforo):<10} "
            f"{inactivo_txt:<10} {p.total_eventos:<8} {lecc_dec:<10} {p.sesiones_recientes:<8}"
        )

    # Sesiones reales de Hermes
    lineas.append("")
    lineas.append("🗓️ SESIONES REALES DE TRABAJO (Hermes):")
    if report.sesiones:
        # Agrupar por fecha
        por_fecha: dict[str, list[SesionActividad]] = {}
        for s in report.sesiones:
            por_fecha.setdefault(s.fecha, []).append(s)

        for f in sorted(por_fecha.keys(), reverse=True):
            lineas.append(f"  [{f}]")
            for ses in por_fecha[f]:
                lineas.append(f"    • {ses.proyecto:<18} │ {ses.titulo} ({ses.mensajes} msgs)")
    else:
        lineas.append("  (No se registraron sesiones interactivas en el periodo analizado)")

    # Foco sugerido
    if report.foco_sugerido:
        lineas.append("")
        lineas.append("🎯 FOCO SUGERIDO:")
        for item in report.foco_sugerido:
            lineas.append(f"  👉 {item}")

    lineas.append("=" * 76)
    return "\n".join(lineas)


def formatear_timeline_texto(items: list[TimelineItem]) -> str:
    """Genera la visualización cronológica en texto para la consola.

    Args:
        items: Lista de TimelineItem ordenados.

    Returns:
        str: Línea de tiempo formateada.
    """
    lineas: list[str] = []
    lineas.append("=" * 76)
    lineas.append("⏱️ LÍNEA TEMPORAL DE ACTIVIDAD MULTI-PROYECTO")
    lineas.append("=" * 76)

    if not items:
        lineas.append("  (No hay actividad registrada con fecha en este periodo)")
        lineas.append("=" * 76)
        return "\n".join(lineas)

    fecha_actual = ""
    for it in items:
        if it.fecha != fecha_actual:
            fecha_actual = it.fecha
            lineas.append(f"\n📅 {fecha_actual}")

        hora = it.timestamp[11:16] if len(it.timestamp) >= 16 else "      "
        lineas.append(f"  [{hora}] [{it.tipo:<9}] [{it.proyecto:<16}] {it.descripcion}")

    lineas.append("")
    lineas.append("=" * 76)
    return "\n".join(lineas)

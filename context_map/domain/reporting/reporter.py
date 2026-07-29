from __future__ import annotations

"""Generador de reportes periódicos y semanales.

Responsabilidades:
- Consolidar eventos registrados en los grafos de contexto.
- Filtrar la actividad recente por ventana de tiempo.
- Construir reportes estadísticos formateados en Markdown.
"""

import json
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List


def _cargar_eventos(state_dir: str) -> List[Dict]:
    """Carga los eventos JSONL almacenados en el directorio de estado.

    Args:
        state_dir (str): Directorio del estado `.context-map`.

    Returns:
        List[Dict]: Lista de diccionarios de eventos.
    """
    eventos: List[Dict] = []
    graph_path = os.path.join(state_dir, "graph.jsonl")

    if os.path.exists(graph_path):
        try:
            with open(graph_path, "r", encoding="utf-8") as f:
                for linea in f:
                    linea_str = linea.strip()
                    if linea_str:
                        try:
                            eventos.append(json.loads(linea_str))
                        except Exception:
                            pass
        except Exception:
            pass

    return eventos


def _filtrar_por_fecha(eventos: List[Dict], dias: int = 7) -> List[Dict]:
    """Filtra la lista de eventos por antigüedad relativa en días.

    Args:
        eventos (List[Dict]): Lista de eventos.
        dias (int): Días máximos de antigüedad.

    Returns:
        List[Dict]: Eventos filtrados.
    """
    ahora = datetime.now()
    desde = ahora - timedelta(days=dias)

    filtrados: List[Dict] = []
    for e in eventos:
        ts = e.get("timestamp", "")
        if ts:
            try:
                fecha = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if fecha >= desde:
                    filtrados.append(e)
            except Exception:
                filtrados.append(e)
        else:
            filtrados.append(e)

    return filtrados


def _contar_por_tipo(eventos: List[Dict]) -> Dict[str, int]:
    """Cuenta el número de eventos acumulados por cada tipo.

    Args:
        eventos (List[Dict]): Lista de eventos.

    Returns:
        Dict[str, int]: Diccionario con las cantidades por tipo.
    """
    counter: Counter[str] = Counter()
    for e in eventos:
        tipo = e.get("type", "UNKNOWN")
        counter[tipo] += 1
    return dict(counter)


def _top_eventos(eventos: List[Dict], n: int = 5) -> List[str]:
    """Obtiene los títulos/textos de los N eventos más recientes.

    Args:
        eventos (List[Dict]): Lista de eventos.
        n (int): Cantidad de eventos a extraer.

    Returns:
        List[str]: Textos recortados.
    """
    return [e.get("text", "")[:100] for e in eventos[:n]]


def generar_semanal(state_dir: str, dias: int = 7) -> str:
    """Genera un reporte semanal formateado en Markdown.

    Args:
        state_dir (str): Ruta del directorio de estado.
        dias (int): Número de días a considerar (predeterminado 7).

    Returns:
        str: Contenido Markdown del reporte.
    """
    eventos = _cargar_eventos(state_dir)
    eventos_recientes = _filtrar_por_fecha(eventos, dias)

    por_tipo = _contar_por_tipo(eventos_recientes)
    total = len(eventos_recientes)
    top = _top_eventos(eventos_recientes)

    tipos_emoji = {
        "BASE": "📦",
        "IDEA": "💡",
        "RIESGO": "⚠️",
        "CAMBIO": "🔄",
        "PRUEBA": "🧪",
        "FUTURO": "🔮",
        "HITO": "🎯",
        "CORRECCION": "🔧",
    }

    lineas = [
        "# 📊 Reporte Semanal",
        "",
        f"**Período**: Últimos {dias} días",
        f"**Total de eventos**: {total}",
        "",
        "## Distribución por tipo",
        "",
    ]

    for tipo, count in sorted(por_tipo.items(), key=lambda x: -x[1]):
        emoji = tipos_emoji.get(tipo, "❓")
        lineas.append(f"- {emoji} **{tipo}**: {count}")

    if top:
        lineas.extend(["", "## Top eventos recientes", ""])
        for i, evento in enumerate(top, 1):
            lineas.append(f"{i}. {evento}")

    lineas.extend(["", "## Resumen", ""])

    if "IDEA" in por_tipo:
        lineas.append(f"- 💡 Se generaron {por_tipo['IDEA']} ideas nuevas")
    if "RIESGO" in por_tipo:
        lineas.append(f"- ⚠️ Se identificaron {por_tipo['RIESGO']} riesgos")
    if "CORRECCION" in por_tipo:
        lineas.append(f"- 🔧 Se realizaron {por_tipo['CORRECCION']} correcciones")
    if "HITO" in por_tipo:
        lineas.append(f"- 🎯 Se alcanzaron {por_tipo['HITO']} hitos")

    if total == 0:
        lineas.append("- Sin actividad registrada en este período")

    return "\n".join(lineas)


def guardar_reporte(state_dir: str, output_path: str, dias: int = 7) -> str:
    """Genera y persiste en disco un reporte de actividad.

    Args:
        state_dir (str): Directorio de estado `.context-map`.
        output_path (str): Ruta de salida para el archivo de reporte.
        dias (int): Ventana temporal en días.

    Returns:
        str: Ruta final del archivo guardado.
    """
    reporte = generar_semanal(state_dir, dias)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reporte)

    return output_path

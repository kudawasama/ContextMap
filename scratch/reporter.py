"""Generador de reportes semanales.

Crea resúmenes de actividad del proyecto.
"""

from __future__ import annotations

import json
import os
from typing import List, Dict
from datetime import datetime, timedelta
from collections import Counter


def _cargar_eventos(state_dir: str) -> List[Dict]:
    """Carga eventos del grafo."""
    eventos = []
    graph_path = os.path.join(state_dir, "graph.jsonl")

    if os.path.exists(graph_path):
        with open(graph_path, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        eventos.append(json.loads(linea))
                    except Exception:
                        pass

    return eventos


def _filtrar_por_fecha(eventos: List[Dict], dias: int = 7) -> List[Dict]:
    """Filtra eventos por fecha."""
    ahora = datetime.now()
    desde = ahora - timedelta(days=dias)

    filtrados = []
    for e in eventos:
        ts = e.get("timestamp", "")
        if ts:
            try:
                fecha = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if fecha >= desde:
                    filtrados.append(e)
            except Exception:
                # Si no se puede parsear, incluir
                filtrados.append(e)
        else:
            filtrados.append(e)

    return filtrados


def _contar_por_tipo(eventos: List[Dict]) -> Dict[str, int]:
    """Cuenta eventos por tipo."""
    counter = Counter()
    for e in eventos:
        tipo = e.get("type", "UNKNOWN")
        counter[tipo] += 1
    return dict(counter)


def _top_eventos(eventos: List[Dict], n: int = 5) -> List[str]:
    """Retorna los N eventos más recientes."""
    return [e.get("text", "")[:100] for e in eventos[:n]]


def generar_semanal(state_dir: str, dias: int = 7) -> str:
    """Genera un reporte semanal.

    Returns:
        Markdown con el reporte
    """
    eventos = _cargar_eventos(state_dir)
    eventos_recientes = _filtrar_por_fecha(eventos, dias)

    # Estadísticas
    por_tipo = _contar_por_tipo(eventos_recientes)
    total = len(eventos_recientes)
    top = _top_eventos(eventos_recientes)

    # Calcular distribución
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

    # Generar reporte
    lineas = [
        f"# 📊 Reporte Semanal",
        f"",
        f"**Período**: Últimos {dias} días",
        f"**Total de eventos**: {total}",
        f"",
        f"## Distribución por tipo",
        f"",
    ]

    for tipo, count in sorted(por_tipo.items(), key=lambda x: -x[1]):
        emoji = tipos_emoji.get(tipo, "❓")
        lineas.append(f"- {emoji} **{tipo}**: {count}")

    if top:
        lineas.extend([
            f"",
            f"## Top eventos recientes",
            f"",
        ])
        for i, evento in enumerate(top, 1):
            lineas.append(f"{i}. {evento}")

    # Resumen
    lineas.extend([
        f"",
        f"## Resumen",
        f"",
    ])

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
    """Genera y guarda el reporte semanal.

    Returns:
        Ruta del archivo generado
    """
    reporte = generar_semanal(state_dir, dias)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(reporte)

    return output_path

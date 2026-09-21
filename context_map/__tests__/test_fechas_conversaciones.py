"""Pruebas de fechas en los eventos derivados de conversaciones.

Regresión de la auditoría 2026-09-21: el ``state.db`` de Hermes guarda
``started_at``/``timestamp`` como epoch Unix y el importador los propagaba en
crudo; 305 de los 313 eventos sin fecha de la BD personal venían de aquí, así
que el historial por día solo mostraba re-escaneos automáticos.
"""

from __future__ import annotations

from datetime import datetime

from context_map.core.parsing.cargadores import (
    _fecha_de_conversacion,
    load_events_from_chat_folder,
)
from context_map.infrastructure.integrations.hermes import (
    Mensaje,
    Sesion,
    _a_iso,
    extraer_contexto_sesion,
)


def _sesion(mensajes: list[Mensaje], fecha: str = "") -> Sesion:
    """Sesión mínima para probar la propagación de fechas."""
    return Sesion(id="s1", titulo="Sesión de prueba", fecha_inicio=fecha, mensajes=mensajes)


def test_a_iso_normaliza_epoch_y_texto() -> None:
    """El epoch de Hermes se convierte a ISO legible; lo inválido queda vacío."""
    assert _a_iso("1789415350.33120").startswith("2026-09-")
    assert _a_iso("2026-08-14T10:00:00").startswith("2026-08-14")
    assert _a_iso("") == ""
    assert _a_iso("no-es-fecha") == ""


def test_eventos_de_sesion_heredan_la_fecha_del_mensaje() -> None:
    """Cada evento hereda la fecha del mensaje que lo originó."""
    sesion = _sesion(
        [Mensaje(id=1, rol="assistant", contenido="quedó implementado el fix", timestamp="2026-09-10T12:00:00")],
        fecha="2026-09-01T00:00:00",
    )

    eventos = extraer_contexto_sesion(sesion)

    assert eventos, "la sesión debía generar eventos"
    assert all(ev["timestamp"].startswith("2026-09-10") for ev in eventos), eventos


def test_eventos_de_sesion_caen_a_la_fecha_de_inicio() -> None:
    """Sin fecha en el mensaje se usa la de inicio de la sesión."""
    sesion = _sesion(
        [Mensaje(id=1, rol="user", contenido="quiero decidir el orden del deploy")],
        fecha="2026-09-14T09:00:00",
    )

    eventos = extraer_contexto_sesion(sesion)

    assert eventos, "la sesión debía generar eventos"
    assert all(ev["timestamp"].startswith("2026-09-14") for ev in eventos), eventos


def test_chats_sin_fecha_en_el_nombre_usan_la_de_modificacion(tmp_path) -> None:
    """Una conversación sin fecha en el nombre se fecha con su mtime."""
    chats = tmp_path / "chats"
    chats.mkdir()
    archivo = chats / "conversacion-suelta.md"
    archivo.write_text("Aplicar la corrección del reporte de gastos\n", encoding="utf-8")

    eventos = load_events_from_chat_folder(str(chats))

    assert len(eventos) == 1
    assert eventos[0].timestamp, "el evento quedó sin fecha"
    datetime.fromisoformat(eventos[0].timestamp)  # debe ser ISO válida


def test_chats_con_fecha_en_el_nombre_la_usan(tmp_path) -> None:
    """Los exports nombrados `YYYY-MM-DD...` o `YYYYMMDD_...` usan esa fecha."""
    chats = tmp_path / "chats"
    chats.mkdir()
    (chats / "2026-09-14_sesion.md").write_text("Aplicar la corrección del reporte\n", encoding="utf-8")
    (chats / "20260813_104604_0451d1.md").write_text("Falta validar el rango de fechas\n", encoding="utf-8")

    fechas = {
        ev.source.removeprefix("chat:"): ev.timestamp[:10]
        for ev in load_events_from_chat_folder(str(chats))
    }

    assert fechas["2026-09-14_sesion.md"] == "2026-09-14"
    assert fechas["20260813_104604_0451d1.md"] == "2026-08-13"


def test_fecha_de_conversacion_ignora_nombres_sin_fecha(tmp_path) -> None:
    """Un nombre sin dígitos de fecha no inventa una fecha."""
    archivo = tmp_path / "notas.md"
    archivo.write_text("x", encoding="utf-8")
    assert _fecha_de_conversacion(str(archivo))

"""Pruebas de la lectura de carpetas de conversaciones de chat.

Regresión de la auditoría 2026-09-21: los clientes de Google Drive siembran un
``desktop.ini`` en UTF-16 dentro de ``.context-map/chats/``; al leerse como UTF-8
sus líneas (``[.ShellClassInfo]``, ``IconResource=...``) generaban eventos IDEA
basura en la BD personal de Gobernanza y reporte_mensuales.
"""

from __future__ import annotations

from context_map.core.parsing.cargadores import load_events_from_chat_folder

DESKTOP_INI_UTF16 = (
    "[.ShellClassInfo]\r\nConfirmFileOp=0\r\n"
    "IconResource=C:\\Program Files\\Google\\Drive File Stream\\130.0.2.0\\GoogleDriveFS.exe,27\r\n"
).encode("utf-16")


def test_ignora_desktop_ini_utf16(tmp_path) -> None:
    """`desktop.ini` (UTF-16 con bytes nulos) no genera eventos."""
    chats = tmp_path / "chats"
    chats.mkdir()
    (chats / "desktop.ini").write_bytes(DESKTOP_INI_UTF16)

    assert load_events_from_chat_folder(str(chats)) == []


def test_ignora_archivos_de_sistema_y_no_texto(tmp_path) -> None:
    """Otros archivos de sistema o no textuales tampoco se leen."""
    chats = tmp_path / "chats"
    chats.mkdir()
    (chats / "Thumbs.db").write_bytes(b"\x00\x01\x02")
    (chats / "imagen.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 40)

    assert load_events_from_chat_folder(str(chats)) == []


def test_lee_conversacion_real(tmp_path) -> None:
    """Un archivo de texto con conversación sí produce eventos."""
    chats = tmp_path / "chats"
    chats.mkdir()
    (chats / "sesion.md").write_text(
        "Aplicar la corrección del reporte de gastos fijos\n"
        "Falta validar el rango de fechas del export\n",
        encoding="utf-8",
    )

    eventos = load_events_from_chat_folder(str(chats))

    assert len(eventos) == 2, eventos
    assert all(ev.source == "chat:sesion.md" for ev in eventos)
    assert eventos[0].type == "CORRECCION"


def test_carpeta_inexistente_no_falla() -> None:
    """Una carpeta inexistente devuelve una lista vacía."""
    assert load_events_from_chat_folder("ruta/que/no/existe") == []

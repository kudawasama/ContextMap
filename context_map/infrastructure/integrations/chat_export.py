"""Exportador de chats externos.

Importa conversaciones de Telegram, Discord, Slack, WhatsApp, etc.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass


@dataclass
class MensajeChat:
    """Un mensaje de chat externo."""
    autor: str
    contenido: str
    timestamp: str = ""
    plataforma: str = ""


def _detectar_plataforma(ruta: str) -> str:
    """Detecta la plataforma de un archivo de chat."""
    nombre = os.path.basename(ruta).lower()

    if "telegram" in nombre:
        return "telegram"
    elif "discord" in nombre:
        return "discord"
    elif "slack" in nombre:
        return "slack"
    elif "whatsapp" in nombre:
        return "whatsapp"
    elif nombre.endswith(".json"):
        return "json"
    else:
        return "text"


def _parsear_telegram_html(ruta: str) -> list[MensajeChat]:
    """Parsea exportación de Telegram en HTML."""
    mensajes = []
    try:
        with open(ruta, encoding="utf-8") as f:
            contenido = f.read()

        # Patrón simple para Telegram HTML
        patron = r'<div class="message[^"]*"[^>]*>.*?<div class="from_name[^"]*"[^>]*>([^<]+)</div>.*?<div class="text[^"]*"[^>]*>(.*?)</div>'
        matches = re.findall(patron, contenido, re.DOTALL)

        for autor, texto in matches:
            # Limpiar HTML
            texto_limpio = re.sub(r'<[^>]+>', '', texto).strip()
            if texto_limpio:
                mensajes.append(MensajeChat(
                    autor=autor.strip(),
                    contenido=texto_limpio[:500],
                    plataforma="telegram",
                ))
    except Exception:
        pass

    return mensajes


def _parsear_texto_simple(ruta: str) -> list[MensajeChat]:
    """Parsea archivos de texto simples con formato 'Autor: mensaje'."""
    mensajes = []
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue

                # Buscar patrón "Autor: mensaje"
                match = re.match(r'^([^:]+):\s*(.+)$', linea)
                if match:
                    mensajes.append(MensajeChat(
                        autor=match.group(1).strip(),
                        contenido=match.group(2).strip()[:500],
                        plataforma="text",
                    ))
    except Exception:
        pass

    return mensajes


def _parsear_json(ruta: str) -> list[MensajeChat]:
    """Parsea archivos JSON con mensajes."""
    mensajes = []
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)

        # Soportar diferentes formatos JSON
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    mensajes.append(MensajeChat(
                        autor=str(item.get("author", item.get("user", "unknown")) or "unknown"),
                        contenido=str(item.get("content", item.get("message", "")) or "")[:500],
                        timestamp=str(item.get("timestamp", item.get("date", "")) or ""),
                        plataforma="json",
                    ))
        elif isinstance(data, dict) and "messages" in data:
            for item in data["messages"]:
                if isinstance(item, dict):
                    mensajes.append(MensajeChat(
                        autor=str(item.get("author", item.get("user", "unknown")) or "unknown"),
                        contenido=str(item.get("content", item.get("message", "")) or "")[:500],
                        timestamp=str(item.get("timestamp", item.get("date", "")) or ""),
                        plataforma="json",
                    ))
    except Exception:
        pass

    return mensajes


def parsear_chat(ruta: str) -> list[MensajeChat]:
    """Parsea un archivo de chat según su formato.

    Returns:
        Lista de mensajes parseados
    """
    plataforma = _detectar_plataforma(ruta)

    if plataforma == "telegram":
        return _parsear_telegram_html(ruta)
    elif plataforma == "json":
        return _parsear_json(ruta)
    else:
        return _parsear_texto_simple(ruta)


def clasificar_mensaje(msg: MensajeChat) -> dict:
    """Clasifica un mensaje por su contenido.

    Returns:
        Dict con type, text, tags
    """
    texto = msg.contenido.lower()

    # Detectar tipo por keywords
    if any(kw in texto for kw in ["decid", "quiero", "vamos a", "hagamos", "elegi"]):
        tipo = "IDEA"
        tags = ["decisión", msg.plataforma]
    elif any(kw in texto for kw in ["riesgo", "problema", "cuidado", "bug", "error"]):
        tipo = "RIESGO"
        tags = ["problema", msg.plataforma]
    elif any(kw in texto for kw in ["fix", "corregi", "arregl", "patch"]):
        tipo = "CORRECCION"
        tags = ["fix", msg.plataforma]
    elif any(kw in texto for kw in ["test", "prueb", "verif"]):
        tipo = "PRUEBA"
        tags = ["test", msg.plataforma]
    elif any(kw in texto for kw in ["idea", "podriamos", "que tal", "propongo"]):
        tipo = "IDEA"
        tags = ["idea", msg.plataforma]
    else:
        tipo = "CAMBIO"
        tags = ["conversación", msg.plataforma]

    return {
        "type": tipo,
        "text": f"[{msg.autor}] {msg.contenido[:200]}",
        "source": "chat",
        "tags": tags,
    }


def importar_chat(
    ruta: str,
    output_path: str = ".context-map/raw/events.jsonl",
) -> int:
    """Importa un archivo de chat como eventos.

    Returns:
        Número de eventos importados
    """
    mensajes = parsear_chat(ruta)
    eventos = [clasificar_mensaje(msg) for msg in mensajes]

    # Guardar
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Leer existentes para evitar duplicados
    existentes = set()
    if os.path.exists(output_path):
        with open(output_path, encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea:
                    try:
                        obj = json.loads(linea)
                        existentes.add(obj.get("text", "")[:80])
                    except Exception:
                        pass

    # Filtrar nuevos
    nuevos = []
    for e in eventos:
        if e["text"][:80] not in existentes:
            nuevos.append(e)

    # Guardar
    with open(output_path, "a", encoding="utf-8") as f:
        for e in nuevos:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    return len(nuevos)

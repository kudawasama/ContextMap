"""Proxy de uso de secretos: inyectar sin exponer y sanear la salida.

Principio: el valor sale del baúl solo hacia el **entorno del proceso** que se
ejecuta; la salida que se devuelve al llamante (o al agente) se **sanea**
reemplazando cada valor por ``***``. Así, aunque la aplicación ejecutada
imprimiera el secreto, este nunca llega al contexto.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

#: Longitud mínima de un valor para redactarlo (valores más cortos podrían
#: producir falsos positivos en textos legítimos).
SANEO_MIN = 4

#: Prefijo reservado del propio ContextMap. Ninguna variable con este prefijo
#: debe llegar al proceso hijo: la frase maestra y el flag de autorización son
#: credenciales del servidor, no del comando que se ejecuta.
PREFIJO_RESERVADO = "CTXMAP_"


def normalizar_var(ident: str) -> str:
    """Convierte un id de secreto en una variable de entorno segura."""
    limpio = re.sub(r"[^A-Za-z0-9_]", "_", ident).upper()
    return f"CTXMAP_SECRET_{limpio}"


def entorno_con_secretos(
    valores: dict[str, str],
    base_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Entorno con los secretos inyectados (no se imprimen nunca aquí).

    Del entorno base se eliminan **todas** las variables ``CTXMAP_*``: la frase
    maestra, el flag de autorización y cualquier secreto de una llamada previa.
    Solo llegan al hijo los valores pedidos explícitamente, como
    ``CTXMAP_SECRET_<ID>``.

    Args:
        valores: Mapa ``id`` → valor a inyectar.
        base_env: Entorno de partida (por defecto, ``os.environ``).

    Returns:
        dict[str, str]: Entorno saneado con los secretos solicitados.
    """
    env = {
        clave: valor
        for clave, valor in dict(base_env or os.environ).items()
        if not clave.upper().startswith(PREFIJO_RESERVADO)
    }
    for ident, valor in valores.items():
        env[normalizar_var(ident)] = valor
    return env


def sanear_salida(texto: str, valores: dict[str, str]) -> str:
    """Redacta los valores en la salida para que no lleguen al llamante."""
    for valor in valores.values():
        if valor and len(valor) >= SANEO_MIN:
            texto = texto.replace(valor, "***")
    return texto


def auditar(ruta_audit: str, linea: str) -> None:
    """Registra una línea de auditoría (nunca valores) sin fallar nunca."""
    try:
        os.makedirs(os.path.dirname(ruta_audit) or ".", exist_ok=True)
        with open(ruta_audit, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} | {linea}\n")
    except Exception:  # noqa: BLE001 — la auditoría no bloquea la operación
        pass

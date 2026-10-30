"""Proxy de uso de secretos: inyectar sin exponer y sanear la salida.

Principio: el valor sale del baúl solo hacia el **entorno del proceso** que se
ejecuta; la salida que se devuelve al llamante (o al agente) se **sanea**
reemplazando cada valor por ``***``. Así, aunque la aplicación ejecutada
imprimiera el secreto, este nunca llega al contexto.
"""

from __future__ import annotations

import base64
import os
import re
import urllib.parse
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


def validar_ids_sin_colision(ids: list[str]) -> None:
    """Lanza ``ValueError`` si dos ids normalizan a la misma variable.

    ``a-b`` y ``a_b`` producen ambos ``CTXMAP_SECRET_A_B`` y colisionarían en
    el entorno del proceso, provocando que un secreto sobrescriba a otro.

    Args:
        ids: Lista de ids de secreto a validar.

    Raises:
        ValueError: Si hay colisión.
    """
    vistos: dict[str, str] = {}
    for ident in ids:
        var = normalizar_var(ident)
        if var in vistos and vistos[var] != ident:
            raise ValueError(
                f"Colisión de variables: '{ident}' y '{vistos[var]}' "
                f"normalizan ambos a '{var}'. Renombra uno de ellos."
            )
        vistos[var] = ident


def variantes_de_valor(valor: str) -> list[str]:
    """Genera variantes ofuscadas de un valor para sanearlas también.

    El saneo por coincidencia exacta se evita con ``rev``, ``base64``, una
    codificación URL o hexadecimal. Se generan las variantes más comunes para
    cerrar esas vías de exfiltración por accidente.

    Args:
        valor: Valor original a proteger.

    Returns:
        list[str]: Lista de variantes (incluye el original) sin duplicados.
    """
    if not valor:
        return []
    variantes: list[str] = [valor]
    variantes.append(valor[::-1])
    variantes.append(urllib.parse.quote(valor, safe=""))
    variantes.append(urllib.parse.quote_plus(valor))
    variantes.append(base64.b64encode(valor.encode()).decode())
    variantes.append(base64.urlsafe_b64encode(valor.encode()).decode().rstrip("="))
    variantes.append(valor.encode().hex())
    variantes.append(valor.lower())
    variantes.append(valor.upper())
    vistas: set[str] = set()
    resultado: list[str] = []
    for v in variantes:
        if v and v not in vistas:
            vistas.add(v)
            resultado.append(v)
    return resultado


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
    validar_ids_sin_colision(list(valores.keys()))
    for ident, valor in valores.items():
        env[normalizar_var(ident)] = valor
    return env


def sanear_salida(
    texto: str,
    valores: dict[str, str],
    *,
    frase_maestra: str | None = None,
    variantes: bool = True,
) -> str:
    """Redacta los valores (y sus variantes) en la salida.

    Args:
        texto: Salida a sanear.
        valores: Mapa id → valor.
        frase_maestra: Si se proporciona, también se redacta (y sus variantes).
        variantes: Si True, redacta variantes ofuscadas además del valor exacto.

    Returns:
        str: Texto con los valores redactados.
    """
    candidatos: list[str] = []
    for valor in valores.values():
        if not valor:
            continue
        if variantes:
            candidatos.extend(variantes_de_valor(valor))
        else:
            candidatos.append(valor)
    if frase_maestra:
        if variantes:
            candidatos.extend(variantes_de_valor(frase_maestra))
        else:
            candidatos.append(frase_maestra)
    candidatos.sort(key=len, reverse=True)
    for candidato in candidatos:
        if len(candidato) >= SANEO_MIN:
            texto = texto.replace(candidato, "***")
    return texto


def auditar(ruta_audit: str, linea: str) -> None:
    """Registra una línea de auditoría (nunca valores) sin fallar nunca."""
    try:
        os.makedirs(os.path.dirname(ruta_audit) or ".", exist_ok=True)
        with open(ruta_audit, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now(timezone.utc).isoformat(timespec='seconds')} | {linea}\n")
    except Exception:  # noqa: BLE001 — la auditoría no bloquea la operación
        pass

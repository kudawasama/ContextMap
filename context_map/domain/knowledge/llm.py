"""Síntesis generativa **opcional** con LLM para la wiki (hook de ``sintetizar``).

La wiki responde por defecto de forma **extractiva y local** (frases citadas,
deterministas, sin red). Este módulo añade un hook para mejorar esa respuesta con
un LLM, siempre que el usuario lo configure **explícitamente**:

- **Cero dependencias**: el cliente HTTP usa la librería estándar
  (``urllib``) contra cualquier endpoint compatible con la API de OpenAI.
- **Nunca por defecto**: sin ``CTXMAP_LLM_API_KEY`` (o con ``--no-llm``) el hook
  no se activa y la extracción local sigue siendo la respuesta.
- **Nunca rompe**: cualquier fallo (red, clave inválida, respuesta rara)
  devuelve ``""`` y ``sintetizar`` conserva su versión extractiva.
- **Privacidad**: activarlo envía a ese endpoint los fragmentos de tus páginas
  que mejor encajan con la pregunta. Es una decisión consciente del usuario.

Configuración (variables de entorno)::

    CTXMAP_LLM_API_KEY   clave del proveedor (obligatoria para activarlo)
    CTXMAP_LLM_MODEL     modelo a usar (default: gpt-4o-mini)
    CTXMAP_LLM_BASE_URL  endpoint compatible (default: https://api.openai.com/v1)
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Callable
from typing import Any

VARIABLE_CLAVE = "CTXMAP_LLM_API_KEY"
VARIABLE_MODELO = "CTXMAP_LLM_MODEL"
VARIABLE_BASE = "CTXMAP_LLM_BASE_URL"

MODELO_DEFAULT = "gpt-4o-mini"
BASE_DEFAULT = "https://api.openai.com/v1"

Generador = Callable[[str], str]
"""Hook inyectable: recibe el prompt y devuelve la respuesta del modelo."""

_INSTRUCCIONES = (
    "Eres un asistente que responde ÚNICAMENTE con el contexto aportado.\n"
    "Reglas: cita cada fuente con su marca [n]; no inventes datos; si el "
    "contexto no responde a la pregunta, dilo con claridad; responde en el "
    "mismo idioma de la pregunta y de forma breve."
)


def configuracion() -> dict[str, str]:
    """Configuración efectiva del LLM leída del entorno.

    Returns:
        dict[str, str]: Claves ``clave``, ``modelo`` y ``base_url`` (la clave se
        devuelve tal cual; úsala solo para construir la petición).
    """
    return {
        "clave": os.environ.get(VARIABLE_CLAVE, "").strip(),
        "modelo": os.environ.get(VARIABLE_MODELO, "").strip() or MODELO_DEFAULT,
        "base_url": os.environ.get(VARIABLE_BASE, "").strip() or BASE_DEFAULT,
    }


def disponible() -> tuple[bool, str]:
    """Indica si la síntesis con LLM está configurada.

    Returns:
        tuple[bool, str]: ``(True, modelo)`` si hay clave configurada;
        ``(False, motivo)`` con un mensaje accionable si falta.
    """
    cfg = configuracion()
    if not cfg["clave"]:
        return False, (
            f"Sin LLM configurado (la wiki responde de forma extractiva local). "
            f"Define {VARIABLE_CLAVE} para activarlo; opcionalmente "
            f"{VARIABLE_MODELO} y {VARIABLE_BASE}."
        )
    return True, cfg["modelo"]


def construir_prompt(pregunta: str, fragmentos: list[tuple[str, str]]) -> str:
    """Construye el prompt con la pregunta y las fuentes numeradas.

    Args:
        pregunta (str): Pregunta del usuario.
        fragmentos (list[tuple[str, str]]): Pares ``(título, texto)`` de las
            páginas recuperadas, en el orden de las citas ``[n]``.

    Returns:
        str: Prompt listo para el modelo.
    """
    lineas = [_INSTRUCCIONES, "", "Contexto:"]
    for i, (titulo, texto) in enumerate(fragmentos, 1):
        lineas.append(f"[{i}] {titulo}")
        lineas.append(texto.strip())
        lineas.append("")
    lineas.append(f"Pregunta: {pregunta.strip()}")
    lineas.append("")
    lineas.append("Respuesta:")
    return "\n".join(lineas)


def _cliente_http(prompt: str, timeout: int = 60) -> str:
    """Llama a un endpoint compatible con ``/chat/completions`` (stdlib).

    Args:
        prompt (str): Prompt a enviar.
        timeout (int): Segundos máximos de espera (default 60).

    Returns:
        str: Texto generado.

    Raises:
        Exception: Cualquier error de red o de formato (lo captura ``generar``).
    """
    cfg = configuracion()
    cuerpo = json.dumps(
        {
            "model": cfg["modelo"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
    ).encode("utf-8")
    peticion = urllib.request.Request(  # noqa: S310 — endpoint configurable por el usuario
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=cuerpo,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['clave']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:  # noqa: S310
        datos = json.loads(respuesta.read().decode("utf-8"))
    return str(datos["choices"][0]["message"]["content"]).strip()


def generar(
    pregunta: str,
    fragmentos: list[tuple[str, str]],
    *,
    generador: Generador | None = None,
    timeout: int = 60,
) -> str:
    """Genera una respuesta con LLM; devuelve ``""`` ante cualquier problema.

    Args:
        pregunta (str): Pregunta del usuario.
        fragmentos (list[tuple[str, str]]): Pares ``(título, texto)`` de contexto.
        generador (Generador | None): Hook inyectable (tests o agentes). Si es
            None se usa el cliente HTTP estándar.
        timeout (int): Segundos máximos (default 60).

    Returns:
        str: Respuesta del modelo, o ``""`` si no hay contexto o algo falla.
    """
    if not fragmentos:
        return ""
    prompt = construir_prompt(pregunta, fragmentos)
    try:
        if generador is not None:
            return (generador(prompt) or "").strip()
        return (_cliente_http(prompt, timeout=timeout) or "").strip()
    except Exception:  # noqa: BLE001 — el LLM es opcional: nunca rompe la wiki
        return ""


def estado() -> dict[str, Any]:
    """Diagnóstico de la configuración (para ``ctxmap wiki llm``).

    Returns:
        dict[str, Any]: Disponibilidad, motivo, modelo, endpoint y si hay
        clave configurada (nunca expone la clave).
    """
    cfg = configuracion()
    ok, motivo = disponible()
    return {
        "disponible": ok,
        "motivo": "" if ok else motivo,
        "modelo": cfg["modelo"],
        "base_url": cfg["base_url"],
        "clave_configurada": bool(cfg["clave"]),
        "variables": [VARIABLE_CLAVE, VARIABLE_MODELO, VARIABLE_BASE],
    }

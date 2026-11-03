"""Herramientas MCP del baúl de secretos (listar y ejecutar sin exponer).

Extraído de ``mcp_server.py`` (1091 líneas) sin cambiar nombres ni
comportamiento: el servidor sigue registrando las mismas tools en el mismo orden.
"""

from __future__ import annotations

import os

from context_map.infrastructure.mcp_tools.base import (
    _frase_maestra,
    _target_abs,
    _tool,
)


@_tool
def secret_list(scope: str = "proyecto", target: str = ".") -> str:
    """Lista los secretos del baúl cifrado de ContextMap: SOLO NOMBRES y metadatos, NUNCA los valores.

    El baúl se cifra con AES-256-GCM y el agente no recibe las credenciales: usa
    esta tool para saber qué secretos existen y su finalidad.

    Args:
        scope: "proyecto" (default) o "global".
        target: Ruta del proyecto (para el baúl de proyecto).
    """
    try:
        from context_map.core.secrets import cargar, listar

        if scope == "global":
            base = os.environ.get("CTXMAP_SECURE_DIR") or os.path.join(
                os.path.expanduser("~"), ".context-map", "secure"
            )
            ruta = os.path.join(base, "vault.json")
        else:
            ruta = os.path.join(_target_abs(target), ".context-map", "secure", "vault.json")
        entradas = listar(cargar(ruta))
        if not entradas:
            return "secret_list: no hay secretos guardados."
        lineas = [f"secret_list: {len(entradas)} secreto(s):"]
        for e in entradas:
            nota = f" — {e['nota']}" if e.get("nota") else ""
            lineas.append(f"- {e['id']} [{e['scope']}]{nota}")
        return "\n".join(lineas)
    except Exception as err:  # noqa: BLE001 — devolver el error al agente
        return f"ERROR en secret_list: {err}"

@_tool
def secret_exec(ids: str, comando: str, autorizado: bool = False, token: str | None = None, target: str = ".", timeout: int = 60) -> str:
    """Ejecuta un comando con secretos del baul inyectados; la salida se sanea (higiene, no frontera).

    Por defecto esta **deshabilitada** en el MCP: requiere
    ``CTXMAP_MCP_SECRET_EXEC=1`` en el entorno del servidor, o un token de
    aprobacion de un solo uso (``ctxmap secret approve``).

    Args:
        ids: Ids separados por coma a inyectar como CTXMAP_SECRET_<ID>.
        comando: Comando (shell) a ejecutar. El valor se redacta de la salida.
        autorizado: Flag del cliente MCP (debil).
        token: Token de aprobacion de un solo uso (recomendado).
        target: Ruta del proyecto.
        timeout: Segundos maximos (default 60).
    """
    import os as _os
    habilitado = _os.environ.get("CTXMAP_MCP_SECRET_EXEC") == "1"
    if not habilitado and not token:
        return "ERROR en secret_exec: deshabilitado en el MCP por defecto. Usa un token (`ctxmap secret approve`) o define CTXMAP_MCP_SECRET_EXEC=1."
    try:
        import subprocess

        from context_map.application.commands.secrets import _consumir_token, _validar_token
        from context_map.core.secrets import (
            auditar,
            cargar,
            entorno_con_secretos,
            obtener,
            sanear_salida,
        )
        from context_map.core.secrets.proxy import validar_ids_sin_colision
    except Exception as err:  # noqa: BLE001
        return f"ERROR en secret_exec: dependencias no disponibles ({err})."

    if not (autorizado or _os.environ.get("CTXMAP_SECRET_AUTORIZA") == "1" or token):
        return "ERROR en secret_exec: no autorizado. El usuario debe autorizar el uso de sus credenciales."

    raiz = _target_abs(target)
    ruta = _os.path.join(raiz, ".context-map", "secure", "vault.json")
    try:
        doc = cargar(ruta)
    except Exception as err:  # noqa: BLE001
        return f"ERROR en secret_exec: {err}"

    ids_lista = [i.strip() for i in ids.split(",") if i.strip()]
    if not ids_lista:
        return "ERROR en secret_exec: indica ids."
    try:
        validar_ids_sin_colision(ids_lista)
    except ValueError as err:
        return f"ERROR en secret_exec: {err}"
    if token and not _validar_token(target, False, token, ids_lista):
        return "ERROR en secret_exec: token invalido, expirado o no cubre los ids."
    try:
        frase = _frase_maestra()
        if not frase:
            return "ERROR en secret_exec: el servidor no tiene CTXMAP_MASTER_PHRASE (frase del baul)."
        valores = {i: obtener(doc, frase, i) for i in ids_lista}
        if not valores:
            return "ERROR en secret_exec: no se desbloqueo ningun secreto."
    except Exception as err:  # noqa: BLE001
        return f"ERROR en secret_exec: {err}"

    env = entorno_con_secretos(valores)
    try:
        proc = subprocess.run(comando, shell=True, capture_output=True, text=True, env=env, timeout=timeout, errors="replace")
    except subprocess.TimeoutExpired:
        return f"ERROR en secret_exec: tiempo agotado ({timeout}s)."
    except Exception as err:  # noqa: BLE001
        return f"ERROR en secret_exec: {err}"

    if token:
        from context_map.application.commands.secrets import _consumir_token
        _consumir_token(target, False, token)
    auditar(_os.path.join(_os.path.dirname(ruta), "audit.log"), f"exec ids={','.join(ids_lista)} rc={proc.returncode}")
    salida = sanear_salida(proc.stdout or "", valores, frase_maestra=frase, variantes=True)
    if proc.stderr:
        salida += sanear_salida(proc.stderr or "", valores, frase_maestra=frase, variantes=True)
    return salida + "\n[exit " + str(proc.returncode) + "]"

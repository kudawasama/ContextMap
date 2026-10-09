"""Comandos del baúl de secretos cifrado (`ctxmap secret`).

El agente (y cualquier herramienta) puede **listar** qué secretos existen, pero el
**valor** se muestra solo en la terminal del usuario (`get`) o se usará en la
Fase 2 vía proxy (`secret exec` / `secret use`), nunca en el contexto del LLM.
"""

from __future__ import annotations

import getpass
import os
import shutil
import sys

from context_map.core.secrets import (
    SecureVaultError,
    agregar,
    cargar,
    crear_documento,
    eliminar,
    guardar,
    listar,
    obtener,
    requerir_cryptography,
)

_ENV_FRASE = "CTXMAP_MASTER_PHRASE"


def _ruta_vault(target: str, global_: bool) -> str:
    """Resuelve la ruta del baúl según el alcance."""
    if global_:
        base = os.environ.get("CTXMAP_SECURE_DIR") or os.path.join(
            os.path.expanduser("~"), ".context-map", "secure"
        )
        return os.path.join(base, "vault.json")
    return os.path.join(target, ".context-map", "secure", "vault.json")


def _leer_frase(confirmar: bool = False) -> str:
    """Frase maestra: variable de entorno documentada o entrada oculta."""
    env = os.environ.get(_ENV_FRASE)
    if env:
        return env
    frase = getpass.getpass("Frase maestra: ")
    if confirmar and frase != getpass.getpass("Repite la frase maestra: "):
        raise SystemExit("Error: las frases no coinciden.")
    return frase


def _pedir_valor() -> str:
    """Pide el valor sin mostrarlo (oculto) o lo lee de stdin si no hay terminal."""
    stdin = sys.stdin
    if stdin and stdin.isatty():
        return getpass.getpass("Valor del secreto (no se mostrará): ")
    valor = stdin.readline().rstrip("\n")
    sys.stderr.write(
        "[secret] Valor leído de stdin (no se muestra). Evita usar el shell history.\n"
    )
    return valor


def _obtener_global(args) -> bool:
    return bool(getattr(args, "global_", False))


def _reportar(ruta: str, accion: str, extra: str = "") -> None:
    print(f"[secret] {accion} — {ruta}{(' — ' + extra) if extra else ''}")


def _cmd_secret_init(args) -> None:
    requerir_cryptography()
    ruta = _ruta_vault(args.target, _obtener_global(args))
    if os.path.exists(ruta):
        raise SystemExit(
            f"[secret] Ya existe un baúl en {ruta}. Usa --global para el global "
            "(o mueve el archivo si quieres empezar de cero)."
        )
    frase = _leer_frase(confirmar=True)
    guardar(ruta, crear_documento(frase))
    _reportar(
        ruta, "baúl creado",
        "RESPALDA esta frase: sin ella no hay recuperación de los secretos.",
    )


def _cmd_secret_set(args) -> None:
    requerir_cryptography()
    target = getattr(args, "target", ".") or "."
    global_ = _obtener_global(args)
    ruta = _ruta_vault(target, global_)
    doc = cargar(ruta)
    frase = _leer_frase()
    valor = _pedir_valor()
    if not valor:
        raise SystemExit("[secret] Valor vacío: cancelado.")
    agregar(
        doc,
        frase,
        args.ident,
        valor,
        scope="global" if global_ else "proyecto",
        proyecto="" if global_ else os.path.basename(os.path.abspath(target)),
        nota=getattr(args, "nota", "") or "",
    )
    guardar(ruta, doc)
    _reportar(ruta, f"secreto '{args.ident}' guardado (cifrado AES-256-GCM)", "el valor no se muestra ni se registra")


def _cmd_secret_list(args) -> None:
    ruta = _ruta_vault(args.target, _obtener_global(args))
    doc = cargar(ruta)
    entradas = listar(doc)
    if getattr(args, "json", False):
        print(__import__("json").dumps(entradas, ensure_ascii=False, indent=2))
        return
    if not entradas:
        print(f"[secret] No hay secretos guardados en {ruta}.")
        return
    print(f"[secret] {len(entradas)} secreto(s) en {ruta}:")
    for e in entradas:
        nota = f"  ({e['nota']})" if e["nota"] else ""
        print(f"  - {e['id']}{nota}")


def _cmd_secret_get(args) -> None:
    ruta = _ruta_vault(args.target, _obtener_global(args))
    doc = cargar(ruta)
    frase = _leer_frase()
    valor = obtener(doc, frase, args.ident)
    print(valor)
    sys.stderr.write(
        "[secret] El valor se mostró en tu terminal. "
        "No lo compartas ni lo pegues en el chat de la IA.\n"
    )


def _cmd_secret_rm(args) -> None:
    ruta = _ruta_vault(args.target, _obtener_global(args))
    doc = cargar(ruta)
    frase = _leer_frase()
    if eliminar(doc, frase, args.ident):
        guardar(ruta, doc)
        _reportar(ruta, f"secreto '{args.ident}' eliminado")
    else:
        raise SystemExit(f"[secret] No existe '{args.ident}'.")


def _cmd_secret_backup(args) -> None:
    ruta = _ruta_vault(args.target, _obtener_global(args))
    cargar(ruta)  # valida que el baúl exista y sea un documento válido
    destino = args.destino
    os.makedirs(os.path.dirname(destino) or ".", exist_ok=True)
    shutil.copy2(ruta, destino)
    _reportar(destino, "respaldo del baúl creado", "el archivo está cifrado; consérvalo junto a tu frase maestra")


def _cmd_secret_where(args) -> None:
    print(_ruta_vault(args.target, _obtener_global(args)))


def cmd_secret(args) -> None:
    """Dispatcher del baúl de secretos."""
    sub = getattr(args, "secret_cmd", "")
    acciones = {
        "init": _cmd_secret_init,
        "set": _cmd_secret_set,
        "list": _cmd_secret_list,
        "get": _cmd_secret_get,
        "rm": _cmd_secret_rm,
        "backup": _cmd_secret_backup,
        "where": _cmd_secret_where,
    }
    if sub not in acciones:
        raise SystemExit("Uso: ctxmap secret {init|set|list|get|rm|backup|where} [args]")
    try:
        acciones[sub](args)
    except SecureVaultError as err:
        raise SystemExit(f"[secret] {err}") from err

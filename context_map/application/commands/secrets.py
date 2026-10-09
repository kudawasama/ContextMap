"""Comandos del baúl de secretos cifrado (`ctxmap secret`).

El agente (y cualquier herramienta) puede **listar** qué secretos existen, pero el
**valor** se muestra solo en la terminal del usuario (`get`) o se usará en la
Fase 2 vía proxy (`secret exec` / `secret use`), nunca en el contexto del LLM.
"""

from __future__ import annotations

import getpass
import os
import re
import shutil
import subprocess
import sys

from context_map.core.secrets import (
    SecureVaultError,
    agregar,
    auditar,
    cargar,
    crear_documento,
    eliminar,
    entorno_con_secretos,
    guardar,
    listar,
    obtener,
    requerir_cryptography,
    sanear_salida,
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


def _cmd_secret_exec(args) -> None:
    """Fase 2: ejecuta un comando con secretos inyectados y la salida saneada."""
    requerir_cryptography()
    ruta = _ruta_vault(args.target, _obtener_global(args))
    doc = cargar(ruta)
    if not _autorizado(args):
        raise SystemExit(
            "[secret] ACCIÓN DENEGADA: ejecutar con tus credenciales requiere "
            "pasar --autorizado (o definir CTXMAP_SECRET_AUTORIZA=1)."
        )
    ids = [i.strip() for i in (getattr(args, "ids", "") or "").split(",") if i.strip()]
    if not ids:
        raise SystemExit("[secret] Indica --ids id1,id2 con los secretos a inyectar.")
    comando = args.comando
    try:
        valores = _valores_por_ids(doc, _leer_frase(), ids)
    except SecureVaultError as err:
        raise SystemExit(f"[secret] {err}") from err
    env = entorno_con_secretos(valores)
    timeout = min(max(int(getattr(args, "timeout", 60) or 60), 5), 600)
    try:
        proc = subprocess.run(
            comando, shell=True, capture_output=True, text=True,
            env=env, timeout=timeout, errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise SystemExit(f"[secret] Tiempo agotado ({timeout}s): {comando[:80]!r}") from None
    _registrar_uso(ruta, f"exec ids={','.join(ids)} rc={proc.returncode} cmd={comando[:120]!r}")
    sys.stdout.write(sanear_salida(proc.stdout or "", valores))
    if proc.stderr:
        sys.stderr.write(sanear_salida(proc.stderr or "", valores))
    raise SystemExit(proc.returncode)


def _cmd_secret_receta(args) -> None:
    """Fase 2: ejecuta una receta del usuario (guion aprobado) con secretos inyectados."""
    requerir_cryptography()
    ruta = _ruta_vault(args.target, _obtener_global(args))
    doc = cargar(ruta)
    if not _autorizado(args):
        raise SystemExit("[secret] ACCIÓN DENEGADA: pasa --autorizado para usar recetas.")
    nombre = re.sub(r"[^A-Za-z0-9\-_]", "", args.nombre)
    base = os.path.join(os.path.dirname(ruta), "recetas")
    script = next(
        (os.path.join(base, f"{nombre}{ext}") for ext in (".cmd", ".bat", ".sh") if os.path.exists(os.path.join(base, f"{nombre}{ext}"))),
        None,
    )
    if not script:
        raise SystemExit(
            f"[secret] No existe la receta '{args.nombre}' en {base} — "
            "crea recetas/<nombre>.cmd|.sh con el guion aprobado."
        )
    ids = [i.strip() for i in (getattr(args, "ids", "") or "").split(",") if i.strip()]
    try:
        valores = _valores_por_ids(doc, _leer_frase(), ids)
    except SecureVaultError as err:
        raise SystemExit(f"[secret] {err}") from err
    env = entorno_con_secretos(valores)
    env["CTXMAP_SECRET_ARGS"] = " ".join(getattr(args, "rest", []) or [])
    cmdline = ["sh", script, *getattr(args, "rest", [])] if script.endswith(".sh") else ["cmd", "/c", script, *getattr(args, "rest", [])]
    timeout = min(max(int(getattr(args, "timeout", 120) or 120), 5), 1800)
    try:
        proc = subprocess.run(cmdline, capture_output=True, text=True, env=env, timeout=timeout, errors="replace")
    except subprocess.TimeoutExpired:
        raise SystemExit(f"[secret] Tiempo agotado con la receta '{nombre}'.") from None
    _registrar_uso(ruta, f"receta={nombre} ids={','.join(ids) or '-'} rc={proc.returncode}")
    sys.stdout.write(sanear_salida(proc.stdout or "", valores))
    if proc.stderr:
        sys.stderr.write(sanear_salida(proc.stderr or "", valores))
    raise SystemExit(proc.returncode)


def _cmd_secret_audit(args) -> None:
    """Muestra las últimas líneas del registro de auditoría (nunca valores)."""
    ruta = os.path.join(os.path.dirname(_ruta_vault(args.target, _obtener_global(args))), "audit.log")
    if not os.path.exists(ruta):
        print("[secret] Todavía no hay usos registrados.")
        return
    with open(ruta, encoding="utf-8") as f:
        lineas = f.read().splitlines()
    for linea in lineas[-int(getattr(args, "n", 20) or 20):]:
        print(linea)


def _autorizado(args) -> bool:
    """Uso autorizado: flag por llamada o sesión (CTXMAP_SECRET_AUTORIZA=1)."""
    return bool(getattr(args, "autorizado", False)) or os.environ.get("CTXMAP_SECRET_AUTORIZA") == "1"


def _valores_por_ids(doc, frase: str, ids: list[str]) -> dict[str, str]:
    return {ident: obtener(doc, frase, ident) for ident in ids}


def _registrar_uso(ruta_vault: str, linea: str) -> None:
    ruta_audit = os.path.join(os.path.dirname(ruta_vault), "audit.log")
    auditar(ruta_audit, linea)


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
        "exec": _cmd_secret_exec,
        "receta": _cmd_secret_receta,
        "audit": _cmd_secret_audit,
    }
    if sub not in acciones:
        raise SystemExit("Uso: ctxmap secret {init|set|list|get|rm|backup|where|exec|receta|audit} [args]")
    try:
        acciones[sub](args)
    except SecureVaultError as err:
        raise SystemExit(f"[secret] {err}") from err

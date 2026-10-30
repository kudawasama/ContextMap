"""Comandos del baúl de secretos cifrado (`ctxmap secret`).

El agente (y cualquier herramienta) puede **listar** qué secretos existen, pero el
**valor** se muestra solo en la terminal del usuario (`get`) o se usará en la
Fase 2 vía proxy (`secret exec` / `secret use`), nunca en el contexto del LLM.
"""

from __future__ import annotations

import getpass
import json
import os
import re
import secrets as rng_secrets
import shutil
import subprocess
import sys
import time

from context_map.core.secrets import (
    SecureVaultError,
    agregar,
    auditar,
    cargar,
    crear_documento,
    desbloquear,
    eliminar,
    entorno_con_secretos,
    guardar,
    listar,
    obtener,
    requerir_cryptography,
    sanear_salida,
    validar_ids_sin_colision,
)

_ENV_FRASE = "CTXMAP_MASTER_PHRASE"

#: Entrada que protege el material sensible del baúl frente a `git add`.
_ENTRADA_GITIGNORE = ".context-map/secure/"

#: Directorio (dentro de secure/) donde se guardan los tokens de aprobación de un solo uso.
_DIR_APROBACIONES = "approvals"


def _dir_aprobaciones(target: str, global_: bool) -> str:
    return os.path.join(os.path.dirname(_ruta_vault(target, global_)), _DIR_APROBACIONES)


def _generar_token() -> str:
    return rng_secrets.token_urlsafe(32)


def _ruta_token(target: str, global_: bool, token: str) -> str:
    return os.path.join(_dir_aprobaciones(target, global_), f"{token}.json")


def _validar_token(target: str, global_: bool, token: str | None, ids: list[str]) -> bool:
    """Valida un token de aprobación de un solo uso sin consumirlo."""
    if not token:
        return False
    ruta = _ruta_token(target, global_, token)
    if not os.path.exists(ruta):
        return False
    try:
        with open(ruta, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return False
    if data.get("used"):
        return False
    if data.get("expires", 0) < time.time():
        return False
    token_ids = set(data.get("ids", []))
    return token_ids.issuperset(ids)


def _consumir_token(target: str, global_: bool, token: str | None) -> None:
    """Marca el token como usado y lo elimina (un solo uso)."""
    if not token:
        return
    ruta = _ruta_token(target, global_, token)
    try:
        if os.path.exists(ruta):
            os.remove(ruta)
    except OSError:
        pass


def _raiz_git(project_dir: str) -> str | None:
    """Busca la raíz del repositorio Git que contiene el proyecto.

    Acepta tanto un directorio ``.git`` (repo normal) como un archivo ``.git``
    (worktrees y submódulos), donde Git guarda un puntero al repositorio real.
    """
    actual = os.path.abspath(project_dir or ".")
    while True:
        if os.path.exists(os.path.join(actual, ".git")):
            return actual
        padre = os.path.dirname(actual)
        if padre == actual:
            return None
        actual = padre


def _asegurar_gitignore(project_dir: str) -> bool:
    """Añade `.context-map/secure/` al `.gitignore` del repositorio (idempotente).

    El hook pre-commit hace ``git add .context-map``; sin esta entrada, el baúl
    cifrado y el ``audit.log`` podrían acabar en el remoto. Solo actúa si el
    proyecto está dentro de un repositorio Git.

    Args:
        project_dir: Directorio del proyecto donde vive el baúl.

    Returns:
        bool: ``True`` si añadió la entrada; ``False`` si ya estaba o no hay Git.
    """
    raiz = _raiz_git(project_dir)
    if not raiz:
        return False
    ruta = os.path.join(raiz, ".gitignore")
    try:
        contenido = ""
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8", errors="ignore") as f:
                contenido = f.read()
        if any(
            linea.strip().rstrip("/") == ".context-map/secure"
            for linea in contenido.splitlines()
        ):
            return False
        with open(ruta, "a", encoding="utf-8", newline="\n") as f:
            if contenido and not contenido.endswith("\n"):
                f.write("\n")
            f.write(
                "\n# ContextMap: material sensible (no se commitea automáticamente)\n"
                f"{_ENTRADA_GITIGNORE}\n"
            )
        return True
    except OSError:
        return False


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
    if not _obtener_global(args):
        _asegurar_gitignore(getattr(args, "target", ".") or ".")
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
    if not global_:
        _asegurar_gitignore(target)
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
    try:
        validar_ids_sin_colision(ids)
    except ValueError as err:
        raise SystemExit(f"[secret] {err}") from err
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
    _consumir_token(getattr(args, "target", ".") or ".", _obtener_global(args), getattr(args, "token", None))
    _registrar_uso(ruta, f"exec ids={','.join(ids)} rc={proc.returncode}")
    sys.stdout.write(sanear_salida(proc.stdout or "", valores, frase_maestra=os.environ.get(_ENV_FRASE)))
    if proc.stderr:
        sys.stderr.write(sanear_salida(proc.stderr or "", valores, frase_maestra=os.environ.get(_ENV_FRASE)))
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
        validar_ids_sin_colision(ids)
    except ValueError as err:
        raise SystemExit(f"[secret] {err}") from err
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
    _consumir_token(getattr(args, "target", ".") or ".", _obtener_global(args), getattr(args, "token", None))
    _registrar_uso(ruta, f"receta={nombre} ids={','.join(ids) or '-'} rc={proc.returncode}")
    sys.stdout.write(sanear_salida(proc.stdout or "", valores, frase_maestra=os.environ.get(_ENV_FRASE)))
    if proc.stderr:
        sys.stderr.write(sanear_salida(proc.stderr or "", valores, frase_maestra=os.environ.get(_ENV_FRASE)))
    raise SystemExit(proc.returncode)


def _cmd_secret_restore(args) -> None:
    """Fase 3: restaura el baúl desde un respaldo cifrado (otro PC, pendrive…)."""
    ruta_destino = _ruta_vault(args.target, _obtener_global(args))
    if os.path.exists(ruta_destino) and not getattr(args, "overwrite", False):
        raise SystemExit(
            f"[secret] El baúl destino ya existe ({ruta_destino}). Usa --overwrite para reemplazarlo."
        )
    origen = getattr(args, "origen", "")
    if not origen or not os.path.exists(origen):
        raise SystemExit(f"[secret] No existe el respaldo {origen!r}.")
    doc = cargar(origen)  # valida que sea un baúl de ContextMap
    if getattr(args, "verificar", False):
        desbloquear(doc, _leer_frase())
    os.makedirs(os.path.dirname(ruta_destino) or ".", exist_ok=True)
    shutil.copy2(origen, ruta_destino)
    if not _obtener_global(args):
        _asegurar_gitignore(getattr(args, "target", ".") or ".")
    _reportar(
        ruta_destino,
        "baúl restaurado desde " + origen,
        "recuerda la frase maestra: sin ella no descifrarás.",
    )


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
    """Uso autorizado: flag por llamada, sesión, o token de un solo uso válido."""
    if bool(getattr(args, "autorizado", False)) or os.environ.get("CTXMAP_SECRET_AUTORIZA") == "1":
        return True
    token = getattr(args, "token", None)
    if token:
        target = getattr(args, "target", ".") or "."
        global_ = _obtener_global(args)
        ids = [i.strip() for i in (getattr(args, "ids", "") or "").split(",") if i.strip()]
        return _validar_token(target, global_, token, ids)
    return False


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
        "restore": _cmd_secret_restore,
        "approve": _cmd_secret_approve,
        "rekey": _cmd_secret_rekey,
    }
    if sub not in acciones:
        raise SystemExit("Uso: ctxmap secret {init|set|list|get|rm|backup|where|exec|receta|audit|restore|approve|rekey} [args]")
    try:
        acciones[sub](args)
    except SecureVaultError as err:
        raise SystemExit(f"[secret] {err}") from err

def _cmd_secret_approve(args) -> None:
    target = getattr(args, "target", ".") or "."
    global_ = _obtener_global(args)
    ids = [i.strip() for i in (getattr(args, "ids", "") or "").split(",") if i.strip()]
    if not ids:
        raise SystemExit("[secret] Indica --ids id1,id2 con los secretos a autorizar.")
    try:
        validar_ids_sin_colision(ids)
    except ValueError as err:
        raise SystemExit(f"[secret] {err}") from err
    ttl = min(max(int(getattr(args, "ttl", 300) or 300), 30), 3600)
    token = _generar_token()
    os.makedirs(_dir_aprobaciones(target, global_), exist_ok=True)
    ruta_token = _ruta_token(target, global_, token)
    with open(ruta_token, "w", encoding="utf-8") as f:
        json.dump({"ids": ids, "expires": time.time() + ttl, "used": False}, f, ensure_ascii=False)
    print(f"[secret] Token de aprobación (un solo uso, {ttl}s): {token}")
    print("[secret] Úsalo con: ctxmap secret exec ... --token " + token)


def _cmd_secret_rekey(args) -> None:
    requerir_cryptography()
    target = getattr(args, "target", ".") or "."
    global_ = _obtener_global(args)
    ruta = _ruta_vault(target, global_)
    doc = cargar(ruta)
    frase_vieja = _leer_frase()
    desbloquear(doc, frase_vieja)
    valores_por_entrada = []
    for e in doc.get("entries", []):
        ident = e["id"]
        valor = obtener(doc, frase_vieja, ident)
        valores_por_entrada.append((ident, valor, e.get("scope", "proyecto"), e.get("proyecto", ""), e.get("nota", "")))
    frase_nueva = getpass.getpass("Nueva frase maestra: ")
    if frase_nueva != getpass.getpass("Repite la nueva frase maestra: "):
        raise SystemExit("[secret] Las frases nuevas no coinciden.")
    if len(frase_nueva) < 8:
        raise SystemExit("[secret] La nueva frase debe tener al menos 8 caracteres.")
    nuevo_doc = crear_documento(frase_nueva)
    for ident, valor, scope, proyecto, nota in valores_por_entrada:
        agregar(nuevo_doc, frase_nueva, ident, valor, scope=scope, proyecto=proyecto, nota=nota)
    guardar(ruta, nuevo_doc)
    _reportar(ruta, "baúl re-cifrado con la nueva frase maestra", "respalda la nueva frase")

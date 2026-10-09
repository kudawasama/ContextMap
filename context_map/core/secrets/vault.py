"""Baúl de secretos cifrado (Fase 1).

Diseño de seguridad:

- Cada valor se cifra con **AES-256-GCM** (autenticado) con una clave maestro
  derivada de la **frase maestra** del usuario (PBKDF2-HMAC-SHA256, stdlib).
- En disco solo existe: metadatos en claro (id, scope, proyecto, nota, fechas)
  y el **cifrado** de cada valor. La frase maestra **nunca** se almacena.
- Cada cifrado usa un *nonce* aleatorio de 12 bytes y un *AAD* que ata el
  cifrado a su identidad ``scope|proyecto|id`` (intercambiar entradas falla).
- El archivo puede commitearse o copiarse a un pendrive: sin la frase no se
  descifra nada.
- Requiere el extra opcional ``context-map-ai[secure]`` (paquete ``cryptography``);
  sin él, las operaciones devuelven un error accionable.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets as rng
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

VERSION = 1
ENC_HEADER = "ctxmap-secure"
ALGO = "aes-256-gcm"
KDF = "pbkdf2-hmac-sha256"
KDF_ITER = 600_000
FRASE_MIN = 8

_ENV_FRASE = "CTXMAP_MASTER_PHRASE"
"""Variable de entorno alternativa a la frase interactiva (documentada como riesgo)."""

try:  # pragma: no cover — depende del extra opcional
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    _CRYPTO_OK = True
except Exception as err:  # noqa: BLE001
    _CRYPTO_OK = False
    _CRYPTO_ERROR = err


def cryptography_disponible() -> bool:
    """True si el extra ``[secure]`` (cryptography) está instalado."""
    return _CRYPTO_OK


def requerir_cryptography() -> None:
    """Lanza un error accionable si falta el extra ``[secure]``."""
    if not _CRYPTO_OK:
        raise SecureVaultError(
            "El baúl de secretos necesita el extra opcional `[secure]`. "
            f"Instala: pip install \"context-map-ai[secure]\" (o uv tool install ...). "
            f"Detalle: {_CRYPTO_ERROR}"
        )


class SecureVaultError(Exception):
    """Error de operación sobre el baúl de secretos."""


class FraseIncorrecta(SecureVaultError):
    """La frase maestra no desbloquea el baúl (o el baúl está incompleto)."""


# ---------------------------------------------------------------------------
# Codificación auxiliar
# ---------------------------------------------------------------------------


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _unb64(texto: str) -> bytes:
    try:
        return base64.b64decode(texto)
    except Exception as err:  # noqa: BLE001
        raise SecureVaultError("Baúl corrupto: cifrado base64 inválido.") from err


def _derivar_clave(frase: str, salt: bytes, iteraciones: int = KDF_ITER) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", frase.encode(), salt, iteraciones, dklen=32)


def _aad(scope: str, proyecto: str, ident: str) -> bytes:
    return f"ctxmap-secure|{scope}|{proyecto or ''}|{ident}".encode()


# ---------------------------------------------------------------------------
# Creación, carga y guardado del documento
# ---------------------------------------------------------------------------


def crear_documento(frase: str, iteraciones: int = KDF_ITER) -> dict[str, Any]:
    """Crea un documento de baúl nuevo y lo desbloquea.

    Args:
        frase: Frase maestra (mínimo `FRASE_MIN` caracteres).
        iteraciones: Iteraciones PBKDF2 (test puede reducirlas).

    Returns:
        dict: Documento del baúl serializable.
    """
    requerir_cryptography()
    if len(frase) < FRASE_MIN:
        raise SecureVaultError(
            f"La frase maestra debe tener al menos {FRASE_MIN} caracteres "
            "(respalda la frase: sin ella no hay recuperación)."
        )
    salt = os.urandom(16)
    clave = _derivar_clave(frase, salt, iteraciones)
    aes = AESGCM(clave)
    check_nonce = os.urandom(12)
    check = aes.encrypt(check_nonce, b"ctxmap-check", _aad("check", "", "check"))
    return {
        "enc": ENC_HEADER,
        "version": VERSION,
        "algo": ALGO,
        "kdf": KDF,
        "iter": iteraciones,
        "salt": _b64(salt),
        "check_nonce": _b64(check_nonce),
        "check": _b64(check),
        "entries": [],
    }


def desbloquear(doc: dict[str, Any], frase: str) -> bytes:
    """Valida la frase maestra y devuelve la clave del documento.

    Raises:
        FraseIncorrecta: si la frase no coincide o el documento está corrupto.
    """
    requerir_cryptography()
    if doc.get("enc") != ENC_HEADER:
        raise SecureVaultError("El archivo no es un baúl de ContextMap.")
    try:
        salt = _unb64(doc["salt"])
        clave = _derivar_clave(frase, salt, int(doc.get("iter", KDF_ITER)))
        aes = AESGCM(clave)
        aes.decrypt(_unb64(doc["check_nonce"]), _unb64(doc["check"]), _aad("check", "", "check"))
    except Exception as err:  # noqa: BLE001
        raise FraseIncorrecta("Frase maestra incorrecta (o baúl dañado).") from err
    return clave


def guardar(ruta: str, doc: dict[str, Any]) -> None:
    """Escribe el documento de forma atómica (temp + rename)."""
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    tmp = ruta + f".tmp{rng.randbelow(10 ** 8)}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ruta)


def cargar(ruta: str) -> dict[str, Any]:
    """Carga el documento del baúl si existe y es válido."""
    if not os.path.exists(ruta):
        raise SecureVaultError(f"No existe un baúl en {ruta}. Ejecuta `ctxmap secret init`.")
    try:
        with open(ruta, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as err:  # noqa: BLE001
        raise SecureVaultError(f"No se pudo leer el baúl {ruta}: {err}") from err
    if not isinstance(doc, dict) or doc.get("enc") != ENC_HEADER:
        raise SecureVaultError(f"El archivo {ruta} no es un baúl de ContextMap válido.")
    return doc


# ---------------------------------------------------------------------------
# Operaciones sobre entradas
# ---------------------------------------------------------------------------


def agregar(
    doc: dict[str, Any],
    frase: str,
    ident: str,
    valor: str,
    *,
    scope: str = "proyecto",
    proyecto: str = "",
    nota: str = "",
) -> None:
    """Cifra y añade (o reemplaza) una entrada en el documento (en memoria)."""
    clave = desbloquear(doc, frase)
    ident = ident.strip()
    if not ident:
        raise SecureVaultError("El id del secreto no puede estar vacío.")
    nonce = os.urandom(12)
    cipher = AESGCM(clave).encrypt(nonce, valor.encode(), _aad(scope, proyecto, ident))
    doc["entries"] = [e for e in doc["entries"] if e.get("id") != ident]  # upsert
    doc["entries"].append(
        {
            "id": ident,
            "scope": scope,
            "proyecto": proyecto,
            "nota": nota,
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "nonce": _b64(nonce),
            "cipher": _b64(cipher),
        }
    )


def obtener(doc: dict[str, Any], frase: str, ident: str) -> str:
    """Descifra y devuelve el valor de una entrada (proyecto/global por id)."""
    clave = desbloquear(doc, frase)
    for e in doc["entries"]:
        if e.get("id") == ident:
            try:
                plano = AESGCM(clave).decrypt(
                    _unb64(e["nonce"]),
                    _unb64(e["cipher"]),
                    _aad(e.get("scope", ""), e.get("proyecto", ""), ident),
                )
            except Exception as err:  # noqa: BLE001
                raise SecureVaultError(
                    f"La entrada '{ident}' no se pudo descifrar (¿phishing de baúl?)."
                ) from err
            return plano.decode("utf-8")
    raise SecureVaultError(f"No existe el secreto '{ident}' en este baúl.")


def listar(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Metadatos de las entradas (nunca los valores)."""
    return [
        {
            "id": e["id"],
            "scope": e.get("scope", ""),
            "proyecto": e.get("proyecto", ""),
            "nota": e.get("nota", ""),
            "created": e.get("created", ""),
        }
        for e in doc.get("entries", [])
    ]


def eliminar(doc: dict[str, Any], frase: str, ident: str) -> bool:
    """Elimina una entrada. Devuelve False si no existía."""
    desbloquear(doc, frase)  # valida la frase antes de mutar
    antes = len(doc["entries"])
    doc["entries"] = [e for e in doc["entries"] if e.get("id") != ident]
    return len(doc["entries"]) < antes

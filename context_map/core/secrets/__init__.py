"""Baúl de secretos cifrado por proyecto y global.

Los valores se cifran con AES-256-GCM; en disco solo hay metadatos en claro y
cifrados. La frase maestra es la única llave (nunca se almacena): respáldala.
"""

from __future__ import annotations

from context_map.core.secrets.vault import (
    ALGO,
    FRASE_MIN,
    KDF_ITER,
    VERSION,
    FraseIncorrecta,
    SecureVaultError,
    agregar,
    cargar,
    crear_documento,
    cryptography_disponible,
    desbloquear,
    eliminar,
    guardar,
    listar,
    obtener,
    requerir_cryptography,
)

__all__ = [
    "ALGO",
    "FRASE_MIN",
    "KDF_ITER",
    "VERSION",
    "FraseIncorrecta",
    "SecureVaultError",
    "agregar",
    "cargar",
    "crear_documento",
    "cryptography_disponible",
    "desbloquear",
    "eliminar",
    "guardar",
    "listar",
    "obtener",
    "requerir_cryptography",
]

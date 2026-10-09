"""Tests del baúl de secretos cifrado (Fase 1): cifrado, no-exposición y AAD."""

from __future__ import annotations

import json
import os

import pytest

from context_map.core.secrets import (
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
)

FRASE = "Mi-Frase-Maestra-2026"
ITER = 10_000  # iteraciones PBKDF2 reducidas para tests rápidos


def test_crear_y_desbloquear_valida_frase(tmp_path) -> None:
    """La frase correcta desbloquea; la incorrecta lanza FraseIncorrecta."""
    doc = crear_documento(FRASE, iteraciones=ITER)
    assert desbloquear(doc, FRASE)
    with pytest.raises(FraseIncorrecta):
        desbloquear(doc, "frase-incorrecta")
    # frases demasiado cortas se rechazan al crear
    with pytest.raises(SecureVaultError):
        crear_documento("corta", iteraciones=ITER)


def test_roundtrip_cifrado_sin_exponer_valor(tmp_path) -> None:
    """El valor viaja cifrado: no aparece en claro ni en listar()."""
    ruta = str(tmp_path / "vault.json")
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "token", "s3cr3to-super-secreto", scope="proyecto", proyecto="P", nota="correo")
    guardar(ruta, doc)

    with open(ruta, encoding="utf-8") as f:
        contenido = f.read()
    assert "s3cr3to-super-secreto" not in contenido

    recargado = cargar(ruta)
    assert obtener(recargado, FRASE, "token") == "s3cr3to-super-secreto"
    for meta in listar(recargado):
        assert "s3cr3to" not in json.dumps(meta)


def test_upsert_reemplaza_y_eliminar_responde(tmp_path) -> None:
    """set del mismo id reemplaza; rm devuelve si existía."""
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "a", "v1", scope="proyecto", proyecto="")
    agregar(doc, FRASE, "a", "v2", scope="proyecto", proyecto="")
    assert len(doc["entries"]) == 1
    assert obtener(doc, FRASE, "a") == "v2"
    assert eliminar(doc, FRASE, "a") is True
    assert eliminar(doc, FRASE, "a") is False
    with pytest.raises(SecureVaultError):
        obtener(doc, FRASE, "a")


def test_aad_ata_el_cifrado_a_su_identidad(tmp_path) -> None:
    """Mover el cifrado a otro id hace que la autenticación falle (anti-intercambio)."""
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "real", "valor", scope="proyecto", proyecto="P")
    entrada = doc["entries"][0]
    doc["entries"][0] = {**entrada, "id": "falso"}
    with pytest.raises(SecureVaultError):
        obtener(doc, FRASE, "falso")


def test_guardar_y_cargar_persisten(tmp_path) -> None:
    """El documento guardado se relee y mantiene metadatos (nunca valores)."""
    ruta = str(tmp_path / "vault.json")
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "cl_email", "valor1", scope="proyecto", proyecto="App", nota="entrada")
    guardar(ruta, doc)
    recargado = cargar(ruta)
    metas = listar(recargado)
    assert len(metas) == 1
    assert metas[0]["id"] == "cl_email"
    assert metas[0]["nota"] == "entrada"


def test_cryptography_disponible_en_ci() -> None:
    """En CI instalamos el extra secure; el módulo debe responder disponible."""
    assert cryptography_disponible() is True


def test_mcp_secret_list_solo_expone_nombres(tmp_path) -> None:
    """La tool MCP lista metadatos sin frase y nunca el valor."""
    from context_map.infrastructure.mcp_server import secret_list

    secure = os.path.join(str(tmp_path), ".context-map", "secure")
    os.makedirs(secure, exist_ok=True)
    ruta = os.path.join(secure, "vault.json")
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "cl_banca", "valor-super-secreto", scope="proyecto", proyecto="P", nota="banco")
    guardar(ruta, doc)

    salida = secret_list(target=str(tmp_path))
    assert "cl_banca" in salida
    assert "valor-super-secreto" not in salida

    # Target inexistente: el tool devuelve un string de error (nunca lanza).
    assert "ERROR" in secret_list(target=str(tmp_path / "inexistente"))

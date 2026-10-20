"""Tests de la Fase 3: restaurar el baúl desde un respaldo cifrado (otro PC/pendrive)."""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from context_map.application.commands.secrets import _cmd_secret_restore
from context_map.core.secrets import (
    FraseIncorrecta,
    SecureVaultError,
    agregar,
    cargar,
    crear_documento,
    guardar,
    obtener,
)

FRASE = "Frase-Restore-2026"
ITER = 10_000


def _crear_baul(ruta: str) -> None:
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    doc = crear_documento(FRASE, iteraciones=ITER)
    agregar(doc, FRASE, "tk", "valor-banca", scope="proyecto", proyecto="P")
    guardar(ruta, doc)


def _args(origen: str, destino: str, overwrite: bool = False, verificar: bool = False):
    return SimpleNamespace(
        origen=origen, target=destino, global_=False,
        overwrite=overwrite, verificar=verificar,
    )


def test_restore_copia_y_desbloquea(tmp_path) -> None:
    """Restaurar instala el baúl y el valor sigue descifrándose con la frase."""
    origen = str(tmp_path / "backup" / "vault.json")
    _crear_baul(origen)
    proyecto = str(tmp_path / "proj")

    _cmd_secret_restore(_args(origen, proyecto))

    destino = os.path.join(proyecto, ".context-map", "secure", "vault.json")
    assert os.path.exists(destino)
    doc = cargar(destino)
    assert obtener(doc, FRASE, "tk") == "valor-banca"


def test_restore_rechaza_sobrescribir_sin_overwrite(tmp_path) -> None:
    """Si el destino ya tiene un baúl, sin --overwrite se niega."""
    origen = str(tmp_path / "backup.json")
    _crear_baul(origen)
    proyecto = str(tmp_path / "proj")
    _cmd_secret_restore(_args(origen, proyecto))

    with pytest.raises(SystemExit):
        _cmd_secret_restore(_args(origen, proyecto))

    _cmd_secret_restore(_args(origen, proyecto, overwrite=True))  # con bandera sí


def test_restore_valida_que_sea_un_baul(tmp_path) -> None:
    """Un archivo que no es un baúl de ContextMap se rechaza."""
    no_baul = str(tmp_path / "no.txt")
    with open(no_baul, "w", encoding="utf-8") as f:
        f.write("esto no es un baúl")
    with pytest.raises(SecureVaultError):
        _cmd_secret_restore(_args(no_baul, str(tmp_path / "p")))


def test_restore_verificar_con_frase_incorrecta_falla_y_no_instala(tmp_path, monkeypatch) -> None:
    """--verificar con frase equivocada aborta antes de instalar."""
    origen = str(tmp_path / "backup.json")
    _crear_baul(origen)
    proyecto = str(tmp_path / "p")

    monkeypatch.setenv("CTXMAP_MASTER_PHRASE", "otra-frase")
    with pytest.raises(FraseIncorrecta):
        _cmd_secret_restore(_args(origen, proyecto, verificar=True))

    assert not os.path.exists(os.path.join(proyecto, ".context-map", "secure", "vault.json"))

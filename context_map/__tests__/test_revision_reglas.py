"""Tests de la revisión idempotente de reglas agénticas generadas por ContextMap."""

from __future__ import annotations

import hashlib
import os

from context_map.domain.ecosystem.adaptador import (
    _guardar_reglas_manifest,
    revisar_reglas_agente,
)

#: Ruta que se genera al detectar Cursor (basta crear la carpeta `.cursor/`).
_REGLA = ".cursorrules"


def _sha(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _leer(p: str) -> str:
    with open(p, encoding="utf-8") as f:
        return f.read()


def test_revision_crea_y_luego_omite(tmp_path) -> None:
    """La primera pasada crea; la segunda, al estar al día, no reescribe nada."""
    os.makedirs(os.path.join(str(tmp_path), ".cursor"), exist_ok=True)

    r1 = revisar_reglas_agente("Demo", str(tmp_path))
    assert _REGLA in r1["creados"]
    ruta = os.path.join(str(tmp_path), _REGLA)
    contenido = _leer(ruta)

    r2 = revisar_reglas_agente("Demo", str(tmp_path))
    assert _REGLA not in r2["creados"] + r2["actualizados"]
    assert _leer(ruta) == contenido  # idempotente: sin cambios


def test_revision_actualiza_solo_si_es_nuestro_y_cambio(tmp_path) -> None:
    """Si ContextMap escribió el archivo y su plantilla cambió, lo actualiza."""
    os.makedirs(os.path.join(str(tmp_path), ".cursor"), exist_ok=True)
    revisar_reglas_agente("Demo", str(tmp_path))
    ruta = os.path.join(str(tmp_path), _REGLA)
    esperado = _leer(ruta)

    # Simular una versión antigua escrita por ContextMap (manifiesto con ese hash).
    antiguo = "reglas viejas de ContextMap\n"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(antiguo)
    _guardar_reglas_manifest(str(tmp_path), {_REGLA: _sha(antiguo)})

    r = revisar_reglas_agente("Demo", str(tmp_path))
    assert _REGLA in r["actualizados"]
    assert _leer(ruta) == esperado


def test_revision_respeta_edicion_del_usuario(tmp_path) -> None:
    """Si el usuario edita el archivo (el hash no es el del manifiesto), se respeta."""
    os.makedirs(os.path.join(str(tmp_path), ".cursor"), exist_ok=True)
    revisar_reglas_agente("Demo", str(tmp_path))
    ruta = os.path.join(str(tmp_path), _REGLA)

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("editado por el usuario\n")

    r = revisar_reglas_agente("Demo", str(tmp_path))
    assert _REGLA in r["respetados"]
    assert _leer(ruta) == "editado por el usuario\n"

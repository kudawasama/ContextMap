"""Contrato del comando ``ctxmap reglas``.

El catálogo no sirve de nada si no se puede consultar: estas pruebas fijan que
se liste, que filtre, que avise cuando no hay catálogo y que ``--verificar``
cruce cada regla con el doctor (y falle si alguna está incumplida).
"""

from __future__ import annotations

import json
import os

import pytest

from context_map.application.commands.reglas_cmd import _filtrar, _orden, cmd_reglas
from context_map.domain.health import doctor

CATALOGO = """\
version: 1.0
proyecto: "Demo"

reglas:
  - id: REG-VLT-001
    resumen: "un solo padre por nota"
    nombre: "Cada nota cuelga de exactamente un padre"
    categoria: REG-VLT
    categoria_nombre: "Vault y topología"
    prioridad: critica
    estado: implementada
    norma: "AGENTS.md"
    seccion: "4. Topologia"
    verificacion: "doctor:topologia"

  - id: REG-DOC-001
    resumen: "commits convencionales"
    nombre: "Commits con Conventional Commits"
    categoria: REG-DOC
    categoria_nombre: "Documentación"
    prioridad: media
    estado: implementada
    norma: "AGENTS.md"
    seccion: "6. Commits"
    verificacion: "manual"
"""


def _proyecto(tmp_path, con_catalogo: bool = True):
    raiz = tmp_path / "demo"
    (raiz / "references" / "reglas").mkdir(parents=True)
    if con_catalogo:
        (raiz / "references" / "reglas" / "reglas_registro.yaml").write_text(
            CATALOGO, encoding="utf-8"
        )
    (raiz / "AGENTS.md").write_text("# Normas\n", encoding="utf-8")
    return raiz


def _args(raiz, **extra):
    base = {
        "target_dir": str(raiz),
        "categoria": "",
        "prioridad": "",
        "verificar": False,
        "json": False,
    }
    base.update(extra)
    return base


def test_lista_el_catalogo_con_su_verificacion(tmp_path, capsys):
    cmd_reglas(_args(_proyecto(tmp_path)))
    salida = capsys.readouterr().out

    assert "2 regla(s)" in salida
    assert "REG-VLT-001" in salida
    assert "doctor:topologia" in salida
    assert "1 las comprueba la máquina" in salida


def test_sin_catalogo_avisa_y_no_inventa_reglas(tmp_path, capsys):
    cmd_reglas(_args(_proyecto(tmp_path, con_catalogo=False)))
    capturado = capsys.readouterr()
    assert "No hay catálogo de reglas" in capturado.err
    assert "REG-" not in capturado.out


def test_filtra_por_categoria_con_o_sin_prefijo(tmp_path, capsys):
    raiz = _proyecto(tmp_path)
    for categoria in ("VLT", "REG-VLT", "reg-vlt"):
        cmd_reglas(_args(raiz, categoria=categoria))
        salida = capsys.readouterr().out
        assert "REG-VLT-001" in salida
        assert "REG-DOC-001" not in salida


def test_filtra_por_prioridad(tmp_path, capsys):
    raiz = _proyecto(tmp_path)
    cmd_reglas(_args(raiz, prioridad="media"))
    salida = capsys.readouterr().out
    assert "REG-DOC-001" in salida
    assert "REG-VLT-001" not in salida


def test_json_estructurado(tmp_path, capsys):
    cmd_reglas(_args(_proyecto(tmp_path), json=True))
    datos = json.loads(capsys.readouterr().out)
    assert datos["total"] == 2
    assert datos["verificadas_por_la_maquina"] == 1
    assert {r["id"] for r in datos["reglas"]} == {"REG-VLT-001", "REG-DOC-001"}


def test_verificar_en_verde_sale_con_cero(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "context_map.application.commands.reglas_cmd.diagnosticar_salud",
        lambda target: doctor.DoctorReport(
            checks=[doctor.DoctorCheck(name="topologia", status="OK", message="bien")]
        ),
    )
    cmd_reglas(_args(_proyecto(tmp_path), verificar=True))
    salida = capsys.readouterr().out
    assert "Todas las reglas que la máquina comprueba están en verde" in salida


def test_verificar_incumplida_sale_con_uno(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(
        "context_map.application.commands.reglas_cmd.diagnosticar_salud",
        lambda target: doctor.DoctorReport(
            checks=[
                doctor.DoctorCheck(
                    name="topologia", status="WARN", message="3 violaciones"
                )
            ]
        ),
    )
    with pytest.raises(SystemExit) as salida:
        cmd_reglas(_args(_proyecto(tmp_path), verificar=True))
    assert salida.value.code == 1
    assert "1 regla(s) incumplida(s)" in capsys.readouterr().out


def test_orden_prioriza_vault_sobre_documentacion():
    vault = {"categoria": "REG-VLT", "id": "REG-VLT-002"}
    doc = {"categoria": "REG-DOC", "id": "REG-DOC-001"}
    assert sorted([doc, vault], key=_orden) == [vault, doc]


def test_filtro_vacio_no_descarta_nada():
    reglas = [{"categoria": "REG-VLT", "prioridad": "critica"}]
    assert _filtrar(reglas, "", "") == reglas


def test_catalogo_real_del_repo_tiene_reglas_verificables():
    """El catálogo de este repo (no una fixture) debe listarse sin romper."""
    raiz = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    from context_map.domain.reglas.reglas import reglas_del_proyecto

    reglas = reglas_del_proyecto(raiz)
    assert len(reglas) >= 10
    assert all("verificacion" in r for r in reglas)


# ── segundo esquema: catálogos escritos antes de esta convención ──────────

CATALOGO_ANTIGUO = """\
reglas:
  - id: REG-ING-001
    nombre: "DB activa es SIEMPRE dte_reportes.db (nunca la legacy)"
    categoria: REG-ING
    celula_nombre: "Ingesta DTE"
    prioridad: critica
    estado: implementada
    norma: "REG-ING-001_db_activa.md"
    test: "test_reg_ing_001.py"
"""


def _proyecto_antiguo(tmp_path):
    raiz = tmp_path / "viejo"
    destino = raiz / "4_infraestructura_core" / "references" / "reglas"
    destino.mkdir(parents=True)
    (destino / "reglas_registro.yaml").write_text(CATALOGO_ANTIGUO, encoding="utf-8")
    return raiz


def test_esquema_antiguo_no_imprime_none_ni_pierde_el_test(tmp_path, capsys):
    """Un catálogo sin `resumen`/`verificacion` debe seguir siendo legible."""
    cmd_reglas(_args(_proyecto_antiguo(tmp_path), verificar=True))
    salida = capsys.readouterr().out

    assert "None" not in salida
    assert "REG-ING-001" in salida
    assert "test:test_reg_ing_001.py" in salida
    assert "1 las comprueba la máquina" in salida


def test_esquema_antiguo_reconoce_la_seccion_ausente(tmp_path, capsys):
    cmd_reglas(_args(_proyecto_antiguo(tmp_path)))
    salida = capsys.readouterr().out
    assert "→ None" not in salida
    assert "norma: REG-ING-001_db_activa.md" in salida


def test_filtro_por_categoria_del_esquema_antiguo(tmp_path, capsys):
    raiz = _proyecto_antiguo(tmp_path)
    cmd_reglas(_args(raiz, categoria="ING"))
    assert "REG-ING-001" in capsys.readouterr().out

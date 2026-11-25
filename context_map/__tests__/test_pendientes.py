"""Tests del cruce de pendientes (``REG-INI-004``).

Se construyen vaults reales en ``tmp_path`` con los formatos que aparecen en los
proyectos de verdad: casillas, tablas con columna de estado y prosa. Un cruce
que informa «nada pendiente» donde hay trabajo es peor que no cruzar, así que
cada formato tiene su caso.
"""

from __future__ import annotations

import json
import os

from context_map.domain.reporting import pendientes as pn


def _vault(tmp_path, nombre: str = "Demo") -> str:
    """Crea la estructura mínima del vault y devuelve su ruta."""
    raiz = os.path.join(str(tmp_path), ".context-map", f"vault-{nombre}")
    os.makedirs(os.path.join(raiz, "7.0-MANUAL", "Diario"), exist_ok=True)
    os.makedirs(os.path.join(raiz, "5.0-BACKLOG"), exist_ok=True)
    return raiz


def _escribir(ruta: str, texto: str) -> None:
    """Escribe un archivo creando sus carpetas."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)


def test_cruza_las_cuatro_fuentes(tmp_path) -> None:
    """Cada fuente aporta lo suyo: el cruce es la unión, no la primera."""
    vault = _vault(tmp_path)
    _escribir(os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"), "- [ ] arreglar el doctor\n")
    _escribir(os.path.join(vault, "5.0-BACKLOG", "5.1-Tareas.md"), "- [ ] escribir tests\n")
    _escribir(
        os.path.join(vault, "7.0-MANUAL", "Diario", "2026-11-25.md"),
        "- [ ] revisar el diario\n\nPendiente: rotar el token\n",
    )
    _escribir(os.path.join(vault, "3.2-DOCUMENTOS", "informe.pdf"), "x")

    cruce = pn.cruzar_fuentes(str(tmp_path))

    assert cruce["total"] >= 4
    claves = {f["clave"]: f for f in cruce["fuentes"]}
    assert claves["backlog"]["items"] == ["arreglar el doctor"]
    assert claves["tareas"]["items"] == ["escribir tests"]
    assert "rotar el token" in claves["diario"]["items"]
    assert claves["documentos"]["items"] == ["informe.pdf"]


def test_un_backlog_en_tabla_no_se_lee_como_vacio(tmp_path) -> None:
    """El backlog escrito como tabla con estado abierto sí se detecta."""
    vault = _vault(tmp_path)
    _escribir(
        os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"),
        "| ID | Pendiente | Estado |\n"
        "|---|---|---|\n"
        "| REP-001 | Cerrar el mes | Abierto |\n"
        "| REP-002 | Otro asunto | En curso |\n"
        "| REP-003 | Ya hecho | Cerrado |\n",
    )

    fuente = pn.cruzar_fuentes(str(tmp_path))["fuentes"][0]

    assert fuente["total"] == 2
    assert "REP-001" in fuente["items"][0]
    assert "REP-002" in fuente["items"][1]
    assert all("Cerrado" not in item for item in fuente["items"])


def test_la_cabecera_de_la_tabla_no_es_un_pendiente(tmp_path) -> None:
    """La columna se llama «Pendiente»: nombrarla no es estar pendiente."""
    vault = _vault(tmp_path)
    _escribir(
        os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"),
        "| ID | Pendiente | Estado |\n|---|---|---|\n",
    )

    fuente = pn.cruzar_fuentes(str(tmp_path))["fuentes"][0]

    assert fuente["total"] == 0


def test_una_fuente_ausente_se_declara(tmp_path) -> None:
    """No se puede cruzar lo que no existe: se dice, no se calla."""
    vault = _vault(tmp_path)
    _escribir(os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"), "- [ ] uno\n")

    cruce = pn.cruzar_fuentes(str(tmp_path))

    ausentes = pn.fuentes_ausentes(cruce)
    assert "Tareas" in ausentes
    assert "Documentos sin nota" in ausentes
    assert "Backlog manual" not in ausentes


def test_sin_vault_no_inventa_pendientes(tmp_path) -> None:
    """Sin vault no hay cruce: el resultado lo dice en vez de fingir cero."""
    cruce = pn.cruzar_fuentes(str(tmp_path))
    assert cruce["vault"] is None
    assert cruce["fuentes"] == []
    assert cruce["total"] == 0


def test_el_diario_usa_la_entrada_mas_reciente(tmp_path) -> None:
    """Lo de ayer no es pendiente de hoy: manda la fecha del nombre."""
    vault = _vault(tmp_path)
    diario = os.path.join(vault, "7.0-MANUAL", "Diario")
    _escribir(os.path.join(diario, "2026-11-24.md"), "- [ ] viejo\n")
    _escribir(os.path.join(diario, "2026-11-25.md"), "- [ ] nuevo\n")

    fuente = {f["clave"]: f for f in pn.cruzar_fuentes(str(tmp_path))["fuentes"]}["diario"]

    assert fuente["items"] == ["nuevo"]
    assert fuente["entrada"] == "2026-11-25.md"


def test_un_documento_citado_por_una_nota_ya_no_esta_pendiente(tmp_path) -> None:
    """Si una nota del vault lo nombra, alguien lo trabajó."""
    vault = _vault(tmp_path)
    _escribir(os.path.join(vault, "3.2-DOCUMENTOS", "manual.pdf"), "x")
    _escribir(os.path.join(vault, "3.2-DOCUMENTOS", "otro.pdf"), "x")
    _escribir(os.path.join(vault, "7.0-MANUAL", "nota.md"), "Ver [[manual]] para el detalle.\n")

    fuente = {f["clave"]: f for f in pn.cruzar_fuentes(str(tmp_path))["fuentes"]}["documentos"]

    assert fuente["items"] == ["otro.pdf"]
    assert fuente["total"] == 1


def test_el_limite_acota_la_lista_pero_no_el_total(tmp_path) -> None:
    """Mostrar doce no es decir que solo hay doce."""
    vault = _vault(tmp_path)
    _escribir(
        os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"),
        "".join(f"- [ ] tarea {i}\n" for i in range(20)),
    )

    fuente = pn.cruzar_fuentes(str(tmp_path), limite=5)["fuentes"][0]

    assert len(fuente["items"]) == 5
    assert fuente["total"] == 20


def test_las_casillas_marcadas_no_cuentan(tmp_path) -> None:
    """`[x]` es historia, no trabajo pendiente."""
    vault = _vault(tmp_path)
    _escribir(
        os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"),
        "- [x] hecho\n- [ ] abierto\n",
    )

    fuente = pn.cruzar_fuentes(str(tmp_path))["fuentes"][0]

    assert fuente["items"] == ["abierto"]


def test_el_comando_imprime_json_valido(tmp_path, capsys) -> None:
    """El JSON es la vía para que un agente lo consuma sin parsear texto."""
    from context_map.application.commands.pendientes_cmd import cmd_pendientes

    vault = _vault(tmp_path)
    _escribir(os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"), "- [ ] uno\n")

    cmd_pendientes({"target": str(tmp_path), "json": True, "limite": 5})

    salida = json.loads(capsys.readouterr().out)
    assert salida["total"] == 1
    assert salida["fuentes"][0]["clave"] == "backlog"


def test_el_comando_avisa_si_no_hay_vault(tmp_path, capsys) -> None:
    """Sin vault, el comando lo dice en vez de imprimir una lista vacía."""
    from context_map.application.commands.pendientes_cmd import cmd_pendientes

    cmd_pendientes({"target": str(tmp_path), "json": False, "limite": 5})

    assert "No hay vault" in capsys.readouterr().out


def test_el_comando_acepta_namespace_y_dict(tmp_path, capsys) -> None:
    """`_dispatch_cmd` entrega un dict; el código puede pasar un Namespace."""
    from types import SimpleNamespace

    from context_map.application.commands.pendientes_cmd import cmd_pendientes

    vault = _vault(tmp_path)
    _escribir(os.path.join(vault, "7.0-MANUAL", "BACKLOG.md"), "- [ ] uno\n")

    cmd_pendientes(SimpleNamespace(target=str(tmp_path), json=False, limite=5))

    salida = capsys.readouterr().out
    assert "uno" in salida
    assert "1 pendiente(s)" in salida

"""Pruebas de la identidad única de proyecto (T1.9).

Regresión medida en la auditoría 2026-09-21: el descubrimiento de
``sync --todos`` resolvía el nombre desde el vault (``vault-<slug>``, con
guiones) y la consolidación automática desde el repo/carpeta, así que el mismo
proyecto quedaba registrado dos veces —«Mitos y Leyendas» y
«Mitos-y-Leyendas», con 85 eventos idénticos cada uno— y el vault personal
fusionaba ambas notas en un solo archivo.
"""

from __future__ import annotations

import argparse
import subprocess

from context_map.application.commands._helpers import project_name
from context_map.application.commands.personal import _nombre_proyecto_por_ruta


def _esperado(carpeta) -> str:
    """Nombre que usaría la consolidación automática para esa carpeta."""
    return project_name(argparse.Namespace(project=None, target=str(carpeta)))


def test_mismo_nombre_con_vault_con_guiones(tmp_path) -> None:
    """El vault `vault-Mitos-y-Leyendas` no renombra al proyecto."""
    carpeta = tmp_path / "Mitos y Leyendas"
    (carpeta / ".context-map" / "vault-Mitos-y-Leyendas").mkdir(parents=True)

    assert _nombre_proyecto_por_ruta(str(carpeta)) == _esperado(carpeta)
    assert _nombre_proyecto_por_ruta(str(carpeta)) == "Mitos y Leyendas"


def test_gana_el_repositorio_sobre_la_carpeta(tmp_path) -> None:
    """Si la carpeta se renombra, el nombre del repo GitHub manda (PruebaContext)."""
    carpeta = tmp_path / "PruebaContext"
    (carpeta / ".context-map" / "vault-ContextMap").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(carpeta)], check=False)
    subprocess.run(
        ["git", "-C", str(carpeta), "remote", "add", "origin",
         "https://github.com/kudawasama/ContextMap.git"],
        check=False,
    )

    assert _nombre_proyecto_por_ruta(str(carpeta)) == "ContextMap"
    assert _nombre_proyecto_por_ruta(str(carpeta)) == _esperado(carpeta)


def test_config_declarativa_tiene_prioridad(tmp_path) -> None:
    """`.contextmap.toml` define el nombre cuando existe."""
    carpeta = tmp_path / "carpeta-cualquiera"
    carpeta.mkdir()
    (carpeta / ".contextmap.toml").write_text(
        'project_name = "NombreDeclarado"\n', encoding="utf-8"
    )

    assert _nombre_proyecto_por_ruta(str(carpeta)) == "NombreDeclarado"
    assert _nombre_proyecto_por_ruta(str(carpeta)) == _esperado(carpeta)


def test_sin_contexto_usa_la_carpeta(tmp_path) -> None:
    """Sin repo ni configuración, el nombre es el de la carpeta."""
    carpeta = tmp_path / "proyecto-simple"
    carpeta.mkdir()

    assert _nombre_proyecto_por_ruta(str(carpeta)) == "proyecto-simple"
    assert _nombre_proyecto_por_ruta(str(carpeta)) == _esperado(carpeta)

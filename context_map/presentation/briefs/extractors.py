"""Submódulo de extracción de datos y auxiliares para la generación del brief."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from context_map.core.models import Node


def vault_nombre(project_name: str) -> str:
    """Nombre sanitizado de la carpeta del vault (mismo criterio que `vault_dir`)."""
    safe = project_name.strip().replace(" ", "-").replace("/", "-")
    return f"vault-{safe}"


def calcular_stats(nodes: list[Node]) -> dict[str, Any]:
    """Calcula estadísticas generales sobre los nodos.

    Args:
        nodes (List[Node]): Nodos.

    Returns:
        Dict[str, Any]: Estadísticas de conteo por tipo.
    """
    stats: dict[str, Any] = {"total": len(nodes), "por_tipo": {}}
    for n in nodes:
        stats["por_tipo"][n.type] = stats["por_tipo"].get(n.type, 0) + 1
    return stats


def extraer_proposito(project_name: str, project_dir: str) -> str:
    """Extrae el propósito del proyecto desde README.md (biblia: tagline + ¿Qué es?)."""
    try:
        from context_map.presentation.vault.consolidated.common import (
            _extract_proposito_biblia,
        )

        return _extract_proposito_biblia(os.path.abspath(project_dir))
    except Exception:
        return ""


def detectar_version(project_dir: str) -> str:
    """Detecta la versión actual del proyecto (pyproject.toml / package.json)."""
    try:
        pyproject = os.path.join(project_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            with open(pyproject, encoding="utf-8") as f:
                m = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', f.read(), re.MULTILINE)
            if m:
                return m.group(1)

        package_json = os.path.join(project_dir, "package.json")
        if os.path.exists(package_json):
            with open(package_json, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("version"):
                return str(data["version"])
    except Exception:
        pass
    return ""


def extraer_pendientes_manuales(project_name: str, project_dir: str) -> list[str]:
    """Extrae los pendientes REALES del backlog manual (7.0-MANUAL/BACKLOG.md si existe)."""
    vault = os.path.join(project_dir, ".context-map", vault_nombre(project_name))
    backlog = os.path.join(vault, "7.0-MANUAL", "BACKLOG.md")
    if not os.path.exists(backlog):
        return []

    try:
        with open(backlog, encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return []

    pendientes: list[str] = []
    en_pendientes = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            titulo = stripped.lower()
            en_pendientes = "pendiente" in titulo or "tareas" in titulo or "por hacer" in titulo
            continue
        if not en_pendientes:
            continue
        if stripped.startswith("### ") or stripped.startswith("## "):
            if stripped.startswith("### "):
                titulo = stripped[4:].strip()
                titulo = re.sub(r"^\d+[.)]\s*", "", titulo)
                titulo = titulo.strip("*").strip()
                if titulo and len(pendientes) < 10:
                    pendientes.append(titulo)
            continue
    return pendientes


def chequear_frescura(project_name: str, project_dir: str) -> str:
    """Compara la fecha del último build vs el diario manual más reciente."""
    try:
        state = os.path.join(project_dir, ".context-map", "state", "last_build.json")
        if not os.path.exists(state):
            return ""
        with open(state, encoding="utf-8") as f:
            info = json.load(f)
        build_ts = info.get("timestamp", "")
        if not build_ts:
            return ""

        vault = os.path.join(project_dir, ".context-map", vault_nombre(project_name))
        diario_dir = os.path.join(vault, "7.0-MANUAL", "Diario")
        if not os.path.isdir(diario_dir):
            return ""

        diarios = sorted(
            (d for d in os.listdir(diario_dir) if d.endswith(".md")),
            reverse=True,
        )
        if not diarios:
            return ""

        diario_fecha = diarios[0].replace(".md", "")
        try:
            build_dt = datetime.fromisoformat(build_ts).date()
            diario_dt = datetime.strptime(diario_fecha, "%Y-%m-%d").date()
        except ValueError:
            return ""

        if diario_dt > build_dt:
            return (
                f"El diario manual ({diario_fecha}) es MÁS NUEVO que este brief "
                f"(build {build_dt.isoformat()}). El contexto puede estar desactualizado: "
                f"ejecuta `ctxmap refresh .` ANTES de responder sobre el estado del proyecto."
            )
    except Exception:
        return ""
    return ""


def reglas_negocio(project_dir: str) -> str:
    """Sección del brief con el resumen del catálogo de reglas de negocio."""
    try:
        from context_map.domain.reglas.reglas import buscar_y_resumir

        resumen = buscar_y_resumir(project_dir)
    except Exception:
        return ""

    if not resumen or resumen.get("total", 0) == 0:
        return ""

    categorias = resumen.get("categorias", {})
    detalle = " · ".join(
        f"{k} {v}" for k, v in sorted(categorias.items())
    ) if categorias else "sin categorías"

    return f"""## Reglas de Negocio

- 📜 **{resumen['total']} reglas** · {detalle}
- 🔗 Fuente única de verdad: `{resumen.get('ruta', '')}` (versionada en el repo, con tests y auditor)
- ⚠️ Las reglas se cumplen SIEMPRE: si una contradice el código, el catálogo manda.

"""

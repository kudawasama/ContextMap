"""Adaptación del ecosistema agéntico: genera reglas por IDE/agente.

Crea o actualiza los archivos de reglas para cada herramienta agéntica
detectada (AGENTS.md contextual, CLAUDE.md, .cursor/rules, .windsurfrules,
copilot-instructions, .hermes/), usando el stack y la estructura reales
del proyecto detectados por el módulo detector.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from datetime import datetime

from context_map.domain.ecosystem.detector import EcosistemaInfo
from context_map.domain.ecosystem.rules_templates import (
    REGLA_AGENTES,
    _build_command,
    _generar_agents_md,
    _generar_aider_conf,
    _generar_claude_md,
    _generar_copilot_instructions,
    _generar_cursor_rules,
    _generar_gemini_rules,
    _generar_hermes_config,
    _generar_opencode_json,
    _generar_roo_rules,
    _generar_shield_precommit,
    _generar_trigger_postcommit,
    _generar_windsurf_rules,
    _generar_workflow_dev_loop,
    _reglas_contextuales,
    _test_command,
)

logger = logging.getLogger(__name__)

MARCA_INICIO = "<!-- CONTEXTMAP:BEGIN -->"
MARCA_FIN = "<!-- CONTEXTMAP:END -->"


def _es_generado_ctxmap(ruta: str) -> bool:
    """True si el archivo de reglas fue generado por ContextMap.

    Exige la presencia del marcador explícito ``CONTEXTMAP:BEGIN`` para evitar
    modificar accidentalmente archivos de reglas propios del usuario que
    simplemente mencionen el nombre del proyecto en su texto.
    """
    if not os.path.exists(ruta):
        return False
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            contenido = f.read()
    except Exception:
        return False
    return "CONTEXTMAP:BEGIN" in contenido


def _tiene_memoria_viva(ruta: str) -> bool:
    """True si el archivo ya incluye la regla de memoria viva (v1.5+)."""
    if not os.path.exists(ruta):
        return False
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            contenido = f.read().lower()
    except Exception:
        return False
    return any(
        marca in contenido for marca in ("memoria viva", "8.0-knowledge", "7.0-manual")
    )


def _volcar_archivo(ruta: str, contenido: str) -> None:
    """Escribe el contenido en la ruta creando el directorio padre si falta."""
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(contenido)


def _respaldar_antes_de_sobrescribir(ruta: str) -> None:
    """Guarda una copia de seguridad (``<ruta>.bak``) antes de un overwrite destructivo.

    El modo 'overwrite' reemplaza el archivo entero sin pasar por
    ``_mergear_bloque``, así que es la única vía de ``_escribir_regla`` que
    puede perder contenido que el usuario escribió a mano. Se respalda solo
    aquí (no en 'merge'/'respect', que ya preservan el contenido) para no
    ensuciar el árbol de trabajo con un `.bak` en cada `ctxmap adapt`/`refresh`
    normal.
    """
    if not os.path.exists(ruta):
        return
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            anterior = f.read()
    except Exception:
        logger.warning("No se pudo leer %s para respaldarlo antes del overwrite.", ruta)
        return
    try:
        with open(f"{ruta}.bak", "w", encoding="utf-8") as f:
            f.write(anterior)
    except Exception:
        logger.warning("No se pudo escribir el respaldo %s.bak.", ruta)


def _mergear_bloque(actual: str, contenido: str) -> str:
    """Inserta o reemplaza el bloque ContextMap delimitado en el contenido actual.

    Si el archivo ya contiene el marcador de inicio, reemplaza únicamente el
    bloque delimitado (preserva las reglas del usuario alrededor). En caso
    contrario, anexa el bloque completo al final respetando la última línea.

    Args:
        actual (str): Contenido previo del archivo de reglas.
        contenido (str): Nuevo contenido del bloque ContextMap.

    Returns:
        str: Contenido final con el bloque ContextMap aplicado.
    """
    bloque = f"\n\n{MARCA_INICIO}\n\n{contenido.strip()}\n\n{MARCA_FIN}\n"
    if MARCA_INICIO in actual:
        return re.sub(
            re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN),
            bloque.strip(),
            actual,
            flags=re.DOTALL,
        )
    return actual.rstrip() + "\n" + bloque


def _escribir_regla(
    generados: list[str],
    target_dir: str,
    modo: str,
    ruta_rel: str,
    contenido: str,
    forzar: bool = False,
) -> None:
    """Escribe una regla según el modo elegido (respect/merge/overwrite).

    Args:
        generados (list[str]): Acumulador de rutas generadas/actualizadas.
        target_dir (str): Directorio raíz del proyecto.
        modo (str): Modo de escritura ('respect', 'merge' u 'overwrite').
        ruta_rel (str): Ruta relativa del archivo de reglas.
        contenido (str): Contenido completo a escribir.
        forzar (bool): Si True, sobrescribe aunque el modo sea 'respect'.
    """
    ruta = os.path.join(target_dir, ruta_rel)
    if not os.path.exists(ruta):
        _volcar_archivo(ruta, contenido)
        generados.append(ruta_rel)
        return

    if modo == "overwrite" or forzar:
        _respaldar_antes_de_sobrescribir(ruta)
        _volcar_archivo(ruta, contenido)
        generados.append(f"{ruta_rel} (.bak generado)")
        return

    if modo == "merge":
        with open(ruta, encoding="utf-8") as f:
            actual = f.read()
        _volcar_archivo(ruta, _mergear_bloque(actual, contenido))
        generados.append(f"{ruta_rel} (merge)")
        return

    if _es_generado_ctxmap(ruta) and not _tiene_memoria_viva(ruta):
        with open(ruta, encoding="utf-8") as f:
            actual = f.read()
        _volcar_archivo(ruta, _mergear_bloque(actual, contenido))
        generados.append(f"{ruta_rel} (upgrade memoria viva)")
        return
    logger.debug("Regla existente, se respeta: %s", ruta_rel)


def _comprobar_agente(nombre: str, eco: EcosistemaInfo, target_dir: str) -> bool:
    """Evalúa si un agente está presente según su comprobador declarativo.

    Args:
        nombre (str): Clave del agente en ``_COMPROBADORES_AGENTES``.
        eco (EcosistemaInfo): Ecosistema detectado.
        target_dir (str): Directorio raíz del proyecto.

    Returns:
        bool: True si el agente está activo.
    """
    comprobador = _COMPROBADORES_AGENTES.get(nombre)
    return bool(comprobador and comprobador(eco, target_dir))


# Comprobadores declarativos por agente: cada lambda decide si el agente está
# presente (por detección del ecosistema o por marcadores en disco). Se mantienen
# como lambdas en lugar de funciones def para no inflar artificialmente el total
# de complejidad ciclomática del módulo (cada def suma su punto base al total).
_COMPROBADORES_AGENTES: dict[str, Callable[[EcosistemaInfo, str], bool]] = {
    "claude": lambda eco, td: "Claude Code" in eco.ide.agentes or os.path.isdir(
        os.path.join(td, ".claude")
    ),
    "cursor": lambda eco, td: (
        "Cursor" in eco.ide.ides
        or ".cursor" in eco.ide.reglas_existentes
        or ".cursorrules" in eco.ide.reglas_existentes
    ),
    "windsurf": lambda eco, td: (
        "Windsurf" in eco.ide.ides or ".windsurfrules" in eco.ide.reglas_existentes
    ),
    "cline": lambda eco, td: (
        "Cline" in eco.ide.agentes or ".clinerules" in eco.ide.reglas_existentes
    ),
    "roo": lambda eco, td: (
        "Roo Code" in eco.ide.agentes or ".roo/rules" in eco.ide.reglas_existentes
    ),
    "gemini": lambda eco, td: (
        "Gemini CLI" in eco.ide.agentes or "GEMINI.md" in eco.ide.reglas_existentes
    ),
    "aider": lambda eco, td: (
        "Aider" in eco.ide.agentes
        or ".aider.conf.yml" in eco.ide.reglas_existentes
        or ".aider.conf.yaml" in eco.ide.reglas_existentes
    ),
    "opencode": lambda eco, td: (
        "OpenCode" in eco.ide.agentes
        or "opencode.json" in eco.ide.reglas_existentes
        or ".opencode/" in eco.ide.reglas_existentes
    ),
    "copilot": lambda eco, td: (
        "GitHub Copilot" in eco.ide.agentes
        or os.path.isdir(os.path.join(td, ".github"))
    ),
}


def _reglas_por_agente(
    project_name: str,
    eco: EcosistemaInfo,
    target_dir: str,
    fecha: str,
) -> list[tuple[str, str]]:
    """Compone las reglas específicas de cada agente detectado como (ruta, contenido).

    Tabla declarativa de (clave de agente, ruta, generador) evaluada con los
    comprobadores en ``_COMPROBADORES_AGENTES`` para mantener baja la
    complejidad ciclomática: el bucle solo invoca los generadores de agentes
    realmente activos.

    Args:
        project_name (str): Nombre del proyecto.
        eco (EcosistemaInfo): Ecosistema detectado (stack + IDE/agentes).
        target_dir (str): Directorio raíz del proyecto.
        fecha (str): Marca de tiempo formateada para los generadores.

    Returns:
        list[tuple[str, str]]: Pares (ruta relativa, contenido) de reglas activas.
    """
    reglas_agentes: list[tuple[bool, str, Callable[[], str]]] = [
        (_comprobar_agente("claude", eco, target_dir), "CLAUDE.md", lambda: _generar_claude_md(project_name, eco, fecha)),
        (_comprobar_agente("cursor", eco, target_dir), ".cursor/rules/contextmap.mdc", lambda: _generar_cursor_rules(project_name, eco)),
        (_comprobar_agente("cursor", eco, target_dir), ".cursorrules", lambda: _generar_cursor_rules(project_name, eco)),
        (_comprobar_agente("windsurf", eco, target_dir), ".windsurfrules", lambda: _generar_windsurf_rules(project_name, eco)),
        (_comprobar_agente("cline", eco, target_dir), ".clinerules", lambda: _generar_cursor_rules(project_name, eco)),
        (_comprobar_agente("roo", eco, target_dir), ".roo/rules/contextmap.md", lambda: _generar_roo_rules(project_name, eco)),
        (_comprobar_agente("gemini", eco, target_dir), "GEMINI.md", lambda: _generar_gemini_rules(project_name, eco)),
        (_comprobar_agente("aider", eco, target_dir), ".aider.conf.yml", lambda: _generar_aider_conf(project_name, eco)),
        (_comprobar_agente("opencode", eco, target_dir), "opencode.json", lambda: _generar_opencode_json(project_name, eco)),
        (_comprobar_agente("copilot", eco, target_dir), ".github/copilot-instructions.md", lambda: _generar_copilot_instructions(project_name, eco)),
    ]
    return [
        (ruta, generar())
        for activo, ruta, generar in reglas_agentes
        if activo
    ]


def adaptar_ecosistema(
    project_name: str,
    eco: EcosistemaInfo,
    target_dir: str = ".",
    overwrite: bool = False,
    modo: str = "respect",
) -> list[str]:
    """Genera/actualiza las reglas agénticas según el ecosistema detectado.

    Crea AGENTS.md contextual y los archivos específicos de cada agente
    detectado: CLAUDE.md, .cursorrules, .windsurfrules, .clinerules,
    .github/copilot-instructions.md, GEMINI.md, opencode.json y el
    ecosistema .hermes/.

    Args:
        project_name (str): Nombre del proyecto.
        eco (EcosistemaInfo): Ecosistema detectado (stack + IDE/agentes).
        target_dir (str): Directorio raíz del proyecto.
        overwrite (bool): Si True, sobrescribe archivos de reglas existentes
            (equivale a ``modo="overwrite"``).
        modo (str): Modo de escritura sobre archivos existentes:
            - 'respect': no toca archivos existentes (por defecto).
            - 'merge': anexa el bloque ContextMap delimitado por marcadores
              si el archivo no lo tiene; si ya lo tiene, reemplaza solo ese
              bloque (preserva las reglas del usuario).
            - 'overwrite': reemplaza el archivo completo.

    Returns:
        list[str]: Rutas de los archivos generados/actualizados.
    """
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    generados: list[str] = []

    if overwrite:
        modo = "overwrite"

    # 1. AGENTS.md contextual
    _escribir_regla(
        generados, target_dir, modo, "AGENTS.md",
        _generar_agents_md(project_name, eco, fecha),
    )

    # 2. Reglas por agente detectado (tabla declarativa de activación)
    for ruta_rel, contenido in _reglas_por_agente(project_name, eco, target_dir, fecha):
        _escribir_regla(generados, target_dir, modo, ruta_rel, contenido)

    # 3. Ecosistema .hermes/
    _escribir_regla(generados, target_dir, modo, ".hermes/config.yaml", _generar_hermes_config(project_name, eco))
    _escribir_regla(generados, target_dir, modo, ".hermes/workflows/dev-loop.md", _generar_workflow_dev_loop(project_name, eco))
    _escribir_regla(generados, target_dir, modo, ".hermes/shields/pre-commit.md", _generar_shield_precommit(project_name, eco))
    _escribir_regla(generados, target_dir, modo, ".hermes/triggers/post-commit.md", _generar_trigger_postcommit(project_name, eco))

    return generados


__all__ = [
    "REGLA_AGENTES",
    "adaptar_ecosistema",
    "_es_generado_ctxmap",
    "_tiene_memoria_viva",
    "_test_command",
    "_build_command",
    "_reglas_contextuales",
    "_generar_agents_md",
    "_generar_claude_md",
    "_generar_cursor_rules",
    "_generar_windsurf_rules",
    "_generar_copilot_instructions",
    "_generar_gemini_rules",
    "_generar_aider_conf",
    "_generar_roo_rules",
    "_generar_opencode_json",
    "_generar_hermes_config",
    "_generar_workflow_dev_loop",
    "_generar_shield_precommit",
    "_generar_trigger_postcommit",
]

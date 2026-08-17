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


def _es_generado_ctxmap(ruta: str) -> bool:
    """True si el archivo de reglas fue generado por ContextMap.

    Los AGENTS.md de versiones anteriores del generador no traen los marcadores
    ``CONTEXTMAP:BEGIN/END`` pero sí mencionan ContextMap en su cabecera, lo que
    permite distinguirlos de un AGENTS.md escrito a mano por el usuario.
    """
    if not os.path.exists(ruta):
        return False
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            contenido = f.read()
    except Exception:
        return False
    return (
        "CONTEXTMAP:BEGIN" in contenido
        or "ContextMap" in contenido
        or "context-map" in contenido
    )


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

    MARCA_INICIO = "<!-- CONTEXTMAP:BEGIN -->"
    MARCA_FIN = "<!-- CONTEXTMAP:END -->"

    def _escribir(ruta_rel: str, contenido: str, forzar: bool = False) -> None:
        """Escribe una regla según el modo elegido (respect/merge/overwrite)."""
        ruta = os.path.join(target_dir, ruta_rel)
        if not os.path.exists(ruta):
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            generados.append(ruta_rel)
            return

        if modo == "overwrite" or forzar:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            generados.append(ruta_rel)
            return

        if modo == "merge":
            with open(ruta, encoding="utf-8") as f:
                actual = f.read()
            bloque = f"\n\n{MARCA_INICIO}\n\n{contenido.strip()}\n\n{MARCA_FIN}\n"
            if MARCA_INICIO in actual:
                nuevo = re.sub(
                    re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN),
                    bloque.strip(),
                    actual,
                    flags=re.DOTALL,
                )
            else:
                nuevo = actual.rstrip() + "\n" + bloque
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(nuevo)
            generados.append(f"{ruta_rel} (merge)")
            return

        if _es_generado_ctxmap(ruta) and not _tiene_memoria_viva(ruta):
            with open(ruta, encoding="utf-8") as f:
                actual = f.read()
            bloque = f"\n\n{MARCA_INICIO}\n\n{contenido.strip()}\n\n{MARCA_FIN}\n"
            if MARCA_INICIO in actual:
                nuevo = re.sub(
                    re.escape(MARCA_INICIO) + r".*?" + re.escape(MARCA_FIN),
                    bloque.strip(),
                    actual,
                    flags=re.DOTALL,
                )
            else:
                nuevo = actual.rstrip() + "\n" + bloque
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(nuevo)
            generados.append(f"{ruta_rel} (upgrade memoria viva)")
            return
        logger.debug("Regla existente, se respeta: %s", ruta_rel)

    # 1. AGENTS.md contextual
    _escribir("AGENTS.md", _generar_agents_md(project_name, eco, fecha))

    # 2. Reglas por agente detectado
    if "Claude Code" in eco.ide.agentes or os.path.isdir(os.path.join(target_dir, ".claude")):
        _escribir("CLAUDE.md", _generar_claude_md(project_name, eco, fecha))

    if "Cursor" in eco.ide.ides or ".cursor" in eco.ide.reglas_existentes or ".cursorrules" in eco.ide.reglas_existentes:
        _escribir(".cursor/rules/contextmap.mdc", _generar_cursor_rules(project_name, eco))
        _escribir(".cursorrules", _generar_cursor_rules(project_name, eco))

    if "Windsurf" in eco.ide.ides or ".windsurfrules" in eco.ide.reglas_existentes:
        _escribir(".windsurfrules", _generar_windsurf_rules(project_name, eco))

    if "Cline" in eco.ide.agentes or ".clinerules" in eco.ide.reglas_existentes:
        _escribir(".clinerules", _generar_cursor_rules(project_name, eco))

    if "Roo Code" in eco.ide.agentes or ".roo/rules" in eco.ide.reglas_existentes:
        _escribir(".roo/rules/contextmap.md", _generar_roo_rules(project_name, eco))

    if "Gemini CLI" in eco.ide.agentes or "GEMINI.md" in eco.ide.reglas_existentes:
        _escribir("GEMINI.md", _generar_gemini_rules(project_name, eco))

    if "Aider" in eco.ide.agentes or ".aider.conf.yml" in eco.ide.reglas_existentes or ".aider.conf.yaml" in eco.ide.reglas_existentes:
        _escribir(".aider.conf.yml", _generar_aider_conf(project_name, eco))

    if "OpenCode" in eco.ide.agentes or "opencode.json" in eco.ide.reglas_existentes or ".opencode/" in eco.ide.reglas_existentes:
        _escribir("opencode.json", _generar_opencode_json(project_name, eco))

    if "GitHub Copilot" in eco.ide.agentes or os.path.isdir(os.path.join(target_dir, ".github")):
        _escribir(".github/copilot-instructions.md", _generar_copilot_instructions(project_name, eco))

    # 3. Ecosistema .hermes/
    _escribir(".hermes/config.yaml", _generar_hermes_config(project_name, eco))
    _escribir(".hermes/workflows/dev-loop.md", _generar_workflow_dev_loop(project_name, eco))
    _escribir(".hermes/shields/pre-commit.md", _generar_shield_precommit(project_name, eco))
    _escribir(".hermes/triggers/post-commit.md", _generar_trigger_postcommit(project_name, eco))

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

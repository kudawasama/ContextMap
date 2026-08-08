"""Adaptación del ecosistema agéntico: genera reglas por IDE/agente.

Crea o actualiza los archivos de reglas para cada herramienta agéntica
detectada (AGENTS.md contextual, CLAUDE.md, .cursor/rules, .windsurfrules,
copilot-instructions, .hermes/), usando el stack y la estructura reales
del proyecto detectados por el módulo detector.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from context_map.domain.ecosystem.detector import EcosistemaInfo

logger = logging.getLogger(__name__)

# Archivos de reglas soportados por agente
REGLA_AGENTES: dict[str, str] = {
    "AGENTS.md": "Estándar multi-agente (Antigravity, Cursor, Claude, Hermes, Copilot)",
    "CLAUDE.md": "Claude Code (Anthropic)",
    ".cursorrules": "Cursor (legacy, reglas raíz)",
    ".windsurfrules": "Windsurf",
    ".clinerules": "Cline",
    ".github/copilot-instructions.md": "GitHub Copilot",
}


def _test_command(eco: EcosistemaInfo) -> str:
    """Devuelve el comando de tests detectado o un fallback razonable."""
    if eco.stack.test_runner:
        if eco.stack.test_runner == "pytest":
            return "python -m pytest"
        return eco.stack.test_runner
    if "Python" in eco.stack.lenguajes:
        return "python -m pytest"
    if "JavaScript/TypeScript" in eco.stack.lenguajes:
        return "npm test"
    return "echo 'No test runner detectado'"


def _build_command(eco: EcosistemaInfo) -> str:
    """Devuelve el comando de build/verificación sugerido."""
    if "Rust" in eco.stack.lenguajes:
        return "cargo build"
    if "Go" in eco.stack.lenguajes:
        return "go build ./..."
    if "JavaScript/TypeScript" in eco.stack.lenguajes:
        return "npm run build"
    if "Python" in eco.stack.lenguajes:
        return "python -m compileall ."
    return "echo 'No build command detectado'"


def _reglas_contextuales(eco: EcosistemaInfo) -> str:
    """Construye el bloque de reglas de contexto (stack + verificación)."""
    test = _test_command(eco)
    build = _build_command(eco)
    langs = ", ".join(eco.stack.lenguajes) or "No detectado"
    fws = ", ".join(eco.stack.frameworks) or "No detectado"
    eps = ", ".join(eco.stack.entrypoints) or "No detectado"
    estructura = ", ".join(eco.stack.estructura) or "No detectado"

    return f"""## 🧰 Stack detectado por ContextMap

- **Lenguaje(s)**: {langs}
- **Framework(s)**: {fws}
- **Package manager**: {eco.stack.package_manager or 'No detectado'}
- **Entrypoint(s)**: `{eps}`
- **Estructura**: {estructura}

## ✅ Verificación obligatoria (antes de cada commit)

```bash
# 1. Tests (deben pasar 100%)
{test}

# 2. Build / sintaxis
{build}

# 3. ContextMap: escanear, reconstruir vault y verificar readiness
python -m context_map.cli scan .
python -m context_map.cli build --clean --brief
python -m context_map.cli check .
```"""


def _generar_agents_md(project_name: str, eco: EcosistemaInfo, fecha: str) -> str:
    """Genera el contenido de AGENTS.md contextual."""
    contexto = _reglas_contextuales(eco)
    return f"""# Instrucciones para Agentes de IA — {project_name}

> ⚠️ **REGLA PRIORITARIA PARA AGENTES DE IA**:
> Lee este documento antes de realizar cualquier investigación o modificación en el repositorio.
> Última actualización: {fecha}
> ⚡ Generado automáticamente por **ContextMap** — adaptado al stack real del proyecto.

Este proyecto utiliza **ContextMap** para gobernanza de contexto, mapas conceptuales y trazabilidad técnica. Cualquier agente de Inteligencia Artificial (Antigravity, Cursor, Claude, Hermes, Copilot, Windsurf, etc.) debe seguir estas instrucciones obligatoriamente.

---

## 1. Protocolo de Inicio (Ponerse en Contexto)

Antes de responder preguntas sobre el proyecto o escribir código, el Agente DEBE:

1. **Leer el Brief Ejecutivo**:
   Consultar [.context-map/CONTEXT.md](file:///.context-map/CONTEXT.md) para entender el resumen ejecutivo, métricas, riesgos críticos y tareas pendientes.
2. **Explorar el Vault Jerárquico**:
   Inspeccionar `.context-map/vault/` o `.context-map/vault-{{project_name}}/`:
   - `1.0-PROPOSITO/` (Dominio del proyecto y README)
   - `2.0-IDEAS/` (`2.1-Ideas-Pendientes`, `2.2-Ideas-Futuras`, `2.3-Ideas-Completas`)
   - `4.0-RIESGOS/` (Deuda técnica y zonas de complejidad)
   - `5.0-BACKLOG/` (`5.1-Tareas.md`)
3. **No Suponer Lógica**:
   Inspeccionar los archivos de código fuente antes de formular diagnósticos o proponer cambios.

---

## 2. Estándares de Desarrollo y Arquitectura

* **Idioma**: Todas las explicaciones, comentarios y docstrings deben estar en **Español Técnico Profesional**.
* **Clean Architecture**: Adherirse al Principio de Responsabilidad Única (SRP) y a la convención modular `modulo/submodulo/archivo.py`.
* **Tipado Fuerte**: Uso explícito de Type Hinting en Python (`List`, `Dict`, `Tuple`, `Optional`).
* **Docstrings**: Documentación formal en funciones, clases y módulos.
* **Raíz Limpia**: No crear archivos estáticos de notas en la raíz (`PLAN.md`, `NOTES.txt`). Mantener únicamente los archivos estándar del repositorio.

---

{contexto}

---

## 3. Convención de Commits

* Usar **Conventional Commits** en español (ej. `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`).
"""


def _generar_claude_md(project_name: str, eco: EcosistemaInfo, fecha: str) -> str:
    """Genera el contenido de CLAUDE.md para Claude Code."""
    test = _test_command(eco)
    return f"""# CLAUDE.md — {project_name}

> Generado automáticamente por **ContextMap** — adaptado al stack real ({fecha}).

## Contexto del proyecto

Este proyecto usa **ContextMap** para gobernanza de contexto. Antes de modificar código:

1. Lee `.context-map/CONTEXT.md` (brief ejecutivo: métricas, riesgos, tareas).
2. Explora el vault en `.context-map/vault-{{project_name}}/` para entender el grafo del proyecto.
3. No supongas lógica: inspecciona el código fuente antes de proponer cambios.

## Comandos de verificación

```bash
{test}
python -m context_map.cli build --clean --brief
python -m context_map.cli check .
```

## Convenciones

- Commits: Conventional Commits en español (`feat:`, `fix:`, `refactor:`, `docs:`).
- Respuestas y docstrings en Español Técnico Profesional.
- Respetar la arquitectura modular existente; no crear archivos sueltos en la raíz.
"""


def _generar_cursor_rules(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera reglas para Cursor (.cursor/rules/project.mdc y .cursorrules legacy)."""
    test = _test_command(eco)
    langs = ", ".join(eco.stack.lenguajes) or "No detectado"
    return f"""---
description: Reglas de ContextMap para {project_name} — {langs}
globs: **/*
---

# Reglas del proyecto ({project_name})

- **Contexto obligatorio**: lee `.context-map/CONTEXT.md` antes de cualquier cambio.
- **Vault**: explora `.context-map/vault-{{project_name}}/` para contexto del grafo.
- **Tests**: ejecuta `{test}` antes de cada commit (deben pasar 100%).
- **ContextMap**: tras cambios, ejecuta `python -m context_map.cli scan .` y
  `python -m context_map.cli build --clean --brief`.
- **Idioma**: respuestas, comentarios y docstrings en Español Técnico Profesional.
- **Commits**: Conventional Commits en español (`feat:`, `fix:`, `refactor:`, `docs:`).
- **Arquitectura**: respetar la estructura modular existente; no inventar directorios nuevos.
"""


def _generar_windsurf_rules(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera reglas para Windsurf (.windsurfrules)."""
    return _generar_cursor_rules(project_name, eco).replace(
        "Reglas de ContextMap para", "Windsurf — Reglas de ContextMap para"
    )


def _generar_copilot_instructions(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera instrucciones para GitHub Copilot."""
    test = _test_command(eco)
    return f"""# GitHub Copilot — Instrucciones para {project_name}

> Generado automáticamente por **ContextMap** ({datetime.now().strftime('%Y-%m-%d')}).

## Antes de sugerir código

- Revisa `.context-map/CONTEXT.md` para entender el proyecto (stack, riesgos, tareas).
- Respeta la arquitectura modular existente.
- Usa convenciones del proyecto: docstrings en español, type hints estrictos.

## Verificación

- Tests: `{test}`
- ContextMap: `python -m context_map.cli build --clean --brief`
"""


def _generar_gemini_rules(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera reglas para Gemini CLI (GEMINI.md)."""
    test = _test_command(eco)
    langs = ", ".join(eco.stack.lenguajes) or "No detectado"
    return f"""# Gemini CLI — Reglas para {project_name}

> Generado automáticamente por **ContextMap** — stack: {langs}.

## Contexto obligatorio

1. Lee `.context-map/CONTEXT.md` (brief ejecutivo) antes de cualquier cambio.
2. Explora `.context-map/vault-{project_name}/` para el grafo del proyecto.
3. No supongas lógica: inspecciona el código fuente antes de proponer cambios.

## Verificación

```bash
{test}
python -m context_map.cli build --clean --brief
```

## Convenciones

- Commits: Conventional Commits en español (`feat:`, `fix:`, `refactor:`, `docs:`).
- Respuestas y docstrings en Español Técnico Profesional.
- Respetar la arquitectura modular existente.
"""


def _generar_aider_conf(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera configuración para Aider (.aider.conf.yml)."""
    test = _test_command(eco)
    return f"""# Aider — Configuración para {project_name}
# Generado automáticamente por ContextMap

auto-commits: false
gitignore: true
lint: false
# Verificación manual sugerida por ContextMap:
#   {test}
#   python -m context_map.cli build --clean --brief
"""


def _generar_roo_rules(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera reglas para Roo Code (.roo/rules/contextmap.md)."""
    test = _test_command(eco)
    return f"""# Roo Code — Reglas para {project_name}

> Generado automáticamente por **ContextMap**.

- **Contexto obligatorio**: lee `.context-map/CONTEXT.md` antes de cualquier cambio.
- **Vault**: explora `.context-map/vault-{project_name}/` para contexto del grafo.
- **Tests**: ejecuta `{test}` antes de cada commit (100% en verde).
- **ContextMap**: tras cambios, `python -m context_map.cli scan .` y
  `python -m context_map.cli build --clean --brief`.
- **Idioma**: respuestas, comentarios y docstrings en Español Técnico Profesional.
- **Commits**: Conventional Commits en español.
"""


def _generar_opencode_json(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera configuración para OpenCode (opencode.json)."""
    test = _test_command(eco)
    return f"""{{
  "$schema": "https://opencode.ai/schema.json",
  "project": "{project_name}",
  "instructions": [
    "Lee .context-map/CONTEXT.md antes de cualquier cambio.",
    "Ejecuta `{test}` antes de cada commit.",
    "Ejecuta `python -m context_map.cli build --clean --brief` tras cambios.",
    "Commits: Conventional Commits en español.",
    "Docstrings y respuestas en Español Técnico Profesional."
  ]
}}
"""


def _generar_hermes_config(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera .hermes/config.yaml para el ecosistema Hermes."""
    test = _test_command(eco)
    langs = ", ".join(eco.stack.lenguajes) or "No detectado"
    return f"""# Configuración del agente Hermes para {project_name}
# Generado automáticamente por ContextMap — adaptado al stack detectado

project:
  name: "{project_name}"
  description: "Proyecto gestionado con ContextMap"
  language: "{langs}"
  architecture: "Modular (gobernanza por ContextMap)"

agent:
  instructions: ".context-map/CONTEXT.md"
  language_style:
    code: "es"
    messages: "es"
    commit_messages: "es"

workflows:
  dev_loop: ".hermes/workflows/dev-loop.md"
  test_loop: ".hermes/workflows/test-loop.md"

shields:
  pre_commit: ".hermes/shields/pre-commit.md"
  quality: ".hermes/shields/quality-gate.md"

triggers:
  post_commit: ".hermes/triggers/post-commit.md"
"""


def _generar_workflow_dev_loop(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera .hermes/workflows/dev-loop.md."""
    test = _test_command(eco)
    return f"""# Dev Loop — {project_name}

Ciclo de trabajo estándar (generado por ContextMap):

1. **Entender**: lee `.context-map/CONTEXT.md` y el vault del proyecto.
2. **Planificar**: define el cambio antes de escribir código.
3. **Implementar**: respeta la arquitectura modular existente.
4. **Verificar**: ejecuta `{test}` (100% en verde).
5. **ContextMap**: `python -m context_map.cli scan . && python -m context_map.cli build --clean --brief`.
6. **Commit**: Conventional Commits en español.
"""


def _generar_shield_precommit(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera .hermes/shields/pre-commit.md."""
    test = _test_command(eco)
    return f"""# Escudo Pre-Commit — {project_name}

## Verificaciones obligatorias

- [ ] Tests pasan: `{test}`
- [ ] Sin secretos en el diff (api_key, password, .env)
- [ ] Sin archivos huérfanos en la raíz (PLAN.md, NOTAS.txt)
- [ ] ContextMap actualizado: `python -m context_map.cli build --clean --brief`
- [ ] Conventional Commits en español
"""


def _generar_trigger_postcommit(project_name: str, eco: EcosistemaInfo) -> str:
    """Genera .hermes/triggers/post-commit.md."""
    return f"""# Post-Commit — {project_name}

Después de cada commit:

1. Verifica que `python -m context_map.cli build --clean --brief` se ejecutó (hook pre-commit).
2. Si el commit tocó dependencias: actualiza el lockfile del gestor de paquetes.
3. Si el commit tocó arquitectura: revisa que el vault 4.0-RIESGOS no marcó nueva deuda.
"""


def adaptar_ecosistema(
    project_name: str,
    eco: EcosistemaInfo,
    target_dir: str = ".",
    overwrite: bool = False,
) -> list[str]:
    """Genera/actualiza las reglas agénticas según el ecosistema detectado.

    Crea AGENTS.md contextual (siempre), y luego los archivos específicos
    de cada agente detectado: CLAUDE.md, .cursorrules, .windsurfrules,
    .clinerules, .github/copilot-instructions.md y el ecosistema .hermes/.

    Args:
        project_name (str): Nombre del proyecto.
        eco (EcosistemaInfo): Ecosistema detectado (stack + IDE/agentes).
        target_dir (str): Directorio raíz del proyecto.
        overwrite (bool): Si True, sobrescribe archivos de reglas existentes.

    Returns:
        list[str]: Rutas de los archivos generados/actualizados.
    """
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    generados: list[str] = []

    def _escribir(ruta_rel: str, contenido: str, forzar: bool = False) -> None:
        ruta = os.path.join(target_dir, ruta_rel)
        if os.path.exists(ruta) and not (overwrite or forzar):
            logger.debug("Regla existente, se respeta: %s", ruta_rel)
            return
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        generados.append(ruta_rel)

    # 1. AGENTS.md contextual: se crea si no existe; se sobrescribe SOLO con --overwrite
    _escribir("AGENTS.md", _generar_agents_md(project_name, eco, fecha))

    # 2. Reglas por agente detectado
    if "Claude Code" in eco.ide.agentes or os.path.isdir(os.path.join(target_dir, ".claude")):
        _escribir("CLAUDE.md", _generar_claude_md(project_name, eco, fecha))

    if "Cursor" in eco.ide.ides or ".cursor" in eco.ide.reglas_existentes or ".cursorrules" in eco.ide.reglas_existentes:
        # Regla moderna de Cursor en .cursor/rules/
        _escribir(".cursor/rules/contextmap.mdc", _generar_cursor_rules(project_name, eco))
        # Regla legacy en raíz
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

    # 3. Ecosistema .hermes/ (Hermes)
    _escribir(".hermes/config.yaml", _generar_hermes_config(project_name, eco))
    _escribir(".hermes/workflows/dev-loop.md", _generar_workflow_dev_loop(project_name, eco))
    _escribir(".hermes/shields/pre-commit.md", _generar_shield_precommit(project_name, eco))
    _escribir(".hermes/triggers/post-commit.md", _generar_trigger_postcommit(project_name, eco))

    return generados

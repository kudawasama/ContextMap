"""Plantillas de reglas agénticas para el ecosistema multi-IDE.

Proporciona las funciones generadoras de contenido para archivos de reglas
y configuración de agentes (AGENTS.md, CLAUDE.md, Cursor, Windsurf, Copilot,
Gemini, Aider, Roo, OpenCode, Hermes).
"""

from __future__ import annotations

from datetime import datetime

from context_map.domain.ecosystem.detector import EcosistemaInfo

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
    """Construye el bloque de contexto del proyecto (stack detectado + verificación)."""
    test = _test_command(eco)
    build = _build_command(eco)
    langs = ", ".join(eco.stack.lenguajes) or "No detectado"
    fws = ", ".join(eco.stack.frameworks) or "No detectado"
    eps = ", ".join(eco.stack.entrypoints) or "No detectado"
    estructura = ", ".join(eco.stack.estructura) or "No detectado"

    return f"""## 🧰 Stack detectado por ContextMap (dato del proyecto)

- **Lenguaje(s)**: {langs}
- **Framework(s)**: {fws}
- **Package manager**: {eco.stack.package_manager or 'No detectado'}
- **Entrypoint(s)**: `{eps}`
- **Estructura**: {estructura}
- **Tests**: `{test}`
- **Build**: `{build}`

## ✅ Verificación obligatoria (antes de cada commit)

```bash
{test}
ctxmap refresh .          # contexto al día: scan + build (preservando manuales) + check
```

> Detalle de comandos y metodología de escritura: `.context-map/contextmap-skill.md`"""


def _generar_agents_md(project_name: str, eco: EcosistemaInfo, fecha: str) -> str:
    """Genera el contenido de AGENTS.md contextual (QUÉ + stack; el CÓMO vive en la skill)."""
    contexto = _reglas_contextuales(eco)
    return f"""# Instrucciones para Agentes de IA — {project_name}

> ⚠️ **REGLA PRIORITARIA PARA AGENTES DE IA**:
> **LEE el contexto del proyecto ANTES de investigar o modificar cualquier cosa.**
> Este proyecto se gobierna por su contexto: si no lo lees, trabajas a ciegas.
> Última actualización: {fecha}
> ⚡ Generado automáticamente por **ContextMap** — adaptado al stack real del proyecto.

Este `AGENTS.md` define **QUÉ** hacer; el **CÓMO** (comandos exactos y metodología
para escribir las notas con alma) está en
**[.context-map/contextmap-skill.md](file:///.context-map/contextmap-skill.md)**.

---

## 1. Protocolo de Inicio (QUÉ hacer antes de trabajar)

1. **Leer el Brief Ejecutivo**: `.context-map/CONTEXT.md` — responde qué es el
   proyecto, por qué existe, qué cumple, sus riesgos y tareas pendientes.
2. **Explorar el Vault**: `.context-map/vault/` o `.context-map/vault-{{project_name}}/`:
   propósito (1.0), ideas (2.0), riesgos (4.0) y backlog (5.0).
3. **Importar la historia del proyecto**: las conversaciones con el usuario también
   son contexto (comandos en la skill). Si el usuario comparte un chat, impórtalo
   ANTES de responder.
4. **Responder las 3 preguntas del alma** antes de proponer cambios:
   ¿Por qué existe este proyecto? ¿Para qué sirve? ¿Qué cumple?
5. **No Suponer Lógica**: inspecciona el código fuente antes de diagnosticar o cambiar.
6. **Captura Autónoma del Dominio**: Al inicializar o ponerse en contexto en un proyecto, el Agente debe inspeccionar los submódulos de lógica nuclear (algoritmos, ecuaciones implícitas, reglas de negocio) y documentar lo descubierto en la memoria viva (`7.0-MANUAL/DOMINIO.md` o notas del Vault), ejecutando `ctxmap refresh .` para que el proyecto quede completamente interpretado.

---

## 2. Estándares de Desarrollo (QUÉ respetar)

* **Idioma**: explicaciones, comentarios y docstrings en **Español Técnico Profesional**.
* **Clean Architecture**: Principio de Responsabilidad Única (SRP) y convención modular `modulo/submodulo/archivo.py`.
* **Tipado Fuerte**: Type Hinting explícito en Python (`List`, `Dict`, `Tuple`, `Optional`).
* **Docstrings**: documentación formal en funciones, clases y módulos.
* **Raíz Limpia**: no crear archivos sueltos en la raíz (`PLAN.md`, `NOTES.txt`).

---

{contexto}

---

## 3. Mantén Vivo el Contexto (QUÉ hacer al terminar)

El contexto es la **memoria viva del proyecto**:

1. Después de implementar, actualiza el mapa (`ctxmap refresh .`) para que refleje tu
   trabajo (nodos CAMBIO / CORRECCION / IDEA).
2. Al terminar una sesión de trabajo, importa la conversación (`import-sessions`,
   `import-antigravity`, `import-chat`) para que las decisiones y porqués queden
   registrados.
3. Un contexto que no se actualiza muere: el siguiente agente queda ciego y el
   proyecto pierde su historia.

> Comandos exactos: `.context-map/contextmap-skill.md`.

---

## 4. Contexto GLOBAL personal (multi-proyecto)

Además del vault local, el usuario mantiene una **BD personal consolidada**
(`ctxmap personal`) con eventos, lecciones y decisiones de TODOS sus
proyectos. Cuando necesites contexto histórico global (decisiones pasadas,
lecciones aprendidas, patrones), consúltala con pocos tokens (FTS5):

```bash
ctxmap personal query "términos" --limite 5
```

Complementa (no reemplaza) el vault local: con ella respondes con el
historial completo del usuario, no solo de este proyecto.

---

## 5. Convención de Commits

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
2. Explora el vault en `.context-map/vault-{project_name}/` para entender el grafo del proyecto.
3. No supongas lógica: inspecciona el código fuente antes de proponer cambios.
4. Para contexto histórico global (otros proyectos): `ctxmap personal query "términos" --limite 5` (BD personal FTS5, pocos tokens).

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
- **Contexto global**: `ctxmap personal query "términos"` para recuperar historial de otros proyectos (BD FTS5, pocos tokens).
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
- Usa convenciones del proyecto: docstrings en español, type hints strictly.

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

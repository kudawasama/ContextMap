# Context Map

**Mapa mental narrativo de proyectos para agentes de IA**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ¿Qué es?

Context Map crea un **Vault de Obsidian** interconectado con el contexto narrativo y técnico completo de tu proyecto: qué es, por qué existe, qué riesgos afronta, qué funcionalidades están implementadas o pendientes, y qué decisiones de arquitectura se han tomado.

No es un simple generador de documentación. Es un sistema que captura el **alma del proyecto** y establece **gobernanza automática para Agentes de IA** (`Antigravity`, `Cursor`, `Claude`, `Hermes`, `Copilot`, etc.).

---

## 🚀 ¿Cómo Inicializar ContextMap en un Proyecto Nuevo?

Tienes dos formas de inicializar y poner en contexto un proyecto:

En cualquier sesión de chat con tu Agente de IA en el IDE, simplemente escríbele:

> **"Inicializa ContextMap para este proyecto"**

**¿Qué hace el Agente automáticamente?**

1. Ejecuta el escaneo y construcción profunda (`ctxmap scan .` && `ctxmap build --clean --brief`).
2. Genera las reglas de gobernanza en `AGENTS.md` y el resumen ejecutivo en `.context-map/CONTEXT.md`.
3. Lee los archivos generados y queda **100% en contexto** de la arquitectura, métricas, riesgos y tareas pendientes del proyecto en esa misma respuesta.

---

### 💻 Opción 2: Desde la Terminal

Si estás trabajando directamente en consola o automatizando un script:

```bash
# Modo All-in-One: Escaneo + Ingesta Git + Reconstrucción limpia en 1 solo paso
ctxmap auto .
```

---

## 🧠 Metodología: Contexto Narrativo con Alma

Context Map enriquece cada nota del Vault con un formato narrativo polimórfico especializado según su tipo semántico:

- 💡 **IDEAS**: ¿Por qué?, ¿De dónde surgió?, ¿Para qué?, ¿Cómo?, y tabla de **Pros y Contras**.
- ⚠️ **RIESGOS**: ¿Qué riesgo es?, ¿Dónde se ubica?, Impacto, Mitigación y **Matriz de Gravedad**.
- 🔧 **CAMBIOS / CORRECCIONES**: ¿Qué se modificó?, Razón del cambio, Archivos y **Verificación de No-Regresión**.
- 📄 **DOCUMENTOS**: Síntesis extractiva, concepto dominante y **citas referenciadas** del documento ingerido.
- 📦 **BASE**: Componente estructural, **Rol en la Arquitectura** e integraciones clave.
- 🧪 **PRUEBAS**: Funcionalidad validada, **Criterios de Aceptación** y comando `pytest`.
- 📝 **FUTURO**: Tarea pendiente, ubicación en código y **Prioridad de implementación**.
- 🎯 **HITO**: Versión, hito de lanzamiento o milestone alcanzado.

---

## 🏛️ Gobernanza Automática de Agentes (`AGENTS.md`)

Al ejecutar `ctxmap build --brief` o `ctxmap init`, ContextMap genera automáticamente un archivo `AGENTS.md` en la raíz del proyecto objetivo. Este documento impone las normas obligatorias para cualquier modelo de IA:

- **Español Técnico Profesional**: Todas las interacciones, explicaciones y docstrings.
- **Documentación Formal**: Google Style / PEP 257 en todas las funciones y clases.
- **Type Hinting Estricto**: Tipado fuerte en Python.
- **Arquitectura Limpia**: Separación de capas en `core/`, `domain/`, `application/`, `infrastructure/` y `presentation/`.
- **Topología Obsidian Limpia**: Grafo en árbol estricto de 3 niveles sin ciclos rotos.
- **Verificación Mandatoria**: Ejecución previa de `pytest`, `ctxmap scan` y `ctxmap build`.

---

## 📊 Topología Estricta en Estrella para Obsidian (Graph View)

Context Map organiza el Vault jerárquicamente en **3 niveles** para garantizar una vista de grafo visualmente deslumbrante en Obsidian:

```Architecture
.context-map/vault/
├── 00-INDICE.md                          # Nivel 0: Dashboard central MOC
├── 1.0-PROYECTO/                         # Nivel 1: Identidad y Visión
├── 2.0-IDEAS/                            # Nivel 1: Sub-clúster por estado
│   ├── 2.1-Ideas-Pendientes/             # Nivel 2: Tareas y TODOs sin implementar
│   ├── 2.2-Ideas-Futuras/                # Nivel 2: Roadmap e iniciativas activas
│   ├── 2.3-Ideas-Completas/              # Nivel 2: Funciones, clases y módulos en código
│   └── 2.4-Ideas-Relevantes/             # Nivel 2: Propuestas clave
├── 3.0-ESTRUCTURA/                       # Nivel 1: Componentes BASE y arquitectura
├── 4.0-RIESGOS/                          # Nivel 1: Alertas y matrices de gravedad
├── 5.0-BACKLOG/                          # Nivel 1: Tareas y sprint backlog
└── 6.0-HISTORIAL/                        # Nivel 1: Commits, cambios y correcciones
```

> **Sincronización Multi-Vault**: Cualquier regeneración con `build` actualiza simultáneamente todas las carpetas `vault*` dentro de `.context-map/` para reflejar cambios en tiempo real en Obsidian.

---

## Comparativa: Otros vs Context Map

| Característica | Otros | Context Map |
| ---------------- | :-----: | :-----------: |
| Escaneo técnico de archivos | ✅ | ✅ |
| Briefs para agentes (`CONTEXT.md`) | ✅ | ✅ |
| Gobernanza automática para Agentes (`AGENTS.md`) | ❌ | ✅ |
| Score de readiness del proyecto | ✅ | ✅ |
| Diagramas Mermaid dinámicos | ✅ | ✅ |
| Vault Obsidian con Graph View limpia de 3 niveles | ❌ | ✅ |
| Sub-clústeres por estado (Completado/Pendiente/Futuro) | ❌ | ✅ |
| Sanitización contra caracteres nulos (`NUL \x00`) en Windows | ❌ | ✅ |
| Wiki-links `[[entre-notas]]` | ❌ | ✅ |
| Tags YAML Frontmatter estandarizados | ❌ | ✅ |
| Captura "por qué" y "para qué" del proyecto | ❌ | ✅ |
| Sync incremental inteligente (sin duplicados) | ❌ | ✅ |
| Importador de chats de Antigravity IDE / Hermes / Telegram | ❌ | ✅ |
| Multi-Vault Real-Time Sync | ❌ | ✅ |

---

## Instalación

```bash
# Instalar globalmente con pip
pip install -e .

# O instalar con UV (recomendado)
uv tool install git+https://github.com/kudawasama/ContextMap.git
```

---

## Lista Completa de Comandos

```bash
# Escaneo e inicialización
ctxmap init                           # Inicializa la estructura del proyecto
ctxmap scan .                         # Escanea el código y genera nodos semánticos

# Construcción del Vault y Briefs
ctxmap build                          # Reconstruye el Vault consolidado
ctxmap build --clean                  # Limpia notas previas y regenera desde cero
ctxmap build --brief                  # Genera CONTEXT.md y AGENTS.md
ctxmap build --clean --brief          # Construcción limpia completa (Recomendado)

# Importadores
ctxmap import-git .                   # Importa historial de commits recientes
ctxmap import-sessions                # Importa sesiones de Hermes Agent
ctxmap import-antigravity             # Importa conversaciones de Antigravity IDE
ctxmap import-chat telegram.txt       # Importa chats de Telegram, Discord o Slack

# Ingesta de documentos externos (segundo cerebro / LLM Wiki style)
ctxmap ingest docs/                   # Ingiere MD/TXT/PDF → nodos DOCUMENTO (3.2-DOCUMENTOS)
ctxmap ingest carta.pdf --brief       # Ingiere un archivo y regenera el brief

# Adaptación al ecosistema agéntico
ctxmap adapt .                        # Detecta stack + IDE y genera reglas por agente
ctxmap adapt . --overwrite            # Fuerza sobrescritura de reglas existentes

# Cobertura de agentes: AGENTS.md (universal), CLAUDE.md (Claude Code),
# .cursorrules + .cursor/rules (Cursor), .windsurfrules (Windsurf),
# .clinerules (Cline), .roo/rules (Roo Code), GEMINI.md (Gemini CLI),
# opencode.json (OpenCode), .aider.conf.yml (Aider),
# .github/copilot-instructions.md (Copilot), .hermes/ (Hermes)

# Diagnóstico y Mantenimiento
ctxmap check .                        # Verifica la preparación (readiness) del sistema
ctxmap update                         # Actualiza ContextMap a la última versión de GitHub
```

---

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md)

---

## Licencia

MIT - Ver [LICENSE](LICENSE)

---

**Creado por [kudawasama](https://github.com/kudawasama)**

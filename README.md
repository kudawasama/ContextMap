# 🗺️ ContextMap

<div align="center">

**Mapa mental narrativo de proyectos para agentes de IA**

*Captura el alma de tu proyecto, establece gobernanza automática y mantiene vivo el contexto para cualquier Agente de IA (`Antigravity`, `Cursor`, `Claude`, `Hermes`, `Copilot`, `Windsurf`, `Gemini`).*

[![Release](https://img.shields.io/badge/version-v1.7.0-blue.svg?style=for-the-badge)](https://github.com/kudawasama/ContextMap)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Readiness](https://img.shields.io/badge/Readiness-100%2F100-brightgreen.svg?style=for-the-badge)](file:///.context-map/CONTEXT.md)
[![MCP Powered](https://img.shields.io/badge/MCP-9%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)

[🚀 Inicio Rápido](#-inicio-rápido) • [✨ Características Clave](#-características-clave) • [🏛️ Gobernanza Multi-IDE](#️-gobernanza-multi-ide) • [🔌 Servidor MCP](#-servidor-mcp-ctxmap-mcp) • [📊 Vault & Obsidian](#-vista-de-grafo-y-vault-obsidian) • [💻 Comandos CLI](#-lista-completa-de-comandos)

</div>

---

## 💡 ¿Qué es ContextMap y por qué existe?

Cuando trabajas con Agentes de IA en tu IDE (`Antigravity`, `Cursor`, `Claude Code`, `Copilot`, etc.), la IA suele olvidar las decisiones del pasado, desconocer las reglas inamovibles o proponer refactorizaciones a ciegas que rompen la arquitectura.

**ContextMap resuelve esto creando una memoria viva del proyecto:**
Construye una bóveda interconectada en **Obsidian** ([Graph View en Árbol Estricto](file:///.context-map/vault-ContextMap/)) y un Brief Ejecutivo ([`CONTEXT.md`](file:///.context-map/CONTEXT.md)) que le enseñan a cualquier Agente de IA:
- **¿Por qué existe el proyecto?** (Propósito, negocio e identidad).
- **¿Qué riesgos afronta?** (Complejidad estática, alertas y zonas sensibles).
- **¿Qué está implementado vs. pendiente?** (Grafo desduplicado de ideas, bases y cambios).
- **¿Qué decisiones de arquitectura se han tomado?** (Memoria viva de conversaciones pasadas e historias de commit).

> 🚫 **No es un simple generador de documentación pasiva.** Es un sistema vivo de **Gobernanza Agéntica**, **Memoria Permanente** y **Readiness**.

---

## ⚡ Inicio Rápido en 10 Segundos

### 1. Instalación Global (con `uv`)

```bash
# Recomendado: instalación directa en 1 comando (requiere https://docs.astral.sh/uv/)
uv tool install git+https://github.com/kudawasama/ContextMap.git

# O con pip desde un clon local:
# git clone https://github.com/kudawasama/ContextMap.git && cd ContextMap && pip install -e .
```

### 2. Poner en Contexto un Proyecto

En cualquier chat con tu Agente de IA dentro de tu IDE, dile:

> 💬 **"Inicializa ContextMap para este proyecto"**

O ejecútalo directamente en la consola de tu repositorio:

```bash
# Inicialización automática completa en 1 paso:
ctxmap auto .

# Día a día: mantén el contexto al día tras hacer cambios:
ctxmap refresh .
```

---

## ✨ Características Clave

### 🧠 1. Contexto Narrativo con Alma
Cada nota del vault se enriquece automáticamente con una estructura narrativa según su rol semántico:
* 💡 **IDEAS**: Por qué surgió, lógica, propuesta de mejora y matriz de **Pros & Contras**.
* ⚠️ **RIESGOS**: Ubicación, nivel de gravedad, impacto de ignorarlo y **Estrategia de Mitigación**.
* 🔧 **CAMBIOS Y CORRECCIONES**: Razón del cambio, componentes afectados y **Verificación de No-Regresión**.
* 📦 **BASE**: Rol estructural en la arquitectura e integraciones clave.
* 🧪 **PRUEBAS**: Funcionalidad validada, criterios de aceptación y comando `pytest`.
* 📄 **DOCUMENTOS**: Ingesta extractiva de PDFs, Markdown y textos con citas referenciadas.

### 🔌 2. Servidor MCP Nativo (Model Context Protocol)
Expone **9 herramientas MCP** nativas vía stdio (`ctxmap mcp`) para que agentes compatibles como **Hermes Agent**, **Claude Desktop** o **Cursor** ejecuten `refresh`, `scan`, `build`, `check` o `context` directamente sin shell:

```bash
# Conectar a Hermes Agent:
hermes mcp add ctxmap --command ctxmap --args mcp
```

### 🛡️ 3. Zona Protegida y Memoria Viva (`7.0-MANUAL/` & `8.0-KNOWLEDGE/`)
* **`7.0-MANUAL/`**: Alberga notas de sesión, diarios (`Diario/YYYY-MM-DD.md`) y acuerdos sostenidos con el usuario. El motor de build **jamás las borra** (`preserve: true`).
* **`8.0-KNOWLEDGE/`**: Aprendizajes accionables reutilizables documentados por la IA: Lección · Cómo se resolvió · Prompt específico · Instrucción previa · Conexiones.

### 📦 4. Base de Datos Personal Consolidada Multi-Proyecto (`ctxmap personal`)
Consolida en un único archivo **SQLite + FTS5** (`~/.context-map/personal/personal.db`) todos los eventos, lecciones y decisiones de **todos** tus proyectos, transportable en pendrive o Google Drive:

```bash
ctxmap personal sync --todos      # Sincroniza todos tus repositorios
ctxmap personal query "términos"  # Búsqueda ultra-rápida full-text (pocos tokens)
```

---

## 🏛️ Gobernanza Multi-IDE

ContextMap genera e inyecta reglas contextuales específicas para el stack de tu proyecto adaptadas a más de 10 herramientas de IA:

| Agente / IDE | Archivo de Reglas Generado |
| :--- | :--- |
| **Estándar Universal** | [`AGENTS.md`](file:///AGENTS.md) |
| **Claude Code** | `CLAUDE.md` |
| **Cursor** | `.cursor/rules/contextmap.mdc` y `.cursorrules` |
| **Windsurf** | `.windsurfrules` |
| **GitHub Copilot** | `.github/copilot-instructions.md` |
| **Gemini CLI** | `GEMINI.md` |
| **Hermes Agent** | `.hermes/config.yaml` + Workflows |
| **Cline & Roo Code** | `.clinerules` / `.roo/rules/contextmap.md` |
| **OpenCode & Aider** | `opencode.json` / `.aider.conf.yml` |

---

## 📊 Vista de Grafo y Vault Obsidian

ContextMap organiza la bóveda bajo una **Topología Estricta en Árbol** que garantiza un Graph View limpio en Obsidian:

```
.context-map/vault-ContextMap/
├── 00-INDICE.md                          # Dashboard central MOC (Nivel 0)
├── 1.0-PROPOSITO/                        # Propósito, valor y límites
├── 2.0-IDEAS/                            # Ideas agrupadas por concepto y estado
│   ├── 2.1-Ideas-Pendientes/             # Tareas pendientes por implementar
│   ├── 2.2-Ideas-Futuras/                # Roadmap e iniciativas activas
│   └── 2.3-Ideas-Completas-e-Implementadas/ # Ideas validadas en código
├── 3.0-ESTRUCTURA/                       # Componentes base y fundamentos
├── 4.0-RIESGOS/                          # Matrices de gravedad y zonas de complejidad
├── 5.0-BACKLOG/                          # Sprint backlog
├── 6.0-HISTORIAL/                        # Historial de commits y cambios
├── 7.0-MANUAL/                           # Zona protegida: Diario y backlog manual
└── 8.0-KNOWLEDGE/                        # Zona protegida: Aprendizajes del agente
```

---

## 🏗️ Arquitectura del Sistema (Clean Architecture)

El código fuente de ContextMap está estructurado bajo principios estrictos de desacoplamiento y modularidad:

```
context_map/
├── core/                        # Dominio fundamental
│   ├── models/                  # Dataclasses (Node, Edge, Event)
│   ├── normalization/           # Estandarización semántica (mappings, inference, cleaning)
│   ├── parsing/                 # Parser de eventos y deserializador JSONL
│   ├── storage/                 # Persistencia JSONL y snapshots
│   └── generators/              # Generadores narrativos y de alma
├── domain/                      # Lógica de negocio
│   ├── scanning/                # Escáner estático AST y detectores
│   ├── synchronization/         # Sincronización incremental del grafo
│   ├── ingestion/               # Ingesta de Markdown, TXT y PDFs
│   ├── ecosystem/               # Adaptador agéntico (rules_templates)
│   ├── analysis/                # Evaluador de Readiness (check 0-100)
│   └── health/                  # Diagnóstico y mantenimiento (doctor)
├── application/                 # Orquestación y CLI
│   ├── cli/                     # Parser de argumentos CLI
│   └── commands/                # Comandos (refresh, build, scan, personal, wrap)
├── infrastructure/              # Integraciones externas
│   ├── integrations/            # Git, Hermes, Antigravity, MCP Server
│   └── analyzers/               # Analizadores estáticos AST
└── presentation/                # Generación visual del Vault
    ├── vault/                   # Generador de Vault Obsidian (atomic, consolidated, notas_ideas)
    └── briefs/                  # Generador de CONTEXT.md para Agentes
```

---

## 💻 Lista Completa de Comandos CLI

```bash
# 🚀 Día a día (recomendado): mantén el contexto al día en 1 solo paso
ctxmap refresh .                      # scan + build (preservando manuales) + check

# 🔄 Cierre de sesión de trabajo
ctxmap wrap                           # refresh + resumen de memoria viva registrada

# 🤖 Servidor MCP
ctxmap mcp                            # Arranca el servidor MCP stdio

# 📦 Base de datos personal multi-proyecto
ctxmap personal sync --todos          # Sincroniza todos los repositorios locales
ctxmap personal query "términos"      # Búsqueda full-text en tu histórico

# 🛠️ Construcción y Escaneo
ctxmap auto .                         # Escaneo completo + ingesta git + build
ctxmap build                          # Reconstruye el Vault Obsidian
ctxmap build --brief                  # Genera CONTEXT.md y AGENTS.md
ctxmap check .                        # Audita el Readiness Score (0-100)

# 📥 Importadores de Historia
ctxmap import-git .                   # Importa commits de Git
ctxmap import-sessions                # Importa sesiones de Hermes Agent
ctxmap import-antigravity             # Importa conversaciones de Antigravity IDE
ctxmap import-chat export.jsonl       # Importa chats de Telegram, Discord o Slack
ctxmap ingest documento.pdf           # Ingiere PDFs/Markdown al vault

# 🧰 Adaptación Agéntica
ctxmap adapt .                        # Genera reglas agénticas respetando existentes
ctxmap adapt . --merge               # Anexa el bloque ContextMap preservando reglas del usuario
```

---

## ⚖️ Comparativa: ContextMap vs Otros Generadores

| Característica | Otros Generadores | ContextMap |
| :--- | :---: | :---: |
| Escaneo técnico de archivos | ✅ | ✅ |
| Resumen ejecutivo para IA (`CONTEXT.md`) | ✅ | ✅ |
| Gobernanza multi-IDE automática (`AGENTS.md`) | ❌ | **✅** |
| Score de Readiness del Proyecto (0-100) | ❌ | **✅** |
| Servidor MCP nativo con 9 Tools (`ctxmap mcp`) | ❌ | **✅** |
| Vault Obsidian con Graph View en Árbol Púro | ❌ | **✅** |
| Sub-clústeres por estado (Completadas/Pendientes/Futuras) | ❌ | **✅** |
| Captura del "Por qué" y "Para qué" (Notas con Alma) | ❌ | **✅** |
| Zona Protegida Indestructible (`7.0-MANUAL/` & `8.0-KNOWLEDGE/`) | ❌ | **✅** |
| Base de Datos Personal Consolidada Multi-Proyecto | ❌ | **✅** |
| Comando único de sincronización diaria (`ctxmap refresh .`) | ❌ | **✅** |

---

## 📄 Licencia

Este proyecto está bajo la Licencia **MIT** — consulta el archivo [LICENSE](LICENSE) para más detalles.

---

<div align="center">

**Creado con ❤️ por [kudawasama](https://github.com/kudawasama)**

</div>

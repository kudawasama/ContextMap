# 🗺️ ContextMap

<div align="center">

**Mapa mental narrativo de proyectos para agentes de IA**

[![English Version](https://img.shields.io/badge/Read_in-English_🇬🇧-0052CC?style=for-the-badge&logo=googletranslate&logoColor=white)](README_EN.md)
[![Versión en Español](https://img.shields.io/badge/Versión_en-Español_🇪🇸-D00000?style=for-the-badge&logo=googletranslate&logoColor=white)](README.md)

*Captura el alma de tu proyecto, establece gobernanza automática y mantiene vivo el contexto para cualquier Agente de IA (`Antigravity`, `Cursor`, `Claude`, `Hermes`, `Copilot`, `Windsurf`, `Gemini`).*

[![Release](https://img.shields.io/badge/version-v2.0.0-blue.svg?style=for-the-badge)](https://github.com/kudawasama/ContextMap)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Readiness](https://img.shields.io/badge/Readiness-100%2F100-brightgreen.svg?style=for-the-badge)](file:///.context-map/CONTEXT.md)
[![MCP Powered](https://img.shields.io/badge/MCP-11%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)

[🚀 Inicio Rápido](#-inicio-rápido-en-10-segundos) • [✨ Características Clave](#-características-clave) • [🤖 Auto-Mantenimiento](#-auto-mantenimiento-autónomo-v190) • [⚖️ Comparativa](#️-comparativa-funcional-contextmap-vs-herramientas-top-del-mercado) • [📜 Historial de Versiones](#-historial-de-versiones-releases) • [💻 Comandos CLI](#-lista-completa-de-comandos-cli)

</div>

> 🇬🇧 **English Speaker?** Click the **`Read in English 🇬🇧`** badge above or read the full English documentation at 👉 [**README_EN.md**](README_EN.md).

---

<details>
<summary><b>🇬🇧 English Speaker? Click here for a quick summary or read the full English documentation!</b></summary>

### 🗺️ ContextMap — Narrative Mental Map for AI Agents
ContextMap creates an interconnected **Obsidian Vault** and **AI Executive Brief (`CONTEXT.md`)** to manage context, multi-IDE rules, living memory, and autonomous self-maintenance for your software projects across agents like `Antigravity`, `Cursor`, `Claude Code`, `Copilot`, `Hermes`, and `Gemini`.

- 📖 **Full English Documentation:** See [**README_EN.md**](README_EN.md)
- ⚡ **Quick Install:** `uv tool install git+https://github.com/kudawasama/ContextMap.git`
- 💬 **Initialize:** Tell your AI Agent: *"Initialize ContextMap for this project"* or run `ctxmap auto .`
</details>

---

## 💡 ¿Qué es ContextMap y por qué existe?

Cuando trabajas con Agentes de IA en tu IDE (`Antigravity`, `Cursor`, `Claude Code`, `Copilot`, etc.), la IA suele olvidar las decisiones del pasado, desconocer las reglas inamovibles o proponer refactorizaciones a ciegas que rompen la arquitectura.

**ContextMap resuelve esto creando una memoria viva del proyecto:**
Construye una bóveda interconectada en **Obsidian** ([Graph View en Árbol Estricto](file:///.context-map/vault-ContextMap/)) y un Brief Ejecutivo ([`CONTEXT.md`](file:///.context-map/CONTEXT.md)) que le enseñan a cualquier Agente de IA:
- **¿Por qué existe el proyecto?** (Propósito, negocio e identidad).
- **¿Qué riesgos afronta?** (Complejidad estática, alertas y zonas sensibles).
- **¿Qué está implementado vs. pendiente?** (Grafo desduplicado de ideas, bases y cambios).
- **¿Qué decisiones de arquitectura se han tomado?** (Memoria viva de conversaciones pasadas e historias de commit).

> 🚫 **No es un simple generador de documentación pasiva.** Es un sistema vivo de **Gobernanza Agéntica**, **Memoria Permanente**, **Readiness** y **Auto-Mantenimiento Autónomo**.

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

### 🤖 2. Auto-Mantenimiento Autónomo (v1.9.0)
* 🏥 **Self-Healing (`ctxmap doctor --fix`)**: Diagnostica y auto-repara inconsistencias de vaults, fragmentación de nombres de proyecto y metadatos sin perder notas manuales.
* 👀 **Watcher Daemon (`ctxmap watch .`)**: Proceso en segundo plano que escucha cambios en el código (`.py`, `.md`, `.json`, etc.) y aplica parches incrementales desbouncheados (500ms).
* ⚓ **Git Hooks Transparentes (`ctxmap hook install`)**: Inyecta scripts `pre-commit` y `post-commit` para sincronizar el mapa y el brief en cada commit.

### 🔌 3. Servidor MCP Nativo (11 Tools stdio)
Expone **11 herramientas MCP** nativas vía stdio (`ctxmap mcp`) para que agentes compatibles como **Hermes Agent**, **Claude Desktop** o **Cursor** ejecuten `refresh`, `scan`, `build`, `check`, `doctor` o `install_hooks` directamente sin shell:

```bash
# Conectar a Hermes Agent:
hermes mcp add ctxmap --command ctxmap --args mcp
```

### 🛡️ 4. Zona Protegida y Memoria Viva (`7.0-MANUAL/` & `8.0-KNOWLEDGE/`)
* **`7.0-MANUAL/`**: Alberga notas de sesión, diarios (`Diario/YYYY-MM-DD.md`) y acuerdos sostenidos con el usuario. El motor de build **jamás las borra** (`preserve: true`).
* **`8.0-KNOWLEDGE/`**: Aprendizajes accionables reutilizables documentados por la IA: Lección · Cómo se resolvió · Prompt específico · Instrucción previa · Conexiones.

### 📦 5. Base de Datos Personal Consolidada Multi-Proyecto (`ctxmap personal`)
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

## ⚖️ Comparativa Funcional: ContextMap vs Herramientas Top del Mercado

En el ecosistema de herramientas de contexto para IA (2026), existen 4 soluciones populares. A continuación se compara **ContextMap** frente a las alternativas web y CLI más utilizadas:

| Característica / Capacidad | Concatenadores CLI (`Repomix`) | Ingestores Web (`Gitingest`) | Repo Maps (`Aider`) | Indexadores IDE (`Cursor` / `Windsurf`) | **ContextMap v1.9.0** |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Enfoque Principal** | Dump a archivo XML/MD | URL GitHub a prompt | Mapa AST + PageRank | RAG Vectorial local | **Gobernanza + Memoria Viva + Vault + Auto-Mantenimiento** |
| **Consumo de Tokens** | 🔴 Masivo (repos entero) | 🔴 Masivo | 🟢 Eficiente | 🟡 Medio | 🟢 **Ultra-eficiente (`CONTEXT.md` / MCP)** |
| **Bóveda Visual Interactiva (Obsidian Vault)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (Grafo en árbol estricto, Canvas, Dataview)** |
| **Captura del "Por Qué" y "Para Qué" (Alma)** | ❌ No (solo código) | ❌ No | ❌ No (solo firmas) | ❌ No | **✅ Sí (Notas narrativas polimórficas)** |
| **Gobernanza Multi-IDE (`AGENTS.md` + 10 IDEs)** | ❌ No | ❌ No | ❌ No | 🟡 Solo propio IDE | **✅ Sí (Portable entre 10+ IDEs)** |
| **Memoria Viva Indestructible (`7.0-MANUAL/`)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (`preserve: true`, jamás se borra)** |
| **Aprendizaje del Agente (`8.0-KNOWLEDGE/`)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (Formato de lecciones accionables)** |
| **Servidor MCP Nativo (stdio)** | ❌ No | ❌ No | ❌ No | 🟡 Propietario | **✅ Sí (`ctxmap mcp`, 11 Tools stdio)** |
| **Base de Datos Personal Multi-Proyecto** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (SQLite + FTS5 transportable)** |
| **Readiness Index del Sistema (Score 0-100)** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (`ctxmap check .`)** |
| **Conteo Exacto de Tokens por Modelo** | ✅ Sí (`tiktoken`) | 🟡 Aproximado | ❌ No | 🟡 Interno | **✅ Sí (`tiktoken` + fallback)** |
| **Escáner Preventivo de Secretos / Credenciales** | ✅ Sí | ❌ No | ❌ No | ❌ No | **✅ Sí (`security.py`)** |
| **Exportación Portable XML/JSON/Markdown** | ✅ Sí | ✅ Sí | ❌ No | ❌ No | **✅ Sí (`ctxmap export`)** |
| **Daemon Watcher de Monitoreo Activo** | ❌ No | ❌ No | ❌ No | ✅ Sí (Background) | **✅ Sí (`ctxmap watch .`)** |
| **Self-Healing y Auto-Reparación de Vault** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (`ctxmap doctor --fix`)** |
| **Instalador Transparente de Git Hooks** | ❌ No | ❌ No | ❌ No | ❌ No | **✅ Sí (`ctxmap hook install`)** |

### 🔍 ¿Por qué ContextMap es superior a la competencia?
* **Repomix & Gitingest:** Útiles para volcar un archivo plano de texto o copiar un repo de GitHub a un chat web, pero consumen presupuestos masivos de tokens y carecen de memoria de decisiones pasadas.
* **Aider Repo Map:** Excelente para el CLI de Aider extrayendo firmas sintácticas, pero no genera documentación visual para humanos ni guarda el trasfondo de decisiones conversadas.
* **Indexadores de Cursor / Windsurf:** Indizan vectores en su propio entorno cerrado, perdiendo todo el contexto si cambias de agente o IDE.
* **ContextMap:** Unifica la **Gobernanza Agéntica Universal**, la **Memoria Viva Indestructible**, el **Auto-Mantenimiento Autónomo** y una **Bóveda Obsidian Interconectada**, garantizando que tu proyecto mantenga su historia e identidad en cualquier IDE o modelo.

---

## 📜 Historial de Versiones (Releases)

Para consultar el historial completo de versiones, cambios, notas de release y novedades desde la v1.0.0 hasta la **v1.9.0**, por favor revisa el archivo [**CHANGELOG.md**](CHANGELOG.md).

---

## 💻 Lista Completa de Comandos CLI

```bash
# 🚀 Día a día (recomendado): mantén el contexto al día en 1 solo paso
ctxmap refresh .                      # scan + build (preservando manuales) + check

# 👀 Monitoreo en segundo plano
ctxmap watch .                        # Daemon escuchador de cambios en tiempo real

# 🏥 Diagnóstico y Self-Healing
ctxmap doctor . --fix                 # Diagnostica y auto-repara el proyecto y el vault

# ⚓ Instalación de Git Hooks
ctxmap hook install                   # Inyecta pre-commit y post-commit transparentes

# 🔄 Cierre de sesión de trabajo
ctxmap wrap                           # refresh + resumen de memoria viva registrada

# 📦 Exportación de Contexto Portable (Repomix compatible)
ctxmap export . --format xml          # Exporta contexto plano en XML, JSON o Markdown

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

## 📄 Licencia

MIT © [kudawasama](https://github.com/kudawasama)

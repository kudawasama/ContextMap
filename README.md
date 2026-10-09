# 🗺️ ContextMap

<div align="center">

# La memoria permanente para tus asistentes de IA

### *Que tu IA no olvide tus decisiones, no queme tokens y no rompa tu código.*

[![Release](https://img.shields.io/badge/version-v2.13.0-blue.svg?style=for-the-badge)](CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/context-map-ai.svg?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/context-map-ai/)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![Tests](https://img.shields.io/badge/tests-410%20passing-brightgreen.svg?style=for-the-badge)](context_map/__tests__/)
[![Type Check: Strict MyPy](https://img.shields.io/badge/mypy-100%25%20strict-00599C.svg?style=for-the-badge&logo=python&logoColor=white)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

[English version 🇬🇧](README_EN.md) · [Documentación técnica 🏛️](README_TECNICO.md) · [Historial de versiones](CHANGELOG.md)

</div>

---

## El problema: cada chat empieza de cero

Si programas con **Cursor, Claude Code, Copilot, ChatGPT, Antigravity, Windsurf o Hermes**, esto te resulta familiar:

| Síntoma | Qué cuesta |
|---|---|
| 🧠 **Amnesia entre sesiones** | Vuelves a explicar el proyecto desde cero en cada chat. |
| 💸 **Contexto quemado** | Pegar 100 archivos satura la ventana, encarece cada respuesta y confunde al modelo. |
| 💥 **Refactors a ciegas** | La IA cambia código que funcionaba porque no conoce las decisiones ni las reglas de negocio. |
| 🔒 **Dependencia del editor** | Si cambias de IDE, pierdes todo el contexto acumulado. |

---

## La solución: un disco duro de memoria viva para tus IAs

**ContextMap** escanea tu proyecto, entiende su estructura y su propósito, y produce **dos artefactos portables** que cualquier agente puede leer:

1. 🗺️ **Una bóveda de Obsidian** — el mapa mental del proyecto: ideas, decisiones, riesgos y su historia, navegable como un grafo.
2. 📄 **Un brief ejecutivo (`CONTEXT.md`)** — un resumen de alta densidad. La capa mínima pesa **~700 tokens** e incluye identidad, estado, riesgos y pendientes.

> **Principio de diseño:** *el script propone, el agente dispone*. ContextMap no "adivina" tu proyecto: genera el borrador, y el agente lo revisa y lo humaniza. El contexto solo se da por bueno cuando alguien lo ha verificado.

```
                    TU PROYECTO
                         │
                 ctxmap refresh .
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 🗺️ Bóveda Obsidian              📄 Brief (CONTEXT.md)
 (grafo navegable +             (~700 tk con la capa
  memoria manual)                mínima; cacheable)
        └────────────────┬────────────────┘
                         ▼
      🤖 Cualquier agente: Cursor · Claude · Copilot ·
         Antigravity · Windsurf · Hermes · pi (MCP)
```

---

## Cómo funciona (4 etapas)

| Etapa | Comando | Qué hace |
|---|---|---|
| **1. Escanear** | `ctxmap scan .` | Analiza estructura, símbolos y cambios → eventos (idea, riesgo, cambio, base…). |
| **2. Sintetizar** | `ctxmap build --brief` | Escribe el grafo y la bóveda, y genera el brief para agentes. |
| **3. Servir** | `ctxmap mcp` | Expone **30 herramientas MCP** para que el agente consulte la memoria sin leer archivos. |
| **4. Revisar y adaptar** | `ctxmap check .` · `ctxmap adapt` | Audita la salud del contexto y genera las reglas nativas de cada IDE. |

Todo en un paso:

```bash
ctxmap refresh .     # = scan + build (preservando tus notas) + check + revisión de reglas
```

---

## Inicio rápido

### 1. Instalar

```bash
pip install context-map-ai            # o: uv tool install context-map-ai
```

Con el servidor MCP para agentes:

```bash
pip install "context-map-ai[mcp]"
```

### 2. Inicializar el proyecto

```bash
ctxmap auto .
```

```text
[auto] Proyecto: Mi-Tienda-Online
[auto] Stack detectado: Python 3.12 · FastAPI · pytest
[auto] Ecosistema: Cursor, Claude Code, GitHub Copilot
[auto]         + AGENTS.md · .cursor/rules/contextmap.mdc · .github/copilot-instructions.md
[auto] Vault: .context-map/vault-Mi-Tienda-Online/  (312 notas)
[auto] Brief: .context-map/CONTEXT.md  (1.852 tk → 695 tk con la capa mínima)
[auto] Readiness: 100/100 — ready
```

### 3. Mantenerlo al día

Cada vez que avances:

```bash
ctxmap refresh .
```

---

## Ejemplos reales

### 🧠 Ejemplo 1 — La IA recuerda la decisión de ayer

Anoche acordaste: *«usamos SQLite + FTS5, no embeddings, para la búsqueda personal»*.
Lo dejaste en tu diario (`.context-map/vault-*/7.0-MANUAL/Diario/`), que el build **nunca borra**.

Hoy, en un chat nuevo, la IA pide el brief y **ya lo sabe**:

```text
ctxmap search "por qué no usamos embeddings"
```

```text
[search] 3 pasaje(s) para: por qué no usamos embeddings

1. [NOTA] Diario — 2026-10-07
   cita: .context-map/vault-MiApp/7.0-MANUAL/Diario/2026-10-07.md
   …se descartaron embeddings pesados; SQLite+FTS5 ya cubre la búsqueda personal y no añade dependencias…

2. [NOTA] Plan de Revisión (mediciones)
   cita: .context-map/vault-MiApp/7.0-MANUAL/MEJORAS/PLAN-REVISION.md
   …el peso estaba en copias de texto sin retención, no en el almacenamiento…
```

> El resultado trae **citas** al archivo real: la IA puede profundizar solo en lo que necesita, en vez de leer carpetas enteras.

### 🔎 Ejemplo 2 — Recuperar contexto sin leer 100 archivos

```text
ctxmap search "retención de snapshots"
```

Devuelve los 5 fragmentos más afines **con su cita**, en lugar de volcar el repositorio. Ese es el ahorro: el agente pide un pasaje, no un proyecto.

### 🌐 Ejemplo 3 — Todos tus proyectos, de un vistazo

```bash
ctxmap personal panorama
```

```text
============================================================================
🌐 PANORAMA MULTI-PROYECTO
============================================================================
Proyecto               Semáforo   Inactivo   Eventos  Lecc/Dec   Sesiones
----------------------------------------------------------------------------
Mi-Tienda-Online       🟢 Activo   1d         582      4/2        3
App-Finanzas           🟢 Activo   5d         336      4/0        1
Bot-Automatizacion     🟡 Tibio    21d        32       2/1        0
----------------------------------------------------------------------------
```

Las lecciones y decisiones se consolidan en una base **SQLite + FTS5** común a todos tus proyectos.

### 🛡️ Ejemplo 4 — Las reglas del equipo que la IA respeta

`ctxmap adapt` escribe tus normas **una sola vez** y las traduce al formato nativo de cada herramienta:

| Herramienta | Archivo generado |
|---|---|
| Universal | `AGENTS.md` |
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/contextmap.mdc` y `.cursorrules` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Windsurf | `.windsurfrules` |
| Cline / Roo | `.clinerules` |
| Antigravity / pi | `.agents/skills/contextmap/SKILL.md` |
| Hermes | `.hermes/workflows/contextmap.yaml` |

En cada `refresh`/arranque, ContextMap **revisa** esas reglas: si están al día **no las toca**; si tu plantilla cambió (versión nueva) **las actualiza**; y si las editaste a mano, **las respeta**.

---

## 🪙 Presupuesto de contexto (medido, no prometido)

El ahorro no es magia: es quitar del prompt lo que no aporta.

| Artefacto | Coste | Cuándo se carga |
|---|---|---|
| Brief completo (`CONTEXT.md`) | ~1.850 tk | a demanda |
| Brief mínimo (`CONTEXT.min.md`) | **~700 tk** | por defecto |
| Una sola sección (`seccion="riesgos"`) | **~300 tk** | cuando la pides |
| Cambios desde un digest (`context_diff`) | **1 línea** si nada cambió | al volver a una sesión |

Frente a "pegar el repositorio entero", un brief de ~700 tokens es un ahorro superior al **99%**. Además, el brief separa un **prefijo invariante** (cacheable por el proveedor) de la parte que cambia, para maximizar el *prompt caching*.

---

## ✨ Características

- **🧠 Memoria permanente** — tu diario y tus notas manuales (`7.0-MANUAL/`) sobreviven a cada build (`preserve: true`). La historia no se borra: lo tosco se redacta.
- **🌐 Multi-proyecto** — base SQLite + FTS5 con lecciones, decisiones y sesiones de todos tus proyectos.
- **🔌 Servidor MCP nativo** — **30 herramientas** (`context`, `context_diff`, `context_search`, `personal_*`, `knowledge_*`, `refresh`, `check`…) para agentes locales.
- **🧩 Paquete de pi** — `pi install npm:@kudawa/pi-contextmap` (MCP + skill + prompts). Ver [docs/PI_PACKAGE.md](docs/PI_PACKAGE.md).
- **🛡️ Adaptación por IDE** — reglas nativas para 10+ editores (ver Ejemplo 4).
- **📚 Second Brain** — captura la web, artículos y vídeos; sintetiza respuestas **con citas** sobre tu propia wiki (`ctxmap wiki ask`).
- **🧩 Opcional, no obligatorio** — OCR de PDF, embeddings y síntesis con LLM se activan solo si los necesitas; la base no añade dependencias pesadas.

---

## ⚖️ ContextMap frente a otras soluciones

| Necesidad | Pegar todo *(Repomix)* | Indexadores de editor *(Cursor)* | **ContextMap** |
|---|:---:|:---:|:---:|
| Gasto de tokens | 🔴 Altísimo | 🟡 Medio | 🟢 **Brief ~700 tk (>99% menos)** |
| Memoria entre sesiones | ❌ | 🟡 Parcial | **✅ Permanente** |
| Mapa visual navegable | ❌ | ❌ | **✅ Bóveda Obsidian** |
| Cambiar de editor sin perder contexto | ❌ | ❌ Atrapado | **✅ Portable** |
| Visión multi-proyecto | ❌ | ❌ | **✅ Base consolidada** |
| Herramientas nativas para el agente | ❌ | 🟡 Cerradas | **✅ 30 tools MCP + skill** |

---

## 💻 Comandos principales

```bash
ctxmap auto .                            # inicializar: detecta el ecosistema y crea todo
ctxmap refresh .                         # día a día: scan + build + check + revisión de reglas
ctxmap check .                           # salud y readiness (0-100)
ctxmap search "tema"                     # pasajes con citas (sin leer ficheros enteros)

ctxmap personal panorama                 # semáforo de todos tus proyectos
ctxmap personal timeline --dias 7        # qué se trabajó esta semana
ctxmap personal query "autenticación jwt"  # busca en lecciones y decisiones

ctxmap adapt                             # genera/actualiza reglas nativas por IDE
ctxmap mcp                               # servidor MCP (stdio) para agentes

ctxmap secret init                      # crea el baúl cifrado (frase maestra)
ctxmap secret set token_api --nota "apunte"   # guarda SIN mostrar el valor
ctxmap secret list                      # solo nombres/metadatos
ctxmap secret exec --ids token_api --autorizado "curl ..."   # usa sin ver (salida saneada)
ctxmap secret receta descargar_cartola --ids cl_banca --autorizado   # guion aprobado
ctxmap secret audit                     # registro de usos (nunca valores)
ctxmap secret backup pendrive/baul.json # respaldo cifrado portable
```

> 🔐 **Baúl de secretos**: valores cifrados con **AES-256-GCM** y clave derivada
> de tu **frase maestra** (nunca almacenada). El agente **nunca ve los valores**:
> `secret_list` solo nombres; `secret exec`/`secret receta` los **inyecta en el
> proceso y sanea la salida** (`***`), con **autorización explícita** y **log de
> auditoría**. El archivo cifrado viaja contigo (commit o pendrive).
> Requiere el extra opcional: `pip install "context-map-ai[secure]"`.

---

## 🔌 Integración con agentes (MCP)

```bash
pip install "context-map-ai[mcp]"
```

Configura el servidor en tu agente (ejemplo, Hermes):

```yaml
mcp_servers:
  ctxmap:
    command: "ctxmap"
    args: ["mcp"]
```

El agente gana herramientas como:

- `context(minimo=True)` — leer el brief sin gastar tokens de más.
- `context_diff(since="<digest>")` — al volver a una sesión, recibir **solo lo que cambió**.
- `context_search("tema")` — pasajes de la memoria **con cita**.
- `personal_query("tema")` — el historial de **todos** tus proyectos.

---

## 📚 Más documentación

- 🏛️ **[Documentación técnica y de arquitectura](README_TECNICO.md)** — AST, complejidad ciclomática, MCP stdio, topología del grafo.
- 🧩 **[Paquete de pi](docs/PI_PACKAGE.md)** · 🖥️ **[Web Clipper](docs/WEB_CLIPPER.md)** · 🤖 **[LLM opcional](docs/LLM.md)**
- 📜 **[Historial de versiones](CHANGELOG.md)**

---

## 📄 Licencia

**MIT**. Úsalo, modifícalo e intégralo en proyectos personales o comerciales.

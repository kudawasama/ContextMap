# 🗺️ ContextMap

<div align="center">

# La Memoria Permanente para tus Asistentes de IA

### *Evita que tu IA olvide tus decisiones, gaste dinero en tokens y rompa tu código.*

[![Release](https://img.shields.io/badge/version-v2.4.0-blue.svg?style=for-the-badge)](CHANGELOG.md)
[![PyPI](https://img.shields.io/pypi/v/context-map-ai.svg?style=for-the-badge&logo=pypi&logoColor=white)](https://pypi.org/project/context-map-ai/)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)
[![Tests: 260 Passing](https://img.shields.io/badge/tests-260%2F260%20passing-brightgreen.svg?style=for-the-badge)](context_map/__tests__/)
[![MCP Powered](https://img.shields.io/badge/MCP-16%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)

[English Version 🇬🇧](README_EN.md) • [📖 Documentación Técnica y Arquitectura 🏛️](README_TECNICO.md) • [Historial de Versiones](CHANGELOG.md)

</div>

---

## 😫 El Gran Problema al Programar con Inteligencia Artificial

Si usas **Cursor, Claude, Copilot, ChatGPT, Antigravity o Windsurf**, seguro te ha pasado esto:

1. 🧠 **Amnesia Constante**: Abres un nuevo chat y la IA olvidó todo lo que conversaron ayer. Tienes que volver a explicarle el proyecto desde cero.
2. 💸 **Desperdicio de Tokens y Dinero**: Copiar y pegar 100 archivos en cada pregunta satura el límite de contexto, cuesta caro y confunde al modelo.
3. 💥 **Refactorizaciones a Ciegas**: La IA cambia código que ya funcionaba porque desconoce las decisiones pasadas y las reglas de negocio.
4. 🔒 **Vendor Lock-in**: Si cambias de editor (de Cursor a Claude o a VS Code), pierdes todo el contexto acumulado.

---

## 💡 La Solución: ContextMap

**ContextMap es como darle un "disco duro de memoria viva" a tus IAs.**

Escanea tu proyecto, entiende su estructura y propósito, y genera dos cosas mágicas:
1. 🗺️ **Un Mapa Mental Visual en Obsidian**: Una bóveda interactiva hermosa donde puedes ver en tiempo real cómo se conectan las ideas, módulos, riesgos y decisiones.
2. 📄 **Un Brief Ejecutivo Ultra-Compacto (`CONTEXT.md`)**: Un resumen de alta densidad de solo **~1.600 tokens** que le enseña al instante a cualquier IA todo lo que necesita saber sin saturar su memoria (**>99% de ahorro de tokens**).

```
   ┌───────────────────────────────────────────────────────────────┐
   │                   TU PROYECTO DE SOFTWARE                     │
   └───────────────────────────────┬───────────────────────────────┘
                                   │
                           [ ctxmap refresh ]
                                   │
                 ┌─────────────────┴─────────────────┐
                 ▼                                   ▼
        🗺️ BÓVEDA OBSIDIAN                  📄 BRIEF EJECUTIVO
     (Visual, Interactiva,              (Solo ~1.600 tokens,
      Conexiones y Grafos)               Ahorro >99% en LLMs)
                 │                                   │
                 └─────────────────┬─────────────────┘
                                   ▼
          🤖 COMPATIBLE CON CUALQUIER ASISTENTE DE IA
        Cursor · Claude Code · Copilot · Antigravity · Hermes
```

---

## 🚀 Inicio Rápido en 3 Pasos

### 1. Instálalo en 1 comando
```bash
pip install context-map-ai
```
*(O con `uv`: `uv tool install context-map-ai`)*

### 2. Inicializa tu proyecto
Dentro de la carpeta de tu proyecto, dile a tu IA en el chat:
> 💬 *"Inicializa ContextMap para este proyecto"*

O ejecútalo tú mismo en la terminal:
```bash
ctxmap auto .
```

### 3. ¡Listo! Mantén el contexto al día tras hacer cambios
Cada vez que avances en tu código o tomes acuerdos importantes:
```bash
ctxmap refresh .
```

---

## ✨ ¿Por Qué ContextMap Enamora a los Desarrolladores?

### 🧠 1. Memoria Indestructible (`7.0-MANUAL/`)
¿Tomaste una decisión crítica con el cliente o tu equipo? Anótala en tu diario o notas manuales. El motor de ContextMap **jamás borrará tus notas** (`preserve: true`). La IA recordará ese acuerdo para siempre.

### 🌐 2. Tablero de Control Multi-Proyecto (`ctxmap personal panorama`)
¿Trabajas en 5, 10 o 20 proyectos a la vez? Con un solo comando tienes un semáforo visual de qué proyectos están activos, cuáles dormidos y qué tareas urgentes tienen pendientes:

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

### 🔌 3. Control Directo para Agentes de IA (Servidor MCP Nativo)
ContextMap incluye un servidor **MCP nativo (16 herramientas)**. Asistentes como **Hermes Agent, Claude Desktop, Cursor o Windsurf** pueden sincronizar el mapa, consultar lecciones y registrar decisiones de forma completamente autónoma sin que toques la terminal.

### 🛡️ 4. Reglas Universales para 10+ Editores e IAs
Escribe tus normas una sola vez y ContextMap las inyecta en el formato nativo de cada herramienta:
* **Universal**: `AGENTS.md`
* **Claude Code**: `CLAUDE.md`
* **Cursor**: `.cursor/rules/contextmap.mdc` y `.cursorrules`
* **GitHub Copilot**: `.github/copilot-instructions.md`
* **Windsurf**: `.windsurfrules`
* **Cline / Roo Code**: `.clinerules`

---

## ⚖️ Comparativa: ContextMap vs. Otras Soluciones

| ¿Qué necesitas? | Copiar y Pegar Todo<br>*(Repomix / Gitingest)* | Indexadores de Editor<br>*(Cursor / Windsurf)* | **ContextMap v2.4.0** |
| :--- | :---: | :---: | :---: |
| **Gasto de Tokens** | 🔴 Altísimo (quema tu dinero) | 🟡 Medio | 🟢 **Mínimo (>99% de ahorro)** |
| **Mapa Visual Interactivo** | ❌ No existe | ❌ No existe | **✅ Bóveda en Obsidian** |
| **No Olvidar Acuerdos** | ❌ Pierde todo al cerrar chat | 🟡 Parcial | **✅ Memoria Permanente** |
| **Cambiar de Editor sin Perder Datos** | ❌ No | ❌ Atrapado en su app | **✅ Totalmente Portable** |
| **Visión de Múltiples Proyectos** | ❌ No | ❌ No | **✅ Base SQLite Consolidada** |
| **Herramientas MCP Nativas** | ❌ No | 🟡 Cerradas | **✅ 16 Tools stdio listas** |

---

## 💻 Comandos Principales

```bash
# 🚀 Día a día: sincroniza y actualiza todo el contexto
ctxmap refresh .

# 🌐 Vista global: semáforo de todos tus proyectos
ctxmap personal panorama

# ⏱️ Línea de tiempo: qué se trabajó en los últimos días
ctxmap personal timeline --dias 7

# 🔍 Búsqueda ultra-rápida: consulta lecciones y decisiones pasadas
ctxmap personal query "autenticación jwt"

# 🏥 Diagnóstico: revisa la salud de tu contexto
ctxmap check .
```

---

## 📚 Documentación Técnica Avanzada

Si eres arquitecto de software o desarrollador y quieres conocer los detalles de bajo nivel (inspección AST de Python, cálculo de Complejidad Ciclomática de McCabe, Entropía de Shannon para escaneo de secretos, protocolo MCP stdio y topología acíclica de grafos):

👉 **[Consulta la Documentación Técnica y de Arquitectura (README_TECNICO.md)](README_TECNICO.md)**

---

## 📄 Licencia

Este proyecto está liberado bajo la Licencia **MIT**. Eres libre de usarlo, modificarlo e integrarlo en proyectos personales o comerciales.

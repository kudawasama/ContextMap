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

1. Ejecuta la inicialización completa (`ctxmap auto .`): escaneo + ingesta del historial git + construcción del vault y brief.
2. Importa la historia del proyecto con el usuario (`ctxmap import-sessions`, `import-antigravity`, `import-chat`) para que las decisiones y porqués queden en el mapa.
3. Genera las reglas de gobernanza en `AGENTS.md` y el resumen ejecutivo en `.context-map/CONTEXT.md`.
4. Lee los archivos generados y queda **100% en contexto** de la arquitectura, métricas, riesgos y tareas pendientes del proyecto en esa misma respuesta.

---

### 💻 Opción 2: Desde la Terminal

Si estás trabajando directamente en consola o automatizando un script:

```bash
# Modo All-in-One: Escaneo + Ingesta Git + Reconstrucción limpia en 1 solo paso
ctxmap auto .

# Día a día: deja el contexto al día en 1 paso (scan + build preservando manuales + check)
ctxmap refresh .
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

## 🏛️ Gobernanza Automática de Agentes (los 3 niveles del contexto)

ContextMap organiza el contexto en **3 niveles** para que cualquier agente de IA
(Antigravity, Cursor, Claude, Hermes, Copilot, etc.) se ponga al día y trabaje bien:

```
AGENTS.md (raíz)                    → QUÉ   : instrucciones (lee el contexto, importa la historia, mantén vivo)
.context-map/contextmap-skill.md    → CÓMO  : comandos exactos + metodología para escribir notas con alma
.context-map/CONTEXT.md             → estado: qué es el proyecto, por qué existe, riesgos, tareas
.context-map/vault-<proyecto>/      → datos : grafo completo (ideas, riesgos, historial)
```

- **`AGENTS.md`** (generado por `ctxmap build --brief` / `ctxmap init`) define **QUÉ** hacer:
  leer el brief, explorar el vault, importar la historia del proyecto, responder las
  3 preguntas del alma (¿por qué existe? ¿para qué sirve? ¿qué cumple?) y mantener el
  contexto vivo. No repite comandos ni metodología.
- **`.context-map/contextmap-skill.md`** (el CÓMO) contiene los comandos exactos
  (`refresh`, `scan`, `build --brief`, `import-*`) y la metodología narrativa para
  escribir cada nota dándole vida (formato por tipo: IDEA/RIESGO/CAMBIO/BASE/PRUEBA/FUTURO).
- **`.context-map/CONTEXT.md`** es el brief de estado: propósito real del proyecto,
  métricas, riesgos críticos y tareas pendientes.

Reglas que impone la gobernanza:

- **Español Técnico Profesional**: Todas las interacciones, explicaciones y docstrings.
- **Documentación Formal**: Google Style / PEP 257 en todas las funciones y clases.
- **Type Hinting Estricto**: Tipado fuerte en Python.
- **Arquitectura Limpia**: Separación de capas en `core/`, `domain/`, `application/`, `infrastructure/` y `presentation/`.
- **Topología Obsidian Limpia**: Grafo en árbol estricto de 3 niveles sin ciclos rotos.
- **Verificación Mandatoria**: Ejecución previa de `pytest` y `ctxmap refresh .` (o `ctxmap scan .` + `ctxmap build --brief`).
- **Contexto Vivo**: Importar la historia del proyecto (chats/sesiones) y mantener el mapa al día tras cada sesión.

---

## 📊 Topología Estricta en Estrella para Obsidian (Graph View)

Context Map organiza el Vault jerárquicamente en **3 niveles** para garantizar una vista de grafo visualmente deslumbrante en Obsidian:

```Architecture
.context-map/vault/
├── 00-INDICE.md                          # Nivel 0: Dashboard central MOC
├── .manual/                              # Zona protegida: notas manuales (nunca se borran)
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

## 🔄 Día a día: deja el contexto vivo con `ctxmap refresh`

El contexto no se genera una vez: **es la memoria viva del proyecto**. Después de
trabajar (código, decisiones o conversaciones), actualiza el mapa en 1 solo paso:

```bash
ctxmap refresh .     # = scan + build (preservando manuales) + check
```

- **scan**: detecta cambios en el código y los convierte en nodos (CAMBIO/CORRECCION/IDEA).
- **build --brief (sin --clean)**: regenera el vault y el brief SIN tocar tu trabajo manual.
- **check**: audita el readiness y la salud del vault.

Tu `AGENTS.md` generado ya instruye al agente del IDE a correr `ctxmap refresh` después
de cada sesión de trabajo e **importar la historia** (`import-sessions`, `import-antigravity`,
`import-chat`) para que las decisiones y porqués queden registrados en el mapa.

---

## 🛡️ Zona protegida `.manual/` — tu trabajo nunca se borra

Cualquier nota que crees a mano en el vault vive en **`.context-map/vault-<proyecto>/.manual/`**:
`build --clean` JAMÁS la borra (también respeta notas con `preserve: true` en el frontmatter,
donde sea que estén). Al limpiar, ContextMap reporta cuántas notas manuales preservó y el
índice `00-INDICE.md` las enlaza.

> Crea ahí tus notas de sesión, decisiones y registros — el build las conserva y el
> agente del IDE las lee como parte del contexto.

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
| Zona protegida de notas manuales (`.manual/`) | ❌ | ✅ |
| Detección del IDE por proceso activo | ❌ | ✅ |
| Comando único para mantener el contexto vivo (`refresh`) | ❌ | ✅ |

---

## Instalación

```bash
# Instalar globalmente con pip
pip install -e .

# O instalar con UV (recomendado)
uv tool install git+https://github.com/kudawasama/ContextMap.git

# Extra para ingesta de PDFs (ctxmap ingest *.pdf)
uv pip install pymupdf   # o: pip install -e ".[pdf]"
```

---

## Lista Completa de Comandos

```bash
# Escaneo e inicialización
ctxmap init                           # Inicializa la estructura del proyecto
ctxmap scan .                         # Escanea el código y genera nodos semánticos
ctxmap auto .                         # Todo-en-uno: scan + git + build limpio

# Día a día (recomendado): mantener el contexto vivo
ctxmap refresh .                      # ★ scan + build (preservando manuales) + check en 1 paso

# Construcción del Vault y Briefs
ctxmap build                          # Reconstruye el Vault consolidado
ctxmap build --clean                  # Regenera desde cero (preserva .manual/ y preserve:true)
ctxmap build --brief                  # Genera CONTEXT.md y AGENTS.md
ctxmap build --clean --brief          # Construcción limpia completa

# Importadores (la historia del proyecto también es contexto)
ctxmap import-git .                   # Importa historial de commits recientes
ctxmap import-sessions                # Importa sesiones de Hermes Agent
ctxmap import-antigravity             # Importa conversaciones de Antigravity IDE
ctxmap import-chat telegram.txt       # Importa chats de Telegram, Discord o Slack

# Ingesta de documentos externos (segundo cerebro / LLM Wiki style)
ctxmap ingest docs/                   # Ingiere MD/TXT/PDF → nodos DOCUMENTO (3.2-DOCUMENTOS)
ctxmap ingest carta.pdf --brief       # Ingiere un archivo y regenera el brief

# Adaptación al ecosistema agéntico
ctxmap adapt .                        # Detecta stack + IDE (incluye IDE por proceso activo), respeta reglas
ctxmap adapt . --merge               # Fusiona: anexa bloque ContextMap preservando reglas del usuario
ctxmap adapt . --overwrite           # Fuerza sobrescritura de reglas existentes

# Cobertura de agentes: AGENTS.md (universal), CLAUDE.md (Claude Code),
# .cursorrules + .cursor/rules (Cursor), .windsurfrules (Windsurf),
# .clinerules (Cline), .roo/rules (Roo Code), GEMINI.md (Gemini CLI),
# opencode.json (OpenCode), .aider.conf.yml (Aider),
# .github/copilot-instructions.md (Copilot), .hermes/ (Hermes)

# Diagnóstico y Mantenimiento
ctxmap check .                        # Readiness + Salud del Vault (notas manuales, alerta de --clean)
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

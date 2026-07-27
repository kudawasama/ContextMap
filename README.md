# Context Map

**Mapa mental narrativo de proyectos para agentes de IA**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ¿Qué es?

Context Map crea un **vault de Obsidian** con el contexto completo de tu proyecto: qué es, por qué existe, qué riesgos tiene, qué ideas hay pendientes, y qué decisiones se tomaron.

No es un escáner de archivos. Es un sistema que captura el **alma** del proyecto.

## ¿Para qué sirve?

Cuando un agente de IA (Hermes, OpenCode, Cursor, Claude) entra a trabajar en tu proyecto, necesita entender:

- **Qué es** este proyecto
- **Por qué** se creó
- **Qué problemas** resuelve
- **Qué riesgos** tiene
- **Qué ideas** están pendientes
- **Qué decisiones** se tomaron y por qué

Sin este contexto, el agente pierde tiempo leyendo archivos uno por uno, y al final no entiende el espíritu del proyecto.

## Comparativa: Otros vs Context Map

| Característica | Otros | Context Map |
|----------------|:-----:|:-----------:|
| Escaneo técnico de archivos | ✅ | ✅ |
| Briefs para agentes | ✅ | ✅ |
| Score de readiness | ✅ | ✅ |
| Mermaid diagrams | ✅ | ✅ |
| Detección de riesgos técnicos | ✅ | ✅ |
| **Vault Obsidian con graph view** | ❌ | ✅ |
| **Wiki-links `[[entre-notas]]`** | ❌ | ✅ |
| **Tags YAML frontmatter** | ❌ | ✅ |
| **Captura "por qué" del proyecto** | ❌ | ✅ |
| **Contexto emocional/decisorio** | ❌ | ✅ |
| **Sync incremental (sin reescribir)** | ❌ | ✅ |
| **Lee chats y conversaciones** | ❌ | ✅ |
| **Evoluciona con el proyecto** | ❌ | ✅ |
| **Memoria persistente entre sesiones** | ❌ | ✅ |
| **Genérico (cualquier agente)** | ⚠️ | ✅ |
| **Importa sesiones de Hermes** | ❌ | ✅ |
| **Importa chats externos** | ❌ | ✅ |
| **Reportes semanales** | ❌ | ✅ |
| **Importa chats de Antigravity IDE** | ❌ | ✅ |
| **Actualización automática** | ❌ | ✅ |
| **Estandarización de nodos** | ❌ | ✅ |

---

## Instalación

```bash
# Instalar con UV (recomendado)
uv pip install git+https://github.com/kudawasama/ContextMap.git

# O instalar en modo desarrollo
git clone https://github.com/kudawasama/ContextMap.git
cd ContextMap
uv pip install -e .
```

## Uso
n> **Nota**: Los comandos detectan automáticamente el nombre del proyecto del directorio actual.
> No es necesario usar `--project` a menos que quieras un nombre diferente.

```bash
# Primera vez: crear estructura
ctxmap init

# Escanear proyecto automáticamente
ctxmap scan .                        # Escanea proyecto actual

# Importar historial git
ctxmap import-git .                  # Importa commits recientes

# Importar sesiones de Hermes
ctxmap import-sessions               # Importa últimas 5 sesiones
ctxmap import-sessions --limit 10    # Importar más sesiones

# Importar chats externos
ctxmap import-chat telegram.txt      # Importa chat de Telegram
ctxmap import-chat discord.json      # Importa chat de Discord

# Importar chats de Antigravity IDE
ctxmap import-antigravity            # Importa chats de IDE
ctxmap import-antigravity --limit 10 # Importar más conversaciones

# Generar el vault completo
ctxmap build

# Generar con diagrama Mermaid
ctxmap build --mermaid

# Sync incremental (solo agrega nuevos eventos)
ctxmap sync

# Verificar readiness del proyecto
ctxmap check .                       # Score y sugerencias

# Generar reporte semanal
ctxmap weekly                        # Últimos 7 días
ctxmap weekly --days 30              # Últimos 30 días

# Observar cambios y regenerar automáticamente
ctxmap watch --interval 30

# Actualizar ContextMap a la última versión
ctxmap update                        # Descarga e instala desde GitHub

# Migrar proyecto existente a nueva versión
ctxmap sync --migrate                # Estandariza y regenera vault
```

## Comandos

| Comando | Descripción |
|---------|-------------|
| `ctxmap init` | Crea estructura `.context-map/` |
| `ctxmap scan [target]` | Escanea proyecto y genera eventos |
| `ctxmap import-git [target]` | Importa historial de commits |
| `ctxmap import-sessions` | Importa sesiones de Hermes |
| `ctxmap import-chat [file]` | Importa chats externos |
| `ctxmap import-antigravity` | Importa chats de Antigravity IDE |
| `ctxmap build` | Genera vault completo |
| `ctxmap build --mermaid` | Genera con diagrama Mermaid |
| `ctxmap sync` | Sync incremental (solo nuevos) |
| `ctxmap sync --migrate` | Migrar proyecto a nueva versión |
| `ctxmap check` | Verifica readiness (0-100) |
| `ctxmap weekly` | Genera reporte semanal |
| `ctxmap watch` | Observa cambios automáticamente |
| `ctxmap update` | Actualiza ContextMap desde GitHub |

## Estructura del Vault

```
.context-map/
├── vault/
│   ├── 00-INDICE.md                    # Map of Content
│   ├── 00-GRAPH.md                     # Diagrama Mermaid
│   ├── 00-CONEXIONES.md                # Grafo de relaciones
│   ├── 00-CONSOLIDACION.md             # Tracking de consolidación
│   ├── 01-PROYECTOS/                   # Qué es cada proyecto
│   │   ├── COMPLETADO/                 # Archivos completados
│   │   ├── EN_PROGRESO/                # En desarrollo
│   │   ├── PENDIENTE/                  # Por hacer
│   │   └── CANCELADO/                  # Cancelados
│   ├── 02-IDEAS/                       # Ideas y conceptos
│   │   ├── COMPLETADO/
│   │   ├── EN_PROGRESO/
│   │   ├── PENDIENTE/
│   │   └── CANCELADO/
│   ├── 03-RIESGO/                      # Riesgos identificados
│   ├── 04-CAMBIOS/                     # Cambios en curso
│   ├── 05-PRUEBAS/                     # Pruebas y validaciones
│   ├── 06-FUTURO/                      # Lo que viene
│   ├── 07-HITORIAL/                    # Hitos y changelog
│   └── 08-CORRECCIONES/                # Bugs y fixes
├── state/
│   ├── graph.jsonl                     # Grafo de nodos
│   ├── edges.jsonl                     # Conexiones
│   ├── processed_events.txt            # Eventos ya procesados
│   └── REPORTE_ESTANDARIZACION.md      # Reporte de estandarización
├── maps/                               # Snapshots históricos
│   └── HISTORY/
├── chats/                              # Exportaciones de chat
└── raw/
    └── events.jsonl                    # Eventos manuales
```

## Fuentes de Eventos

### 1. Escaneo Automático
```bash
ctxmap scan .
```
Escanea archivos, detecta estructura, entry points, docs, configs, tests, TODOs/FIXMEs.

### 2. Historial Git
```bash
ctxmap import-git .
```
Importa commits y los clasifica: fix→CORRECCION, feat→IDEA, test→PRUEBA.

### 3. Sesiones de Hermes
```bash
ctxmap import-sessions
```
Lee la base de datos de sesiones y extrae contexto de conversaciones.

### 4. Chats Externos
```bash
ctxmap import-chat archivo.txt
```
Soporta Telegram, Discord, Slack, WhatsApp, JSON, texto simple.

### 5. Antigravity IDE
```bash
ctxmap import-antigravity
```
Lee conversaciones de Antigravity IDE (Gemini) desde `~/.gemini/antigravity-ide/`.

### 6. JSONL Manual
Crea `.context-map/raw/events.jsonl`:
```json
{"type":"IDEA","text":"Agregar soporte multiagente","timestamp":"2026-07-24T14:00:00","source":"manual"}
```

## Tipos de Eventos

| Tipo | Descripción | Icono |
|------|-------------|-------|
| `BASE` | Fundamentos del proyecto | 📦 |
| `IDEA` | Ideas y conceptos | 💡 |
| `RIESGO` | Riesgos identificados | ⚠️ |
| `CAMBIO` | Cambios en curso | 🔄 |
| `PRUEBA` | Pruebas y validaciones | 🧪 |
| `FUTURO` | Lo que viene | 🔮 |
| `HITO` | Hitos y changelog | 🎯 |
| `CORRECCION` | Bugs y fixes | 🔧 |

## Roadmap

- [x] Escaneo automático de archivos del proyecto
- [x] Lector de historial git
- [x] Mermaid diagrams
- [x] Score de readiness
- [x] Integración con sesiones de Hermes
- [x] Exportador de chats externos
- [x] Generador de resúmenes semanales
- [x] Integración con Antigravity IDE
- [x] Actualización automática (ctxmap update)
- [x] Estandarización de nodos (tags, status, evidence)
- [x] Carpetas por estado (COMPLETADO, EN_PROGRESO, PENDIENTE, CANCELADO)
- [x] Consolidación automática de notas relacionadas
- [ ] Dashboard web (opcional)

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md)

## Licencia

MIT - Ver [LICENSE](LICENSE)

---

**Creado por [kudawasama](https://github.com/kudawasama)**

# Context Map Generator

**Mapa mental narrativo de proyectos para agentes de IA**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## ¿Qué es?

Context Map Generator crea un **vault de Obsidian** con el contexto completo de tu proyecto: qué es, por qué existe, qué riesgos tiene, qué ideas hay pendientes, y qué decisiones se tomaron.

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

## Comparativa: Otros vs Context Map Generator

| Característica | Otros | Context Map Generator |
|----------------|:-----:|:---------------------:|
| Escaneo técnico de archivos | ✅ | ✅ |
| Briefs para agentes | ✅ | ❌ |
| Score de readiness | ✅ | ✅ |
| Mermaid diagrams | ✅ | ✅ |
| CI/CD integration | ✅ | ❌ |
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

---

## Instalación

```bash
# Instalar desde el repositorio
pip install git+https://github.com/kudawasama/context-map-generator.git

# O instalar en modo desarrollo
git clone https://github.com/kudawasama/context-map-generator.git
cd context-map-generator
pip install -e .
```

## Uso

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

# Generar el vault completo
ctxmap build --project "Mi Proyecto"

# Generar con diagrama Mermaid
ctxmap build --project "Mi Proyecto" --mermaid

# Sync incremental (solo agrega nuevos eventos)
ctxmap sync --project "Mi Proyecto"

# Verificar readiness del proyecto
ctxmap check .                       # Score y sugerencias

# Generar reporte semanal
ctxmap weekly                        # Últimos 7 días
ctxmap weekly --days 30              # Últimos 30 días

# Observar cambios y regenerar automáticamente
ctxmap watch --project "Mi Proyecto" --interval 30
```

## Comandos

| Comando | Descripción |
|---------|-------------|
| `ctxmap init` | Crea estructura `.context-map/` |
| `ctxmap scan [target]` | Escanea proyecto y genera eventos |
| `ctxmap import-git [target]` | Importa historial de commits |
| `ctxmap import-sessions` | Importa sesiones de Hermes |
| `ctxmap import-chat [file]` | Importa chats externos |
| `ctxmap build` | Genera vault completo |
| `ctxmap build --mermaid` | Genera con diagrama Mermaid |
| `ctxmap sync` | Sync incremental (solo nuevos) |
| `ctxmap check` | Verifica readiness (0-100) |
| `ctxmap weekly` | Genera reporte semanal |
| `ctxmap watch` | Observa cambios automáticamente |

## Estructura del Vault

```
.context-map/
├── vault/
│   ├── 00-INDICE.md                    # Map of Content
│   ├── 00-GRAPH.md                     # Diagrama Mermaid
│   ├── 00-CONEXIONES.md                # Grafo de relaciones
│   ├── 01-PROYECTOS/                   # Qué es cada proyecto
│   ├── 02-IDEAS/                       # Ideas y conceptos
│   ├── 03-RIESGO/                      # Riesgos identificados
│   ├── 04-CAMBIOS/                     # Cambios en curso
│   ├── 05-PRUEBAS/                     # Pruebas y validaciones
│   ├── 06-FUTURO/                      # Lo que viene
│   ├── 07-HITORIAL/                    # Hitos y changelog
│   └── 08-CORRECCIONES/                # Bugs y fixes
├── state/
│   ├── graph.jsonl                     # Grafo de nodos
│   ├── edges.jsonl                     # Conexiones
│   └── processed_events.txt            # Eventos ya procesados
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

### 5. JSONL Manual
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
- [ ] Dashboard web (opcional)

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md)

## Licencia

MIT - Ver [LICENSE](LICENSE)

---

**Creado por [kudawasama](https://github.com/kudawasama)**

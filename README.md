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

## Comparativa con Proyectos Existentes

### Lo que hacen otros

| Herramienta | ¿Qué hace? | Limitaciones |
|-------------|-------------|--------------|
| **[repo-context-map](https://github.com/yanqr213/repo-context-map)** | Escanea archivos, genera brief para agentes, Mermaid diagrams | Solo ve estructura técnica, no captura "por qué" |
| **[agent-repo-map](https://github.com/manuelsampedro1/agent-repo-map)** | Analiza repos, genera score de "readiness" | No tiene memoria, no recuerda decisiones |
| **CLAUDE.md / AGENTS.md** | Instrucciones estáticas para el agente | No evoluciona, no captura contexto dinámico |
| **Obsidian (vanilla)** | Notas interconectadas con graph view | No se auto-genera desde código |

### Lo que tiene Context Map Generator

| Característica | repo-context-map | agent-repo-map | CLAUDE.md | **Context Map Generator** |
|----------------|:----------------:|:--------------:|:---------:|:-------------------------:|
| Escanea estructura técnica | ✅ | ✅ | ❌ | ❌ |
| Genera brief para agentes | ✅ | ✅ | ❌ | ❌ |
| Score de readiness | ❌ | ✅ | ❌ | ❌ |
| Vault Obsidian con graph view | ❌ | ❌ | ❌ | ✅ |
| Wiki-links `[[entre-notas]]` | ❌ | ❌ | ❌ | ✅ |
| Tags YAML frontmatter | ❌ | ❌ | ❌ | ✅ |
| Captura "por qué" del proyecto | ❌ | ❌ | ❌ | ✅ |
| Contexto emocional/decisorio | ❌ | ❌ | ❌ | ✅ |
| Sync incremental (sin reescribir) | ❌ | ❌ | ❌ | ✅ |
| Lee chats y conversaciones | ❌ | ❌ | ❌ | ✅ |
| Evoluciona con el proyecto | ❌ | ❌ | ❌ | ✅ |
| Genérico (cualquier agente) | ⚠️ | ⚠️ | ❌ | ✅ |
| Mermaid diagrams | ✅ | ❌ | ❌ | ❌ |
| CI/CD integration | ✅ | ❌ | ❌ | ❌ |
| Detección de riesgos técnicos | ✅ | ✅ | ❌ | ❌ |

### Lo que le falta a cada uno

**repo-context-map le falta:**
- No genera mapas mentales, solo reportes
- No tiene memoria entre ejecuciones
- No captura el contexto emocional del proyecto
- No se integra con Obsidian

**agent-repo-map le falta:**
- No tiene memoria persistente
- No evoluciona con el proyecto
- No genera visualizaciones
- Solo manda un "score", no contexto narrativo

**CLAUDE.md / AGENTS.md le falta:**
- Es estático, no cambia
- No se auto-genera
- No captura historial de decisiones
- No tiene conexiones entre conceptos

**Context Map Generator le falta:**
- No escanea archivos del proyecto (todavía)
- No tiene Mermaid diagrams
- No tiene CI/CD integration
- No tiene score de readiness
- No tiene detección automática de riesgos técnicos
- Es nuevo, poca comunidad todavía

### ¿Por qué usar Context Map Generator?

Si necesitas:
- **Entender el "por qué"** del proyecto, no solo el "qué"
- **Un mapa que evolucione** con el proyecto
- **Visualización en Obsidian** con graph view
- **Contexto narrativo** para agentes de IA

Si necesitas:
- **Escaneo técnico rápido** → usa repo-context-map
- **Score de readiness** → usa agent-repo-map
- **Instrucciones estáticas** → usa CLAUDE.md

**Lo ideal: combinarlos.** Usar repo-context-map para lo técnico y Context Map Generator para lo narrativo.

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

# Generar el vault completo
ctxmap build --project "Mi Proyecto"

# Sync incremental (solo agrega nuevos eventos)
ctxmap sync --project "Mi Proyecto"

# Observar cambios y regenerar automáticamente
ctxmap watch --project "Mi Proyecto" --interval 30
```

## Estructura del Vault

```
.context-map/
├── vault/
│   ├── 00-INDICE.md                    # Map of Content
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

### 1. JSONL Manual

Crea `.context-map/raw/events.jsonl`:

```json
{"type":"IDEA","text":"Agregar soporte multiagente","timestamp":"2026-07-24T14:00:00","source":"manual"}
{"type":"RIESGO","text":"Perder trazabilidad si se edita el mapa a mano","timestamp":"2026-07-24T14:01:00","source":"manual"}
```

### 2. Chats Exportados

Coloca archivos de texto en `.context-map/chats/`:

```
chat-export-2026-07-24.txt
```

El parser clasifica automáticamente cada línea por keywords:
- `feat`, `adding` → IDEA
- `fix`, `correc` → CORRECCION
- `test`, `qa` → PRUEBA
- `todo`, `future` → FUTURO
- `risk`, `bug` → RIESGO

### 3. Sync Incremental

```bash
# Solo procesa eventos nuevos, no reescribe lo existente
ctxmap sync
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

- [ ] Escaneo automático de archivos del proyecto
- [ ] Integración con sesiones de Hermes
- [ ] Lector de historial git
- [ ] Mermaid diagrams
- [ ] Exportador de chats de Telegram/Discord
- [ ] Generador de resúmenes semanales
- [ ] Score de readiness (como agent-repo-map)
- [ ] Dashboard web (opcional)

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md)

## Licencia

MIT - Ver [LICENSE](LICENSE)

---

**Creado por [kudawasama](https://github.com/kudawasama)**

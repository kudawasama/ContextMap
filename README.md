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

## Formato de las Notas

Cada nota tiene:

```markdown
---
type: idea
status: vigente
version: 1
created: 2026-07-24T00:00:00
updated: 2026-07-24T00:00:00
source: "sesion"
tags: ["problema", "valor"]
---

# 💡 El problema que resuelve

**Tags**: `#problema` `#valor`

## Descripción

Cuando un agente nuevo entra a un proyecto, no sabe qué es importante.

## 🔗 Conexiones

- [[la-solucion-es-un-mapa-mental|La solución]]
- [[riesgo-estructura-vacia|Riesgo principal]]
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

## Integración con Obsidian

1. Abre Obsidian
2. File → Open vault → selecciona `.context-map/vault/`
3. Ve el **Graph View** para ver todas las conexiones
4. Navega por las carpetas para explorar el contexto

## Diferencia con Otros Proyectos

| Característica | repo-context-map | agent-repo-map | **Context Map Generator** |
|----------------|------------------|----------------|---------------------------|
| Escanea archivos | ✅ | ✅ | ❌ |
| Captura "por qué" | ❌ | ❌ | ✅ |
| Formato Obsidian | ❌ | ❌ | ✅ |
| Wiki-links | ❌ | ❌ | ✅ |
| Tags YAML | ❌ | ❌ | ✅ |
| Contexto emocional | ❌ | ❌ | ✅ |
| Sync incremental | ❌ | ❌ | ✅ |
| Genérico (cualquier agente) | ❌ | ❌ | ✅ |

## Roadmap

- [ ] Integración con sesiones de Hermes
- [ ] Lector de historial git
- [ ] Exportador de chats de Telegram/Discord
- [ ] Generador de resúmenes semanales
- [ ] Dashboard web (opcional)

## Licencia

MIT - Ver [LICENSE](LICENSE)

---

**Creado por [kudawasama](https://github.com/kudawasama)**

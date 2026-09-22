# 🏛️ ContextMap — Especificaciones Técnicas y Arquitectura Interna

<div align="center">

**Documentación de Ingeniería de Software, Patrones de Diseño, AST y Protocolos**

[![Version: v2.4.0](https://img.shields.io/badge/version-v2.4.0-blue.svg?style=for-the-badge)](CHANGELOG.md)
[![Tests: 260 Passing](https://img.shields.io/badge/tests-260%2F260%20passing-brightgreen.svg?style=for-the-badge)](context_map/__tests__/)
[![MCP: 16 Tools](https://img.shields.io/badge/MCP%20Server-16%20Tools-purple.svg?style=for-the-badge)](https://modelcontextprotocol.io/)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](pyproject.toml)

[Volver al README Principal](README.md) • [English Documentation](README_EN.md) • [Changelog](CHANGELOG.md)

</div>

---

## 1. Visión General de Arquitectura (Clean Architecture Jerárquica)

ContextMap está diseñado bajo el principio de **Clean Architecture**, desacoplando estrictamente el dominio de negocio, los analizadores estáticos de código, la persistencia en disco y los adaptadores de salida visual.

```
context_map/
├── core/                        # Fundamentos del dominio y modelos de datos
│   ├── models/                  # Dataclasses inmutables (Node, Edge, Event, Domain)
│   ├── parsing/                 # Clasificadores semánticos y deserialización JSONL
│   ├── storage/                 # Persistencia atómica JSONL y snapshots
│   ├── normalization/           # Estandarización léxica y reglas de deduplicación
│   ├── personal/                # Lógica pura de base SQLite + FTS5, panorama y repair
│   └── generators/              # Inyectores de Contexto Narrativo Polimórfico
├── domain/                      # Lógica de negocio y análisis estático
│   ├── scanning/                # Escáner estático del árbol de archivos del proyecto
│   ├── synchronization/         # Motor de reconciliación incremental del grafo
│   ├── ingestion/               # Ingestores de documentos (Markdown, PDF, Textos)
│   ├── ecosystem/               # Detección de stack tecnológico y reglas agénticas
│   ├── analysis/                # Cálculo del Readiness Score e indicadores del sistema
│   ├── health/                  # Diagnóstico, self-healing y auto-reparación (doctor)
│   └── reporting/               # Generadores de reportes ejecutivos semanales
├── application/                 # Capa de aplicación y CLI
│   ├── cli/                     # Parser de argumentos CLI unificado (argparse)
│   └── commands/                # Handlers de comandos (auto, refresh, scan, build, check, wrap...)
├── infrastructure/              # Integraciones externas y analizadores AST
│   ├── integrations/            # Git, Hermes Agent, Antigravity, SQLite, Chat exports
│   ├── analyzers/               # Inspección AST Python, complejidad ciclomática y seguridad
│   └── mcp_server.py            # Servidor MCP stdio nativo (FastMCP)
└── presentation/                # Generadores de artefactos visuales y de contexto
    ├── vault/                   # Motor de renderizado del Vault Obsidian (Topología estricta)
    └── briefs/                  # Generador de brief ejecutivo para LLMs (CONTEXT.md)
```

---

## 2. Motor de Análisis Estático (AST & Seguridad)

### 2.1 Complejidad Ciclomática de McCabe (AST)
El analizador en `domain/analyzers/cyclomatic.py` inspecciona recursivamente los nodos del Abstract Syntax Tree (AST) de Python calculando los caminos lógicamente independientes:
$$\text{Complejidad} = 1 + \sum (\text{If} + \text{For} + \text{AsyncFor} + \text{While} + \text{ExceptHandler} + \text{With} + \text{AsyncWith} + \text{Assert} + \text{IfExp} + \text{BoolOp})$$

Si una función supera una complejidad ciclomática de **10**, se clasifica automáticamente como **RIESGO CRÍTICO** en el grafo y en el brief ejecutivo.

### 2.2 Detección de Secretos y Entropía de Shannon
`infrastructure/analyzers/security.py` combina coincidencia léxica determinista de firmas de credenciales (Slack tokens, Stripe live keys, AWS secret keys, GitHub tokens) con el cálculo matemático de la **Entropía de la Información de Shannon**:
$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$
Cadenas asignadas a variables sensibles con $H(X) > 4.5$ son alertadas como llaves criptográficas de alta entropía.

---

## 3. Topología Estricta en Árbol de Obsidian (Graph View)

Para garantizar un Graph View de Obsidian legible, limpio y sin colisiones:

1. **Jerarquía Acíclica Pura**: Cada nota tiene **exactamente un único nodo padre** mediante el pie `⬅ Volver a ...`.
2. **Nivel 0 (`00-INDICE.md`)**: Enlaza únicamente a las 6 secciones raíz (`1.0`, `2.0`, `3.0`, `4.0`, `5.0`, `6.0`).
3. **Nivel 1 (`X.0`)**: Enlaza bidireccionalmente solo a su padre (`00-INDICE.md`) y a sus hijos inmediatos.
4. **Nombres Únicos de Índice**: Los índices de conceptos de ideas se generan con sufijo determinista (`{CONCEPTO}-Pendientes.md`, `{CONCEPTO}-Futuras.md`, `{CONCEPTO}-Completas.md`) para evitar fusiones silenciosas de Obsidian.
5. **Deduplicación Hash SHA-256**: Los eventos y nodos son deduplicados por hash de contenido antes de renderizar.

---

## 4. Servidor MCP Nativo (Model Context Protocol)

El módulo `infrastructure/mcp_server.py` implementa el protocolo **MCP sobre transporte `stdio`**, permitiendo que agentes como **Hermes Agent**, **Cursor**, **Claude Desktop** y **Windsurf** ejecuten 16 herramientas nativas:

| Tool MCP | Descripción |
| :--- | :--- |
| `refresh` | Flujo completo de sincronización (scan + build con preservación + check). |
| `scan` | Inspección estática del código y extracción incremental de eventos. |
| `build` | Generación de la bóveda Obsidian y del brief `CONTEXT.md`. |
| `check` | Evaluación del Readiness Index y diagnóstico de salud del vault. |
| `doctor` | Self-healing y reparación automática de inconsistencias. |
| `personal_panorama` | Semáforo consolidado de actividad multi-proyecto. |
| `personal_timeline` | Feed cronológico de sesiones y eventos con fecha real. |
| `personal_query` | Búsqueda Full-Text Search (FTS5) en milisegundos. |
| `personal_repair` | Saneamiento de eventos, deduplicación y optimización SQLite. |
| `adapt` | Inyección de directrices en formatos `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, etc. |
| `context` | Lectura directa del brief ejecutivo destilado. |
| `export` | Exportación portable a XML, JSON o Markdown. |
| `import_sessions` | Importación y reconciliación de sesiones de trabajo de Hermes (`state.db`). |
| `import_git` | Extracción de historial enriquecido de commits. |
| `import_chat` | Ingesta de conversaciones exportadas de IA. |
| `install_hooks` | Inyección de hooks de Git (`pre-commit` y `post-commit`). |

---

## 5. Base de Datos Personal Consolidada (SQLite + FTS5)

Ubicada en `~/.context-map/personal/personal.db`, proporciona persistencia relacional con tabla virtual de búsqueda de texto completo:

```sql
CREATE TABLE proyectos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT UNIQUE NOT NULL,
    ruta TEXT NOT NULL DEFAULT '',
    ultimo_sync TEXT NOT NULL
);

CREATE TABLE eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proyecto_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    texto TEXT NOT NULL,
    hash TEXT NOT NULL,
    timestamp TEXT NOT NULL DEFAULT '',
    fuente TEXT NOT NULL DEFAULT '',
    FOREIGN KEY(proyecto_id) REFERENCES proyectos(id),
    UNIQUE(proyecto_id, hash)
);

CREATE VIRTUAL TABLE eventos_fts USING fts5(
    texto,
    content='eventos',
    content_rowid='id'
);
```

---

## 6. Aseguramiento de Calidad y Pruebas

Toda la lógica está cubierta por pruebas automatizadas en `pytest`:

```bash
# Ejecución del suite completo (260 tests)
pytest

# Validación de topología en árbol de Obsidian
pytest context_map/__tests__/test_topologia_arbol.py

# Verificación de señales de readiness
python -m context_map.cli check .
```

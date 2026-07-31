# Changelog — Context Map

Todas las notas de versión y cambios destacables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### ♻️ Refactorizado

- **Plan de Refactorización 5.2 completado (F0–F4)**: Eliminados los God Modules identificados en el brief inicial, aplicando Clean Architecture jerárquica y responsabilidad única con verificación de no-regresión en cada fase:
  - **F0 — Logging estructurado**: Nuevo `context_map/core/logging_setup.py` centralizado; eliminadas todas las excepciones silenciosas (`except: pass`) reemplazadas por `logger.warning()` con contexto.
  - **F1 — Fachada en `writer.py`**: Consolidado como fachada única de orquestación del vault (160 líneas).
  - **F2 — Paquete `consolidated/`**: `consolidated.py` (1462 líneas) dividido en `__init__.py`, `common.py`, `consolidado.py` y `jerarquico.py`. Verificación byte-a-byte del vault renderizado: **0 diffs** en modos `consolidated` y `hierarchical`.
  - **F3 — Separación CLI**: `create_parser()` extraído a `cli/parser.py`; `cli/cli.py` reducido de 165 a 62 líneas (solo `main()` y dispatch).
  - **F4 — Paquete `parsing/`**: `parser.py` (234 líneas) dividido en `clasificacion.py`, `cargadores.py`, `dedup.py` y `grafo.py` por responsabilidad única.
- **API pública preservada**: `core/parsing`, `application/cli` y `presentation/vault/consolidated` re-exportan la misma superficie; importadores externos sin cambios.
- **Cobertura de calidad**: `ruff`, `isort`, `mypy` (70 archivos fuente) y `pytest` (17 tests) en verde; readiness 100/100.

---

## [1.2.2] - 2026-07-31

### 🧹 Simplificado y Corregido

- **Deduplicación de tags en render del vault (`_normalize_tags`)**: Cuando `STANDARD_TAGS_BY_TYPE[type]` y los tags del nodo compartían valores (ej: nodo `RIESGO` con tag `riesgo`), el render producía listas con duplicados como `["riesgo", "class:other", "riesgo"]`. Ahora se deduplica preservando orden, dejando tags limpias como `["riesgo", "class:other"]`.
- **CHANGELOG actualizado**: Documentadas por primera vez las versiones `v1.2.0` (dedup de nodos, tags limpias, vault sin duplicados) y `v1.2.1` (normalización de títulos RIESGO eliminan volátiles numéricos, truncamiento 90→200 chars) que estaban publicadas solo en git pero no documentadas en el changelog.

---

## [1.2.1] - 2026-07-30

### 🧹 Simplificado y Corregido

- **Normalización de Títulos `RIESGO`**: Eliminación de volátiles numéricos en títulos (línea de código, distancia de caracteres) que generaban duplicados falsos en el grafo. Ahora `Archivo complejo: writer.py` ya no aparece N veces según el estado del archivo; solo aparece una vez por nombre lógico.
- **Truncamiento de Títulos 90→200 caracteres**: Aumentado el límite para evitar títulos cortados como `Archivo complejo consolidated.py (1457 lí` en wikilinks y frentes de Obsidian.

---

## [1.2.0] - 2026-07-30

### 🚀 Añadido 1.2.0

- **Deduplicación de Nodos en Pipeline (`dedup_nodes()`)**: Nueva función en `core/normalization/standardize.py` que colapsa nodos con el mismo `(type, title[:80])` en cada build/sync. Reduce el state de miles de duplicados a una representación canónica.
- **Tags `class:*` Estandarizadas vía Commits Convencionales**: Mapeo automático en `standardize.py` que deriva `class:feature|fix|chore|other|style|test|update` desde prefijos Conventional Commits (`feat:`, `fix:`, `chore:`, etc.), con limpieza simultánea de variantes legacy sin `:` (`classchore`, `classfeature`).

### 🧹 Simplificado y Corregido

- **Vault sin Duplicados**: Archivo `4.0-RIESGOS.md` pasó de ~42 KB con cientos de wikilinks a menos de 2 KB con 6 entradas únicas. `2.4-Ideas-Relevantes` dejó de triplicar contenido. `5.1-Tareas` ahora renderiza contenido o queda omitido (no vacío).
- **Sincronización Multi-Vault Limpia**: Purgado de la carpeta huérfana `.context-map/vault-vault/` cuando el nombre del repo se resuelve desde la primera instancia del remote.

---

## [1.1.0] - 2026-07-30

### 🚀 Añadido 1.1.0

- **Comando Orquestador All-in-One (`ctxmap auto [target]`)**: Orquestación automática en 1 solo paso (`scan` + `import-git` + `build --clean --brief`).
- **Jerarquía de Detección de Nombre de Repositorio GitHub (1ª Instancia)**: Resolución automática del nombre del Vault basado en el remoto de GitHub.
- **Analizador de Complejidad Ciclomática McCabe**: Ingesta sintáctica AST de puntos de decisión en funciones y módulos.
- **Git Pre-Commit Hook (`ctxmap hook install`)**: Sincronización silenciosa en segundo plano antes de cada commit.

### 🧹 Simplificado y Corregido

- **Unificación de Importadores**: Consolidación de `import-antigravity2` dentro de `import-antigravity`.
- **Depreciación del comando `watch`**: Reemplazado a favor del Pre-Commit Hook desatendido.
- **Consolidación de Vault Único**: Eliminación de duplicados `.context-map/vault` para generar un único directorio de Vault por proyecto.
- **Tolerancia Multi-Disco en Windows**: Solución al fallo `ValueError: relpath` entre distintas unidades de disco (ej. `C:` y `G:`).

---

## [1.0.0] - 2026-07-29

### 🚀 Añadido 1.0.0

- **Gobernanza Automática para Agentes (`AGENTS.md`)**: Generación automática de normas arquitectónicas en proyectos escaneados.
- **Vista de Grafo Obsidian en 3 Niveles**: Estructura en estrella limpia (`00-INDICE.md` -> Secciones `X.0` -> Sub-secciones `X.Y`).
- **Clasificación Semántica de Estado**: Distinción entre código implementado (`completado`), roadmap (`activo`) y tareas/TODOs (`pendiente`).
- **Filtrado NUL (`\x00`)**: Sanitización estricta de nombres de archivo contra caracteres de control en Windows.
- **Sincronización Multi-Vault**: Actualización en tiempo real de todas las carpetas `vault*` asociadas.
- **Integración con Antigravity IDE**: Importador automático de sesiones de chat Gemini/Antigravity.

### 🔧 Corregido

- Sanitización de rutas con espacios y soporte nativo para rutas de red/Google Drive.
- Prevención de ciclos redundantes en enlaces wiki de Obsidian (`[[nota]]`).

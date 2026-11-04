# Índice FTS5 del vault — Plan de Implementación

> **Motivación:** el vault es Markdown-first (fuente de verdad, portátil,
> diff-friendly y navegable en Obsidian). Las consultas de texto libre hoy
> dependen de `grep`/lectura secuencial, que escala mal cuando el vault crece.
> La memoria personal (`ctxmap personal`) ya usa SQLite + FTS5 y es rápida;
> la idea es replicar ese patrón **sobre el vault local**, sin abandonar el
> Markdown como fuente de verdad.

**Goal:** añadir un índice FTS5 derivado del vault local que permita búsquedas
de texto libre en milisegundos (`ctxmap search "término"`), regenerado en cada
`build`/`refresh`, sin romper la portabilidad ni la topología del grafo.

**Arquitectura:** el índice es un artefacto **derivado y reproducible** (no se
versiona, se regenera). Fuente de verdad sigue siendo el árbol de `.md` del
vault; la DB es caché/índice, como ya se hace con `personal`. Se reutiliza el
módulo de storage existente (`core/storage`) y el patrón de `ctxmap personal`.

**Tech Stack:** Python 3.10+, `sqlite3` (stdlib), FTS5 (ya disponible en el
proyecto), pytest. Sin dependencias nuevas.

**Principios:** YAGNI (solo texto libre + filtros básicos), determinismo
(mismo vault → mismo índice), no tocar la topología ni el frontmatter, y no
romper el flujo `ctxmap refresh .` ni los tests de topología.

---

## Estado actual (Fase 0)

| Artefacto | Estado |
|---|---|
| Bóveda Obsidian (`.md` por nota) | ✅ fuente de verdad |
| `ctxmap personal` (SQLite + FTS5) | ✅ multi-proyecto, patrón a replicar |
| `context_map/core/storage` (SQLite) | ✅ base a reutilizar |
| Búsqueda local en el vault | ❌ solo `grep`/lectura secuencial |
| Índice FTS5 por proyecto | ❌ no existe |

---

## Fase 1 — Especificación (sin código)

### Task 1.1: `docs/planes/INDICE-FTS5-VAULT.md` (este documento)

**Objective:** dejar por escrito el contrato del índice para no improvisar.

**Contrato del índice:**

- Ubicación: `.context-map/state/vault_index.db` (junto al manifiesto de reglas).
- Tabla `notas (ruta, titulo, seccion, tipo, estado, contenido)` + virtual
  `notas_fts` (FTS5 sobre `titulo, contenido`).
- Regeneración completa en cada `build`/`refresh` (no incremental en v1).
- `.gitignore`: `vault_index.db` y `*.db-wal`/`*.db-shm` (artefacto derivado).
- Comando: `ctxmap search "término" [--seccion X] [--tipo IDEA] [--limite N]`.

---

## Fase 2 — Implementación (TDD)

### Task 2.1: módulo `core/storage/vault_index.py`

**Objective:** crear/abrir la DB y poblarla desde un directorio de vault.

- `abrir_indice(ruta_db) -> sqlite3.Connection` (crea esquema si no existe).
- `indexar_vault(conn, vault_dir) -> int` (borra y reinserta; devuelve nº de notas).
- Parseo mínimo del frontmatter YAML-like (sin dependencia de `yaml`): `titulo`,
  `seccion`, `tipo`, `estado`. Si falta, valores por defecto.
- Tests: `test_vault_index.py` con vault temporal de 3 notas.

### Task 2.2: comando CLI `search`

**Objective:** exponer la búsqueda al usuario y a los agentes.

- `ctxmap search "término" [--seccion X] [--tipo IDEA] [--limite N]`.
- Salida: tabla compacta (ruta, título, extracto con highlight).
- JSON opcional (`--json`) para consumo por agentes/MCP.
- Tests: `test_cli_search.py`.

### Task 2.3: integración en `build`/`refresh`

**Objective:** el índice se regenera automáticamente.

- En `build` (tras escribir el vault): `indexar_vault(conn, vault_dir)`.
- En `refresh`: ya llama a `build`, así que queda cubierto.
- Si el vault no cambió, saltar el reindexado por hash del directorio (YAGNI:
  solo si el coste del reindexado completo se vuelve notable).

### Task 2.4: herramienta MCP `context_search_vault`

**Objective:** exponer la búsqueda al MCP (hoy `context_search` busca en código).

- Nueva tool `context_search_vault(query, seccion?, tipo?, limite?)`.
- Reutiliza `core/storage/vault_index`.
- Tests: `test_mcp_server_seguridad.py` (sin regresiones).

---

## Fase 3 — Verificación

- `python -m pytest` → 100% verde (hoy 479; objetivo ≥ 490).
- `ctxmap refresh .` → índice regenerado, sin cambios en el árbol de `.md`.
- `ctxmap search "arquitectura"` → resultados en < 50 ms para el vault actual.
- `git status` limpio tras el build (el `.db` está en `.gitignore`).
- `test_topologia_arbol.py` sigue pasando (0 rotos).

---

## Fase 4 — Documentación

- `docs/` o `7.0-MANUAL/DOMINIO.md`: sección «Búsqueda en el vault».
- `CHANGELOG.md`: entrada en `[Unreleased]`.
- `AGENTS.md`/brief: mencionar `ctxmap search` como vía rápida.

---

## Riesgos y decisiones

| Riesgo | Mitigación |
|---|---|
| Drift entre `.md` y el índice | Regeneración completa en cada build; el índice nunca es fuente de verdad. |
| `.db` versionado por error | `.gitignore` explícito + test que falla si aparece en `git status`. |
| Frontmatter no estándar | Parser tolerante con valores por defecto; nunca rompe el build. |
| Coste del reindexado | Medir; si es alto, hash del directorio para saltar. |

---

## Estimación

- Fase 1: 0.5 h (este documento).
- Fase 2: 3–4 h (módulo + comando + integración + MCP).
- Fase 3–4: 1 h.

**Total: ~5 h.** Se puede entregar por fases (primero 2.1+2.2, luego 2.3+2.4).

---

## Decisión abierta

¿Se incluye en v2.15.0 o se deja para v2.16.0 junto a otras mejoras del vault?
Recomendación: v2.15.0, porque es aditivo, no rompe nada y mejora la UX de
búsqueda sin cambiar el modelo de datos.

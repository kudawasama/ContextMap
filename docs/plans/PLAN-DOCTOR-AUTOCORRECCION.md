# Doctor & Auto-corrección (Self-Healing) — Plan de Implementación

> **Motivación:** `domain/health/doctor.py` ya cubre 6 chequeos (git, directorio
> de actualización, vault, nombre, notas manuales e historial) y ya tiene CLI
> (`ctxmap doctor`, `--fix`, `--json`, `--sizes`) y tool MCP (`doctor`, con
> `confirm`). Falta (1) cubrir los fallos de **calidad del entorno** que hoy no
> se detectan (índice FTS5 ausente/viejo, reglas agénticas desactualizadas,
> skills duplicadas, dependencias MCP rotas, contexto viejo), (2) una
> **auto-reparación segura y acotada** y (3) que el **protocolo de inicio** de la
> skill base y de `AGENTS.md` obligue a validar la salud antes de trabajar.

**Goal:** `ctxmap doctor` es el punto único de salud del proyecto: determinista,
rápido (objetivo < 2 s sin red), con auto-reparación solo de lo reversible, y
presente en el arranque de sesión (skill + `AGENTS.md` + brief).

**Arquitectura:** cada chequeo es una función `check_*(report, fix, project_dir)`
registrada en `CHECKS`; `run()` ya los itera, y CLI/MCP ya los consumen, así que
**no hace falta tocar la fachada** salvo el contrato de salida (exit code
`--strict`). La lógica reutilizable se extrae a módulos de producción, nunca se
importa desde `__tests__`.

**Tech Stack:** Python 3.10+, stdlib (`os`, `sqlite3`, `hashlib`, `subprocess`,
`importlib.metadata`), pytest. Sin dependencias nuevas.

**Principios:** determinista · no destructivo por defecto · auto-fix solo
reversible e idempotente · sin red obligatoria · compatible con el pre-commit
(que ya ejecuta `ctxmap refresh`, no `doctor`).

---

## Estado actual (Fase 0)

| Artefacto | Estado real |
|---|---|
| `domain/health/doctor.py` — 6 checks en `CHECKS` | ✅ existente |
| CLI `doctor` con `--fix`, `--json`, `--sizes` | ✅ existente (sin exit code de fallo) |
| Tool MCP `doctor(target, fix, confirm)` | ✅ existente; `fix=True` exige `confirm=True` |
| `run()` itera `CHECKS` y CLI/MCP lo consumen | ✅ existente |
| Frescura del contexto (build vs commits/sesiones) | ✅ existe en `domain/analysis/signals.py::ultima_actividad` |
| Aviso de actualización (metadatos + GitHub, caché 24 h) | ✅ existe en `infrastructure/version_check.py` |
| Reglas agénticas gestionadas con manifiesto `ruta → hash` | ✅ existe en `domain/ecosystem/adaptador.py` (`revisar_reglas_agente`) |
| Índice FTS5 del vault | ✅ existe (`core/storage/vault_index.py`), sin chequeo de salud |
| Validador de topología en producción | ❌ solo dentro de `__tests__/test_topologia_arbol.py` |
| Colisiones de skills entre orígenes (incidente 2026-11-09) | ❌ no existe |
| Contrato de inicio de sesión en skill base / `AGENTS.md` | ⚠️ parcial (solo `ctxmap check`) |

**Conclusión de la revisión:** el borrador anterior duplicaba lógica ya
existente (versión y frescura), proponía importar código de test desde dominio y
no cubría la ruta real del incidente. Este documento lo corrige.

---

## Fase 0 — Prerrequisito: extraer el validador de topología

### Task 0.1: `presentation/vault/topologia.py`

**Objective:** que el chequeo de topología use código de producción y que el
test siga cubriéndolo, sin que `domain` importe desde `__tests__`.

- Crear `analizar_topologia(vault_dir: str) -> ResultadoTopologia` moviendo la
  lógica de `test_topologia_arbol.py::_analizar_vault` (sin padre, colisiones de
  nombre base, wikilinks rotos, índices de concepto).
- `ResultadoTopologia` (dataclass): `sin_padre`, `colisiones`, `enlaces_rotos`,
  `indices_invalidos`, `ok` (propiedad).
- `test_topologia_arbol.py` importa y usa `analizar_topologia`; su
  comportamiento no cambia.

**Tests:** los 3 tests actuales de topología siguen verdes sin cambios de
aserción.

**Aceptación:** `grep -r "__tests__" context_map/domain context_map/presentation`
no devuelve importaciones de test en producción.

---

## Fase 1 — Nuevos chequeos (TDD)

Cada task añade su función a `CHECKS` y sus tests a
`context_map/__tests__/test_doctor.py` (archivo existente, no crear otro).

### Task 1.1: `check_update_available` (no `check_cli_version`)

**Objective:** avisar si hay versión más nueva, **reutilizando**
`infrastructure/version_check.py`.

- `version_local()` (metadatos del paquete, fallback a `pyproject.toml` del
  paquete) + `hay_actualizacion()` (GitHub, caché 24 h).
- `OK` si no hay actualización o no se pudo verificar (sin red/caché).
- `WARN` si la remota es mayor. Nunca `FAIL` por red.
- Sin auto-fix (lo decide el usuario).
- **No leer `pyproject.toml` del proyecto analizado**: ese archivo pertenece al
  proyecto del usuario y no declara la versión de ContextMap.

**Tests:** remota mayor → `WARN`; excepción/red caída → `OK`; sin actualización
→ `OK`.

### Task 1.2: `check_mcp_deps`

**Objective:** detectar un servidor MCP roto por versiones incompatibles.

- `importlib.metadata.version("mcp")` y `version("pydantic")`.
- Si `mcp` **no está instalado** → `OK` con mensaje «extra [mcp] no instalado;
  no aplica» (un usuario solo-CLI no debe ver un WARN permanente).
- Si `mcp` está instalado y `pydantic < 2.13` → `FAIL` (el import de
  `mcp_server` se rompe; piso real en `pyproject.toml`) sin auto-fix.
- Si ambos cumplen (`mcp >= 1.2,<2`, `pydantic >= 2.13,<3`) → `OK`.

**Tests:** metadata simulada para los tres casos.

### Task 1.3: `check_vault_index`

**Objective:** índice FTS5 presente y fresco respecto al vault.

- Resolver el vault con la misma lógica que `check_vault_default`
  (`vault_nombre(nombre_del_repo)` y, si no existe, el primer `vault*`).
- Sin vault → `OK` («sin vault aún»). Sin `.context-map/state/vault_index.db` →
  `WARN` (ejecutar `ctxmap build`).
- Frescura: `mtime` máximo de los `.md` del vault > `mtime` del `.db` → `WARN`.
- `fix`: reindexar **solo** con `abrir_indice` + `indexar_vault` (no lanzar un
  `build` completo) y recalcular el estado.
- Sin BD de vault o con SQLite corrupto → `WARN`, nunca excepción.

**Tests:** sin BD → `WARN`; BD más vieja que una nota → `WARN`; `fix` crea e
indexa (`COUNT(*) == nº de .md`); vault vacío → `OK`.

### Task 1.4: `check_context_freshness`

**Objective:** detectar contexto desactualizado **sin reinventar** la lógica.

- Ejecutar `analizar_readiness(project_dir)` y leer `resultado.frescura`
  (producido por `signals.ultima_actividad`: último build vs último commit y
  sesiones de Hermes pendientes).
- `WARN` si `frescura["aviso"]`; el mensaje es el propio aviso.
- Sin auto-fix (`refresh` puede ser costoso).
- Corregir la descripción anterior («brief vs diario»): la comparación real es
  **último build vs actividad posterior**, no brief vs diario.

**Tests:** `analizar_readiness` monkeypatcheado con y sin `aviso`; nunca lanza
si el análisis falla (`OK` con mensaje de omisión).

### Task 1.5: `check_skill_collisions`

**Objective:** evitar que una copia manual de la skill gane a la del paquete
(incidente 2026-11-09).

- Raíces **conocidas y acotadas** (solo si existen):
  - `~/.agents/skills`
  - `<proyecto>/.agents/skills`
  - `~/.claude/skills`
  - `~/.pi/agent/npm/node_modules/@*/*/skills` ← ruta real del incidente
  - `<proyecto>/node_modules/@*/*/skills`
- **No** recorrer `node_modules/**` completo (viola el objetivo de < 2 s):
  profundidad máxima 3 por raíz, `os.scandir`, sin seguir symlinks.
- Extraer `name:` del frontmatter con un parser tolerante (reutilizar el patrón
  de `core/storage/vault_index.py`).
- Un `name` en ≥ 2 orígenes → `WARN` listando rutas. **No afirmar cuál gana**:
  el orden depende del agente; para pi se documenta que gana «el primero
  descubierto», como información, no como veredicto del doctor.
- Sin auto-fix (mover/borrar es decisión del usuario).

**Tests:** home y proyecto simulados con `monkeypatch`; duplicado → `WARN` con
ambas rutas; único → `OK`; rutas inexistentes → `OK`; no se escanea
`node_modules` genérico.

### Task 1.6: `check_generated_rules`

**Objective:** detectar reglas agénticas gestionadas que quedaron viejas o
fueron editadas, usando el manifiesto existente.

- Leer `.context-map/state/reglas_generadas.json` (`ruta → hash`). Sin manifiesto
  → `OK` (proyecto antiguo o sin reglas).
- **Prerrequisito de código:** añadir `dry_run: bool = False` a
  `revisar_reglas_agente()` para poder calcular estados (`creados`,
  `actualizados`, `omitidos`, `respetados`) **sin escribir**.
- `WARN` si hay `actualizados` (plantilla nueva) o `respetados` con marcador
  (edición manual de un bloque gestionado); el mensaje indica `ctxmap adapt`.
- `fix`: ejecutar `revisar_reglas_agente()` real (idempotente; respeta ediciones
  manuales) y reportar el resultado.

**Tests:** `dry_run` no escribe; plantilla cambiada → `WARN` y `fix` actualiza;
edición manual → se respeta; sin manifiesto → `OK`.

### Task 1.7: `check_topologia`

**Objective:** convertir el test de topología en chequeo de salud.

- Usar `analizar_topologia(vault_dir)` de la Fase 0.
- `OK` si `resultado.ok`; `FAIL` con el conteo de violaciones en caso contrario.
- Sin auto-fix (se corrige con `ctxmap build`).
- Si no hay vault → `OK` (lo reporta `check_vault_default`).

**Tests:** vault temporal sano → `OK`; wikilink roto / nombre duplicado →
`FAIL` con el detalle.

---

## Fase 2 — Integración en el arranque de sesión

> Aclaración importante: una skill **instruye**, no ejecuta. No hay hook que
> fuerce el chequeo al abrir sesión. Por eso el plan combina (a) instrucción
> explícita en los artefactos que el agente lee y (b) resumen de salud en el
> brief, que se genera solo.

### Task 2.1: skill operativa `.context-map/contextmap-skill.md`

**Objective:** el «CÓMO» que genera `build` incluye la validación de inicio.

- `presentation/briefs/skill.py::generar_skill_contextmap`: añadir
  `ctxmap doctor` a la lista de comandos y un paso 0 del protocolo:
  «Antes de trabajar: `ctxmap doctor --json`. Si hay `FAIL`, repara o reporta;
  nunca `--fix` sin confirmación del usuario».
- Este archivo se regenera en cada `build`, así que llega a proyectos existentes
  sin `adapt --overwrite`.

### Task 2.2: skill nativa `.agents/skills/contextmap/SKILL.md`

- `domain/ecosystem/rules_templates.py::_generar_antigravity_skill`: añadir el
  paso 0 al «Protocolo de inicio» y `ctxmap doctor` a la lista de comandos.
- Nota: `adapt` escribe en `.agents/skills/` **del proyecto**, nunca en
  `~/.agents/skills/`; el plan no debe prometer lo contrario.

### Task 2.3: `AGENTS.md`

- `_generar_agents_md` y `presentation/briefs/agents.py`: añadir `ctxmap doctor`
  al protocolo de inicio.
- **Modos:** `adapt` por defecto usa `modo="respect"` y no toca `AGENTS.md`
  existente. Para propagar el cambio en proyectos ya inicializados hay que usar
  `ctxmap adapt --merge` (bloque delimitado por `CONTEXTMAP:BEGIN/END`) o
  `--overwrite`. Documentarlo; no asumir que «regenerar con adapt» basta.

### Task 2.4 (recomendada): salud visible en el brief

- En `build`, ejecutar `run(fix=False)` y añadir una línea «Salud del entorno:
  N OK · M WARN · K FAIL» en `.context-map/CONTEXT.md`, con los nombres de los
  `FAIL`. Coste: los checks son deterministas y locales.
- Beneficio: el agente ve el estado aunque no invoque `doctor`.

### Task 2.5: contrato de salida CLI (nuevo `--strict`)

- `doctor_cmd.py` hoy **siempre sale con código 0**; un script o el arranque de
  sesión no pueden distinguir OK de FAIL.
- Añadir `--strict`: exit 1 si `report.failed` no está vacío (los `WARN` no
  fallan). Sin `--strict`, comportamiento actual.
- Actualizar `parser.py` y tests de CLI.
- **MCP:** sin cambios de firma; `doctor` ya llama a `run()` y ya exige
  `confirm=True` para `fix=True`. No se añaden tools (siguen siendo 34).

---

## Fase 3 — Verificación

- `python -m pytest` → 100 % verde (incluye `test_doctor.py`,
  `test_topologia_arbol.py`, `test_revision_reglas.py`, `test_dependencias_mcp.py`).
- `ctxmap doctor` → 6 checks actuales + 6 nuevos (12 en total).
- `ctxmap doctor --json` → JSON válido con los 12.
- `ctxmap doctor --strict` → exit 1 con un FAIL simulado, exit 0 en proyecto sano.
- `ctxmap doctor --fix` en un proyecto temporal → reindexa el vault, actualiza
  reglas gestionadas y no toca nada editable por el usuario.
- `ctxmap build` → regenera `contextmap-skill.md` con el paso 0 y el brief con
  la línea de salud.
- `ctxmap adapt --merge` → `AGENTS.md` y `SKILL.md` con el paso 0.
- `context_map/__tests__/test_topologia_arbol.py` sigue pasando y ya no contiene
  la lógica duplicada.

---

## Fase 4 — Documentación

- `docs/GOBERNANZA-AGENTES.md`: sección «Auto-diagnóstico» con la diferencia
  `check` (readiness) vs `doctor` (salud del entorno + reparación).
- `AGENTS.md` del repo: `ctxmap doctor` en el protocolo de inicio.
- `CHANGELOG.md`: entrada en `[Unreleased]`.
- `7.0-MANUAL/DOMINIO.md`: nota del módulo de salud.
- Marcar este plan como implementado al cerrar.

---

## Riesgos y decisiones

| Riesgo | Mitigación |
|---|---|
| El arranque de sesión se vuelve lento | Checks locales, sin red obligatoria; escaneo acotado de skills; objetivo < 2 s. |
| Una skill solo «aconseja», no ejecuta | Instrucción explícita en skill + `AGENTS.md` + resumen de salud en el brief (Task 2.4). |
| `--fix` destructivo | Solo índice y reglas gestionadas; `revisar_reglas_agente` respeta ediciones manuales; MCP exige `confirm=True`. |
| Duplicación con `ctxmap check` | `check` = readiness del proyecto; `doctor` = entorno + reparación. Reutiliza `ultima_actividad`, no la copia. |
| Falsos positivos de colisión | Solo raíces conocidas, sin recorrer `node_modules` completo; se reporta, no se borra. |
| `AGENTS.md` no se actualiza | Documentar `adapt --merge`/`--overwrite`; `contextmap-skill.md` y el brief sí se regeneran siempre. |
| Importar código de test desde dominio | Fase 0 extrae el validador a `presentation/vault/topologia.py`. |

---

## Estimación

- Fase 0 (extracción topología): 1 h.
- Fase 1 (6 chequeos + `dry_run` + tests): 4–5 h.
- Fase 2 (skill, AGENTS, brief, `--strict`): 2 h.
- Fase 3–4: 1–2 h.

**Total: ~8–10 h.** Entregable por bloques: (1) Fase 0 + 1.3/1.7, (2) 1.1/1.2/1.4,
(3) 1.5/1.6, (4) Fase 2 y documentación.

---

## Fuera de alcance

- Hook que ejecute `doctor` en cada commit (el pre-commit ya hace `refresh`).
- Comprobación remota de PyPI en cada arranque (la caché de 24 h de
  `version_check` es suficiente).
- Reparación automática de colisiones de skills (requiere decisión humana).
- Nuevas tools MCP (el inventario se mantiene en 34).

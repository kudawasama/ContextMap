# Clasificación Calibrada (patrón System One / Jev) — Plan de Implementación

> **Restricción que gobierna este plan:** la API de **Jev (TypeSafe AI) no es
> usable hoy**: está en *early access* con lista de espera, es propietaria y
> exige `TYPESAFE_API_KEY`. Por tanto **nada** del plan depende de ella: se
> replica el *patrón* (decisiones tipadas + confianza calibrada + evidencias)
> de forma **local, determinista y sin coste**. El adaptador remoto queda como
> fase opcional (Fase 5), desactivado por defecto y sin llamadas en tests.

**Goal:** sustituir la clasificación «gana el primer patrón» de ContextMap por
un motor de decisiones tipadas que (1) acumule evidencia ponderada, (2) publique
distribución de probabilidad y **confianza calibrada**, (3) marque la ambigüedad
en una **cola de revisión** visible en el vault y (4) documente el ecosistema
frente al que se compara.

**Arquitectura:** capa de decisión **sin dependencias externas** en
`core/decisiones.py` (stdlib puro) + panel de preguntas derivado de
`normalization/mappings.py` (una sola fuente de verdad) + integración en los
tres puntos reales de clasificación (`_heuristic_event`, `inferir_classification`,
`inferir_concepto`, `clasificar_tipo`). Las **reglas duras** (Conventional
Commits, origen git, tipo explícito) deciden primero y son irrevocables
(`por_regla=True`).

**Tech Stack:** Python 3.10+, dataclasses frozen, `re`, `functools.lru_cache`,
pytest. Sin red, sin modelos, sin claves.

**Principios:** TDD (test → fail → implement → pass), DRY (catálogos existentes
como fuente única), determinismo (mismo texto → misma distribución: el build
sigue siendo reproducible byte a byte), YAGNI (nada de embeddings ni de LLM en
esta capa).

---

## Estado actual (Fase 0 completada y verificada en esta sesión)

| Artefacto | Estado |
|---|---|
| `context_map/core/decisiones.py` — motor tipado (`noul`/`choice`/`score`) | ✅ implementado |
| `context_map/core/normalization/paneles.py` — `PREGUNTA_TIPO/CLASIFICACION/CONCEPTO` derivadas de `mappings.py` | ✅ implementado |
| Integración en `parsing/clasificacion.py` (`_heuristic_event`) | ✅ implementado |
| Integración en `normalization/inference.py` (`inferir_classification`, `inferir_concepto`, `clasificar_tipo`) | ✅ implementado |
| Cola de revisión `revision:clasificacion` en `estandarizar_nodo` | ✅ implementado |
| Verificación | 23 tests OK (`test_parsing`, `test_clasificacion_chat`, `test_standardize`, `test_hermes_clasificacion`, `test_topologia_arbol`) |

**Evidencia del cambio:** `"feature: fix del parser"` antes → `IDEA` en silencio;
ahora → `IDEA` con confianza `0.11`, margen `0.00` y dos evidencias en conflicto
(`IDEA: feature/adding`, `CORRECCION: fix/corrección`) → queda marcado para
revisión en lugar de resolverse por accidente.

---

## Fase 1 — Documentar (sin código)

### Task 1.1: `docs/INVESTIGACION-JEV.md`

**Objective:** Dejar por escrito qué es Jev, cómo funciona, pros/contras y por
qué se replica localmente en vez de consumirlo.

**Files:** Create `docs/INVESTIGACION-JEV.md`

**Contenido mínimo:** definición (discriminativo, no generativo, *System One*),
primitivas `noul`/`choice`/`score`, fórmula de confianza
`(p_max − 1/n)/(1 − 1/n)`, RLCD + datos sintéticos, latencia 70–500 ms, precio
$0.042/M entrada y salida gratis, pros, contras (paper no publicado, evals
propias sesgadas, delega umbrales al usuario, preguntas independientes) y la
sección **«Por qué ContextMap no depende de Jev»**.

### Task 1.2: `docs/COMPARATIVO-ECOSISTEMA-CONTEXTO.md`

**Objective:** Comparativa honesta de ContextMap contra Second Brain, Obsidian
y capas de memoria/contexto, con datos objetivos (★ de GitHub) y qué tenemos y
qué no.

**Files:** Create `docs/COMPARATIVO-ECOSISTEMA-CONTEXTO.md`

**Contenido mínimo:** tablas por área (PKM, Obsidian+agente, memoria de agentes,
contexto de código, ingesta), tabla «capacidad → quién la tiene → ContextMap»,
y la lista explícita de **brechas** (grafo temporal tipo Graphiti, spec-driven
tipo spec-kit/OpenSpec, sync bidireccional Obsidian).

---

## Fase 2 — Tests propios del motor (TDD)

### Task 2.1: `context_map/__tests__/test_decisiones.py`

**Objective:** Fijar el contrato del motor: probabilidades, calibración,
desempate histórico, anti-señales, conflicto y determinismo.

**Files:**
- Create: `context_map/__tests__/test_decisiones.py`
- Referencia: `context_map/core/decisiones.py`, `context_map/core/normalization/paneles.py`

**Casos obligatorios**

```python
def test_softmax_suma_uno_y_uniforme_sin_evidencia() -> None: ...
def test_confianza_cero_con_distribucion_uniforme() -> None: ...
def test_confianza_uno_con_distribucion_degenerada() -> None: ...
def test_senal_negativa_reduce_probabilidad_de_su_etiqueta() -> None: ...
def test_desempate_respeta_orden_historico() -> None: ...      # "feature fix" -> IDEA
def test_decidir_tipo_elige_por_evidencia_no_por_orden() -> None: ...
def test_ambiguedad_real_se_marca_como_conflicto() -> None: ...  # feature + fix
def test_regla_dura_no_requiere_revision() -> None: ...
def test_pregunta_rechaza_senal_de_etiqueta_desconocida() -> None: ...
def test_score_devuelve_puntuacion_ponderada() -> None: ...
def test_mismo_texto_misma_decision() -> None: ...               # determinismo
def test_anti_senal_todo_en_minusculas_no_es_futuro() -> None: ...
```

**Step 1:** escribir los tests → **Step 2:** `pytest` → los que fallen, **Step 3:**
ajustar motor/panel, **Step 4:** verde.

### Task 2.2: Regresión de la integración

**Objective:** Garantizar que la integración no rompió los contratos previos.

**Files:** ya existentes (`test_parsing.py`, `test_clasificacion_chat.py`,
`test_standardize.py`); añadir a `test_decisiones.py` un caso end-to-end por
`estandarizar_nodo` que verifique la etiqueta `revision:clasificacion`.

---

## Fase 3 — Verificación del pipeline (inamovible)

```bash
python -m pytest                                   # 1. tests
python -m context_map.cli scan .                    # 2. escanear
python -m context_map.cli build --clean --brief     # 3. vault + brief
python -m context_map.cli check .                   # 4. readiness
```

**Criterios de aceptación**

1. `test_topologia_arbol.py` en verde (0 sin padre, 0 colisiones, 0 wikilinks rotos).
2. `check .` con readiness ≥ el valor previo (100/100).
3. Ningún test que pasaba antes falla por este cambio.
4. Los 8 fallos preexistentes de MCP/pydantic 2.9 quedan **fuera del alcance**
   (no se tocan aquí).

**Riesgo conocido y mitigación:** el cambio de clasificación mueve nodos entre
tipos (IDEAS/BASES/etc.) y añade `revision:clasificacion`. Mitigación: los
catálogos se derivan de `mappings.py` con **peso decreciente por posición
histórica**, de modo que en caso de empate gana exactamente el grupo que ganaba
antes; la primera etiqueta de cada pregunta es el valor por defecto histórico
(`IDEA`, `other`, `GENERAL`) para que «sin evidencia» no cambie nada.

---

## Fase 4 — Memoria viva (gobernanza)

### Task 4.1: Diario y conocimiento

**Objective:** Dejar la lección reutilizable, no solo el código.

**Files:**
- Update `.context-map/vault-ContextMap/7.0-MANUAL/Diario/2026-10-13.md`
- Create nota en `.context-map/vault-ContextMap/8.0-KNOWLEDGE/` con la estructura
  **Lección · Cómo se resolvió · Prompt · Instrucción · Conexiones**
- Update `7.0-MANUAL/BACKLOG.md` solo si queda trabajo pendiente real.

### Task 4.2: Dominio

**Objective:** Documentar la lógica nuclear en el manual del proyecto.

**Files:** `7.0-MANUAL/DOMINIO.md` (si no existe, crearlo) con la sección
«Clasificación calibrada: motor, panel, umbrales y cola de revisión».

---

## Fase 5 — Adaptador Jev remoto (OPCIONAL, bloqueado hoy)

**Estado: NO ejecutable** — sin acceso a la API (waitlist) no hay nada que
probar, y el proyecto prohíbe generar coste sin autorización explícita.

**Diseño ya previsto (para cuando haya acceso):**

```python
class MotorJevRemoto(MotorLexicoCalibrado):
    """Adaptador al contrato HTTP de TypeSafe. Requiere TYPESAFE_API_KEY."""
    nombre = "jev-remoto"
    # decidir(): state + questions -> distribuciones; mapea a Distribucion/Decision
    # Si falta la clave o falla la red -> delega en el motor local (degradación).
```

**Guardas obligatorias:** (a) solo se activa con `CTXMAP_MOTOR=jev` **y**
`TYPESAFE_API_KEY`; (b) nunca en tests ni en `build`; (c) si falla, *fallback*
silencioso al motor local y registro en log. La firma pública
(`decidir(estado, pregunta) -> Decision`) ya es compatible, así que el cambio es
aditivo y no toca a los consumidores.

---

## Fuera de alcance (explícito)

- Embeddings semánticos en la capa de decisión (ya existen como opcionales aparte).
- Grafo temporal de entidades (Graphiti) y spec-driven (spec-kit/OpenSpec):
  son brechas **identificadas** en el comparativo, no parte de este plan.
- Arreglar los 8 fallos preexistentes de MCP/pydantic.

---

## Orden de ejecución

1. Fase 1 (documentos) → 2. Fase 2 (tests del motor) → 3. Fase 3 (pipeline) →
4. Fase 4 (diario/DOMINIO) → 5. Fase 5 queda bloqueada hasta que exista acceso a Jev.

---

## Resultado de la ejecución (2026-10-13)

| Fase | Estado | Evidencia |
|---|---|---|
| 0 — Código del motor | ✅ | `core/decisiones.py`, `normalization/paneles.py`, integración |
| 1 — Documentos | ✅ | `docs/INVESTIGACION-JEV.md`, `docs/COMPARATIVO-ECOSISTEMA-CONTEXTO.md` |
| 2 — Tests del motor | ✅ | `context_map/__tests__/test_decisiones.py` — **19 passed** |
| 3 — Pipeline | ✅ | pytest **422 passed** (+19) y los mismos 8 fallos preexistentes; `scan` OK; `build --clean --brief` OK; `check` → **readiness 100/100** |
| 4 — Memoria viva | ✅ | `7.0-MANUAL/DOMINIO.md`, nota `8.0-KNOWLEDGE/Clasificacion-Calibrada-Sin-Depender-de-Jev.md` (+ entrada 18 en el índice), Diario 2026-10-13, `7.0-MANUAL.md` enlaza el manual |
| 5 — Adaptador Jev | ⛔ bloqueado | Sin acceso a la API (waitlist). No se probó nada: el plan prohíbe generar coste sin autorización |

**Criterios de aceptación:** (1) topología en verde ✅ · (2) readiness 100/100 ✅ ·
(3) 0 regresiones ✅ · (4) fallos MCP/pydantic fuera de alcance ✅.

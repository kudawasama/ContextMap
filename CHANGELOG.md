# Changelog — Context Map

Todas las notas de versión y cambios destacables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.1] — 2026-08-21

### 🔧 Correcciones — Saneamiento de release

- **fix: flag `--version` real**: `ctxmap --version` ahora imprime la versión instalada (antes no existía y `update` mostraba un mensaje hardcodeado).
- **fix: detección de versión con el paquete renombrado**: `version_check` prioriza `context-map-ai` (nombre canónico actual) sobre el heredado `context-map`, eliminando avisos falsos de actualización.
- **fix: lint (ruff) 100% limpio**: corregidos 11 errores (`F811` redefinición en `brief.py`, `F841` variables sin usar, `SIM102/105/108`).
- **style: ruff --fix e isort** aplicados en todo el paquete (anotaciones modernas `dict`/`| None` y orden de imports).

Suite: 176/176 tests verdes · ruff limpio.

---

## [2.2.0] — 2026-08-19

### 🗜️ Nuevo — Paquetes de Contexto Portátiles Offline, Escáner de Auditoría AST & Fallback de Modelos

- **🗜️ Empaquetado y Desempaquetado Portátil (`ctxmap pack` / `ctxmap unpack`)**: Nuevo sistema para comprimir la memoria viva completa de cualquier proyecto en un archivo único binario `.ctxpack` con manifiesto de integridad (`pack_manifest.json`) y restaurarlo 100% offline en cualquier equipo.
- **🛡️ Escáner Sintáctico AST de Auditoría Local (`domain/analyzers/ast_audit.py`)**: Motor determinístico de análisis estático que detecta ejecuciones dinámicas inseguras (`eval/exec`), concatenaciones de SQL dinámicas, bloques `except Exception: pass` silenciosos, desuso de administradores de contexto en archivos y credenciales hardcodadas.
- **🦙 Fallback Inteligente de Modelos Ollama (`infrastructure/integrations/ollama.py`)**: Auto-resolución de modelos locales instalados vía API `/api/tags` para seleccionar automáticamente modelos disponibles (`coder`, `qwen`, `llama`, `deepseek`, `phi`) sin fallar por modelos ausentes.
- **⚙️ Generación Automática de Plantilla `dominios.yaml` (`application/commands/_helpers.py`)**: Creación transparente de la plantilla por defecto de agrupamiento temático para Obsidian.
- **Suite de Pruebas**: 176/176 tests unitarios pasados al 100% verde.

---

## [2.1.0] — 2026-08-18

### ✨ Nuevo — Suite de Inteligencia Offline, Tokenización Profesional & Protocolo Agéntico de Dominio

- **🧮 Visualización Profesional de Tokenización**: Medición en tiempo real del presupuesto de tokens en consola CLI y tabla ejecutiva en `CONTEXT.md` mostrando >99% de ahorro de ventana de contexto respecto al código crudo.
- **🦙 Integración Ollama Local Adaptativa (`infrastructure/integrations/ollama.py`)**: Conexión opcional a Ollama en `http://localhost:11434` sin costo de API ni internet.
- **🖥️ Diagnóstico de RAM y Guardián de Hardware (`domain/health/hardware.py`)**: Evaluación previa de memoria RAM y CPU para recomendar modelos de bajo consumo (`qwen2.5-coder:1.5b` ~1.2 GB RAM) y conmutar a AST determinístico si la RAM es baja (<3.5 GB libres).
- **✍️ Enriquecedor de Código Función por Función (`ctxmap enrich`)**: Comando CLI (`application/commands/enrich.py`) que audita y documenta funciones sin docstring en Español Técnico (Google Style).
- **🏷️ Extractor de Conceptos TF-IDF (`domain/normalization/domain_extractor.py`)**: Descubrimiento determinístico local de términos de dominio del negocio (`FACTURACION`, `INVENTARIO`, `TCG`, `AUTENTICACION`).
- **🧠 Protocolo Agéntico de Captura del Dominio (`AGENTS.md`)**: Protocolo estandarizado en reglas agénticas para que cualquier IA en el IDE (`Antigravity`, `Cursor`, `Claude`) interprete y documente automáticamente ecuaciones implícitas y reglas nucleares en `7.0-MANUAL/DOMINIO.md`.
- **🎨 Grupos de Color del Graph View Profesionalizados (`common.py`)**: Grafo de Obsidian limpio y estructurado únicamente por las 8 secciones de dominio principales y tipos de nodos base.
- **Suite de Pruebas**: 173/173 tests unitarios pasados al 100% verde.

---

## [2.0.0] — 2026-08-17

### 🚀 Major Release — Arquitectura de Siguiente Generación & Inteligencia AST

- **Complejidad Ciclomática AST (`domain/analyzers/cyclomatic.py`)**: Cálculo sintáctico de la complejidad de McCabe por función/método con alertas preventivas en `4.0-RIESGOS` al superar 10 ramas lógicas.
- **Escaneo Incremental con Caché SHA-256 (`domain/scanning/cache.py`)**: Sistema de almacenamiento en caché `.context-map/cache.json` que omite re-analizar archivos no modificados, logrando un escaneo 10 veces más rápido.
- **Diagramas Mermaid Dinámicos por Submódulo (`presentation/vault/`)**: Generación de diagramas de arquitectura interactivos `mermaid` en `3.0-ESTRUCTURA` para visualizar capas y paquetes.
- **Documentación Interactiva MkDocs (`mkdocs.yml`)**: Sitio web oficial con tema MkDocs Material y despliegue automático mediante GitHub Actions.
- **Soporte de Tokenización Universal**: Integración del catálogo completo de 60+ modelos LLM de 2026 (OpenAI GPT-5.x, Claude 4.5/5, Gemini 3.x Flash, DeepSeek V4, GLM 5, Kimi K2.5-K3, Qwen 3.5/3.6, Grok 4.5/4.6, MiniMax M3, Nemotron, etc.).

---

## [1.9.0] — 2026-08-17

### ✨ Nuevo — Auto-Mantenimiento Autónomo & Self-Healing

- **Self-Healing (`ctxmap doctor --fix`)**: Diagnóstico y auto-reparación determinística de vault, unificación de nombres de proyectos y metadatos sin perder notas manuales.
- **Daemon Watcher (`ctxmap watch .`)**: Monitoreo en segundo plano con debouncing (500ms) que detecta cambios de código y sincroniza incrementalmente en tiempo real.
- **Git Hooks Transparentes (`ctxmap hook install`)**: Inyección automática de `pre-commit` y `post-commit` para sincronizar código y brief en cada commit.
- **Servidor MCP Ampliado**: Nuevas herramientas `doctor` e `install_hooks` en el servidor MCP stdio (11 herramientas stdio en total).
- **Suite de Pruebas**: 160/160 tests unitarios pasados exitosamente al 100% verde.

---

## [1.8.0] — 2026-08-17

### ✨ Nuevo — Tokenización, Escáner de Seguridad y Exportador Portable

- **Módulo de Tokenización (`core/tokenization.py`)**: Conteo exacto de tokens por modelo (`gpt-4o`, `claude-3-5-sonnet`, `gemini-1.5-pro`) con `tiktoken` y fallback sintáctico.
- **Escáner Preventivo de Secretos (`domain/scanning/security.py`)**: Detección de claves AWS, API keys de OpenAI/Anthropic, GitHub tokens y credenciales DB.
- **Exportador Portable (`ctxmap export`)**: Generador de volcados planos en formato XML (compatible Repomix), JSON o Markdown.
- **Internacionalización**: Documentación bilingüe [`README_EN.md`](README_EN.md).

---

## [1.7.0] — 2026-08-13

### ✨ Nuevo — Contexto global personal operativo (BD + agentes multi-IDE)

- **BD personal consolidada (`ctxmap personal`) completada**:
  - `sync --todos` descubre proyectos de forma **recursiva** incluyendo
    Google Drive (Mi unidad en cualquier letra de unidad) + flag `--rutas`
    (adicionales separadas por ';') + proyecto directo y contenedor a la vez
    (ej. `H:\...\GitHub`). Verificado: 8 proyectos · 1390 eventos.
  - **Nombre consistente del proyecto**: `vault-<X>` > frontmatter `project`
    > carpeta — un proyecto ya no se duplica con el nombre de la carpeta
    local (ej. PruebaContext vs ContextMap).
  - `export` sin wikilinks a notas inexistentes (sin nodos fantasma).
- **Tool MCP `personal_query`**: el agente (Hermes) consulta la BD personal
  (FTS5) con pocos tokens y filtro por proyecto, sin terminal.
- **Adaptación multi-IDE** (el proyecto se adecúa al IDE): `adapt` enseña a
  cada entorno a usar el CLI — AGENTS.md (sección "Contexto GLOBAL personal"),
  CLAUDE.md (punto 4) y Cursor rules (bullet).
- **Punto de control de versión**: `refresh`/`build` verifican el PROGRAMA
  antes de actualizar el CONTEXTO y avisan con el comando exacto (idea del
  usuario: "ContextMap siempre actualizado").
- **CI/CD con GitHub Actions** (pytest bloqueante + ruff bloqueante) + badge
  de estado — publicación 100% profesional.
- **Lienzo arreglado** (`00-MAPA-MENTAL.canvas`): dedup por archivo,
  agrupación por sección y aristas reales (18 tarjetas únicas · 34 aristas).
- **Deuda técnica del scanner limpiada**: backlog (5.1) y brief (CONTEXT.md)
  sin TODOs de código ruidosos.
- **Extras visuales tolerantes a permisos** (fix Linux CI: `PermissionError
  '/.context-map'`).
- **Fix cross-platform**: test de resolución de ruta BD en Windows.

Suite: 101/101 verdes · ruff 100 % limpio · CI verde.

---

## [1.6.0] — 2026-08-13

### ✨ Nuevo — Base de datos personal consolidada (`ctxmap personal`)

- **BD personal SQLite + FTS5 transportable**: un solo archivo `personal.db`
  que consolida eventos, lecciones y decisiones de TODOS los proyectos.
  Resolución de ruta por jerarquía: `--db` > `CTXMAP_PERSONAL_DB` > disco F:
  montado y escribible (Linux `/mnt/fdrive`, Windows `F:\`) > fallback
  `~/.context-map/personal/personal.db`. `journal_mode=DELETE` para operar
  seguro en pendrives/USB; backup = copiar un archivo.
- **Comando `ctxmap personal`** con 5 subcomandos:
  - `sync` — consolida un proyecto (`.`) o todos (`--todos`) en la BD;
    upsert idempotente por hash SHA-256 (re-sync nunca duplica).
  - `add "texto" --tipo leccion|decision` — captura conocimiento al vuelo
    con `--proyecto`, `--contexto` y `--tags`.
  - `query "términos"` — búsqueda full-text (FTS5, BM25) sobre eventos,
    lecciones y decisiones, filtrable por `--proyecto`; reduce tokens de
    consulta de histórico 80–95 % (solo trae fragmentos relevantes).
  - `export` — genera un vault personal Obsidian (`vault-Personal`) desde
    la BD, sin tocar los vaults de proyecto.
  - `backup --destino <ruta>` — copia la BD a un pendrive/disco externo.
- **Conexión proyecto ↔ global automática**: cada `build`/`scan`/`refresh`
  consolida el proyecto en la BD personal de forma tolerante (nunca rompe
  el flujo ni falla en CI sin F:).
- **Módulo nuevo**: `context_map/core/personal/bd.py` + comando en
  `application/commands/personal.py`, 100 % stdlib (sqlite3), alineado con
  la clean architecture del AGENTS.md.
- **Aislamiento de tests**: `conftest.py` redirige `CTXMAP_PERSONAL_DB` a
  una BD temporal por test — la suite jamás contamina la BD real.
- **8 tests nuevos** (idempotencia, FTS5, resolución de ruta, tolerancia);
  suite completa 96/96 verdes, ruff 100 % limpio.

---

## [1.5.0] — 2026-08-11

### ✨ Nuevo — Confiabilidad del contexto (lección del incidente Gemini)

- **Verificación del PROYECTO correcto en AGENTS.md**: el protocolo de inicio
  ordena confirmar que el vault del proyecto es el correcto antes de responder —
  evita el error de responder con el contexto de OTRO proyecto (incidente
  Gemini/mi-app-utm 2026-08-11: Antigravity estaba en c:/mi-app-utm y respondió
  pendientes de ese vault cuando el usuario preguntaba por ContextMap).
- **Sección "Estado del Contexto" en el brief**: compara la fecha del último
  build (`state/last_build.json`) contra el diario manual más reciente
  (`7.0-MANUAL/Diario/`). Si el diario es más nuevo → aviso "el contexto puede
  estar desactualizado: ejecuta `ctxmap refresh .` ANTES de responder".
  Implementación: `_chequear_frescura()` en `briefs/brief.py`.
- **Pendientes del backlog manual en el brief**: el CONTEXT.md ahora combina
  los pendientes conversados con el usuario (`7.0-MANUAL/BACKLOG.md`, zona
  protegida) con los TODOs del código (nodos FUTURO). Antes el brief solo
  mostraba TODOs del scanner y podía decir "No hay tareas pendientes" cuando
  el backlog manual sí tenía trabajo pendiente. Implementación:
  `_extraer_pendientes_manuales()` en `briefs/brief.py`.
- **Versión del proyecto en el brief**: se detecta desde pyproject.toml /
  package.json y se muestra en el Resumen Ejecutivo.
- **Protocolo de lectura obligatorio en la skill** (`contextmap-skill.md`):
  sección "🧭 PONERSE EN CONTEXTO CORRECTAMENTE" — orden de lectura (brief →
  frescura → backlog manual → diario → 5.0-BACKLOG → riesgos → código) y regla
  anti-error: NUNCA responder "¿qué quedó pendiente?" basándose solo en un
  documento suelto (auditoría, CHANGELOG, docs/).
- **Tests de regresión**: `test_brief_protocolo_anti_error_proyecto_equivocado`
  y `test_brief_refleja_pendientes_manuales_y_frescura` (79 tests verdes).

---

## [1.4.0] — 2026-08-11

### ✨ Nuevo

- **Servidor MCP (`ctxmap mcp`)**: expone las 9 herramientas como tools MCP
  (refresh, scan, build, check, import_git, import_chat, import_sessions,
  adapt, context) para Hermes/Claude/Cursor. Registrable con
  `hermes mcp add ctxmap --command ctxmap --args mcp`.
- **8.0-KNOWLEDGE (aprendizaje del agente)**: zona protegida con el
  conocimiento accionable — cada nota con formato fijo (🎯 Lección · 🛠️ Cómo
  se resolvió · 💬 Prompt específico · 📋 Instrucción específica · 🔗
  Conexiones).
- **Regla MEMORIA VIVA**: ContextMap es la memoria del proyecto — el agente
  documenta AUTOMÁTICAMENTE lo conversado (nota del día + knowledge) sin
  esperar a que se lo pidan. Regla en AGENTS.md, skill del vault y skill de
  Hermes.
- **Grupos de color del grafo**: `.obsidian/graph.json` → `colorGroups` por
  tag, sección y dominio temático (funciona con frontmatter). Snippet CSS de
  etiquetas autogenerado (`colored-tags.css`, se activa solo).
- **Dominios temáticos por proyecto** (`.context-map/dominios.yaml`): define
  los GRUPOS reales del contexto con palabras clave; cada nota se etiqueta
  `grupo-<dominio>`. Incluye el dominio `raiz` (la esencia del proyecto).
- **Aviso automático de actualizaciones**: `ctxmap check`/`build`/`refresh`
  comparan la versión local con el último tag de GitHub (caché 24h) y avisan
  si hay actualización pendiente con el comando para actualizar.
- **Importador de sesiones de Hermes arreglado**: lee `state.db` moderno
  (started_at/timestamp) y filtra por proyecto (`--project` — evita
  contaminar el vault con sesiones de otros proyectos).
- **AGENTS.md generado con memoria viva**: los proyectos nuevos nacen con la
  regla completa (documenta automáticamente + nota del día + 8.0-KNOWLEDGE +
  humaniza todos los archivos).

### 🧹 Mejorado

- **Vault humanizado completo**: filtro de TODOs del scanner fuera de las
  ideas (`_es_todo_scanner`), riesgos deduplicados (`_clave_dedup_riesgo`),
  historial compacto (mensajes de commits reales), batches de completadas
  solo con ideas reales, etiquetas inline bajo los títulos.
- **Nota del día protegida**: si el agente la escribió con alma (`preserve:
  true`), el build NUNCA la pisa — el scanner solo anexa los nodos nuevos.

### 🐛 Corregido

- `_leer_dominios` sin pyyaml (el entorno del binario no lo traía) — mini-
  parser de fallback, nunca rompe el build.
- Importar sesiones sin filtro contaminaba el vault (88 nodos ajenos
  eliminados del estado; el filtro por proyecto evita que vuelva).

---

## [Unreleased]

### ✨ Nuevo

- **Brief con alma (`CONTEXT.md`)**: El brief ejecutivo ahora abre con **"¿Qué es y por qué existe?"** — extrae el propósito real del proyecto desde `README.md` y obliga al agente a responder las 3 preguntas del alma (¿por qué existe?, ¿para qué sirve?, ¿qué cumple?) desde el vault `1.0-PROPOSITO`. Un brief puro de métricas era "pésimo, no decía nada" y el agente del IDE lo ignoraba.
- **"Cómo trabajar aquí — dale vida al contexto"**: Reemplaza la "Estructura Recomendada" genérica por un protocolo accionable: leer brief + vault, revisar riesgos, inspeccionar código real y **actualizar el mapa después de trabajar** para que el contexto nunca muera.
- **Detección de IDE por proceso activo**: `detectar_ide_proceso()` lista los procesos del sistema (tasklist/ps) y detecta Cursor, VS Code, Windsurf, JetBrains y Antigravity **corriendo ahora**, aunque el proyecto no tenga su carpeta de configuración. `ctxmap adapt` los reporta como "IDEs por proceso activo" y genera sus reglas.
- **`ctxmap refresh` — contexto al día en 1 paso**: scan + build (preservando manuales, SIN `--clean`) + check. Reemplaza el protocolo de 4 comandos: `python -m pytest && ctxmap refresh .`.
- **Zona protegida `.manual/` en el vault**: `build --clean` JAMÁS borra el trabajo manual. Preserva la carpeta `.manual/` completa, cualquier nota con frontmatter `preserve: true`, y el backlog manual previo. Reporta cuántas notas preservó. El `00-INDICE.md` enlaza las notas de `.manual/`.

### 🔄 Cambiado

- **AGENTS.md — separación QUÉ / CÓMO (arquitectura de niveles)**: El template ahora
  solo da instrucciones de QUÉ hacer (leer contexto, explorar vault, importar historia,
  3 preguntas del alma, mantener vivo) y referencia la skill. El CÓMO (comandos exactos
  y metodología para escribir notas con alma) vive en **`.context-map/contextmap-skill.md`**,
  generada por `generar_skill_contextmap()`. Aplica a ambos generadores (`briefs/agents.py`
  y `domain/ecosystem/adaptador.py`). El brief `CONTEXT.md` queda como estado/datos y
  referencia la skill en vez de listar comandos.
- **Pre-commit hook**: ahora usa `build --brief` (SIN `--clean`) para no destruir notas manuales (antes `--clean` las borraba en cada commit).
- **`ctxmap check` — Salud del Vault**: reporta nº de notas manuales, vaults activos y alerta si el último build usó `--clean` (destructivo) con cuántas notas preservó (`state/last_build.json`).
- **`generar_brief()` acepta `project_dir`**: extrae el propósito del README del proyecto real (robusto ante invocaciones con target temporal, p. ej. tests).

---

## [1.3.0] - 2026-08-07

### ✨ Nuevo

- **`ctxmap ingest` — Ingesta de documentos externos (segundo cerebro / LLM Wiki)**: Convierte archivos MD/TXT/PDF en nodos `DOCUMENTO` con síntesis extractiva, concepto dominante y citas referenciadas. Nuevo tipo de nodo `DOCUMENTO` y sección `3.2-DOCUMENTOS` en el vault (respeta topología en árbol).
- **`ctxmap adapt` — Adaptación al ecosistema agéntico**: Detecta el stack técnico del proyecto (lenguaje, framework, test runner, package manager, entrypoints desde `pyproject.toml`) y los IDEs/harnesses presentes, y genera reglas específicas por agente:
  - `AGENTS.md` contextual (estándar universal: Antigravity, Cursor, Claude, Copilot, OpenCode, Codex, Gemini)
  - `CLAUDE.md` (Claude Code), `.cursor/rules/contextmap.mdc` + `.cursorrules` (Cursor), `.windsurfrules` (Windsurf), `.clinerules` (Cline), `.roo/rules/contextmap.md` (Roo Code), `GEMINI.md` (Gemini CLI), `opencode.json` (OpenCode), `.aider.conf.yml` (Aider), `.github/copilot-instructions.md` (Copilot)
  - Ecosistema `.hermes/` completo (config.yaml, workflows, shields, triggers)
  - **3 modos**: `respect` (no toca existentes), `--merge` (anexa bloque `<!-- CONTEXTMAP:BEGIN/END -->` preservando reglas del usuario, idempotente), `--overwrite` (reemplaza completo)
- **Auto-adaptación en `init` y `build`**: tras inicializar o construir, ContextMap detecta y crea reglas faltantes automáticamente.

### 🔄 Cambiado

- **Topología estricta en árbol (REGLA INAMOVIBLE)**: Cada nota del vault cuelga de EXACTAMENTE UN padre; las ramas 2.1-Pendientes / 2.2-Futuras / 2.3-Completas son independientes y nunca se cruzan. Índices de concepto con nombre único por estado (`DEVOPS-Pendientes.md` ≠ `DEVOPS-Completas.md`) para evitar que Obsidian fusione estados. `00-CONEXIONES.md` sin wikilinks en modo jerárquico.
- **Nombres de nota idea únicos por id**: `idea_{id}_{ACCION}.md` (antes `idea_{timestamp}_{ACCION}.md` colisionaba si dos ideas del mismo concepto se creaban el mismo segundo).
- **Pre-commit hook usa el código local** (`python -m context_map.cli build`) antes que el binario global `ctxmap` desactualizado.
- **Vault único por proyecto**: los vaults obsoletos se mueven a `.context-map/_legacy/`.

### ✅ Añadido

- **Test de topología inamovible** (`test_topologia_arbol.py`): verifica 0 nodos sin padre, 0 colisiones de nombre base, 0 enlaces rotos e índices con sufijo de estado.
- Tests de ingesta (`test_ingest.py`) y de ecosistema (`test_ecosistema.py`): 45 tests en verde.

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

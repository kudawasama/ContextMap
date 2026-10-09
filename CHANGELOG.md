# Changelog — Context Map

Todas las notas de versión y cambios destacables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.9.2] — 2026-10-09

### 🐛 Arreglado

- **`sync` idempotente (P2.4)**: `_hash_evento` guardaba la firma cruda
  `type|text[:80]|source`; si el texto del evento tenía saltos de línea, la marca
  de procesado se partía en varias líneas en `processed_events.txt` y **nunca
  volvía a coincidir**, así que esos eventos se **reprocesaban en cada `sync`**
  (el resumen mostraba `nodos 333 -> 344` de forma perpetua, aunque el dedup
  mantuviera el grafo). Ahora es una **huella sha1** del texto completo: el
  segundo `sync` reporta **0** eventos nuevos.
  - *Nota*: el primer `sync` tras actualizar reprocesa una vez (formato de marca
    nuevo) y a partir de ahí el grafo es estable.

### ✅ Tests

- `test_sync_idempotencia.py` (3); suite **396**.

## [2.9.1] — 2026-10-09

### 🐛 Arreglado

- **Canvas determinista (P2.3)**: `00-MAPA-MENTAL.canvas` usaba `uuid4()` para los
  ids de nodos y aristas, así que el vault cambiaba en **cada** build e impedía
  comparar versiones o verificar por hash (frenaba cualquier auditoría). Ahora los
  ids derivan del contenido con `uuid5`: mismo grafo → **mismo lienzo byte a byte**
  (verificado en el proyecto real y con tests).
- **Ruido de 191 «TODO» históricos**: la limpieza debía hacerse en la **fuente**
  (`.context-map/raw/events.jsonl`), no solo en el grafo derivado — el `sync`
  reinyectaba los eventos. Archivados **193 eventos** (y sus nodos) con copia de
  seguridad; verificado que no vuelven en refrescos consecutivos. Se conservan los
  **3** marcadores reales de comentarios.
  - La búsqueda personal de ContextMap ya no devuelve docstrings como pendientes.

### ✅ Tests

- `test_canvas_determinista.py` (3); suite **391**.

## [2.9.0] — 2026-10-08

### 🧠 Búsqueda semántica de contexto (P1.3)

- `ctxmap search` / tool MCP `context_search` **fusionan BM25 con similitud
  semántica** (peso 0.5): una paráfrasis sin solape léxico (“amnesia entre
  sesiones”) recupera su página (“memoria viva del proyecto”).
- Sin `sentence-transformers` el comportamiento es **BM25 puro** (cero regresión);
  la opción se puede desactivar con `ctxmap search --no-semantico` o
  `context_search(..., semantico=False)`.
- **Núcleo reutilizable**: el índice vectorial (caché por hash, coseno, degradación
  elegante) se extrae a `core/vectorial.py` y lo comparten la **wiki** (G3) y la
  **búsqueda de contexto** (P1.3); cada una con su propia caché
  (`state/embeddings.json` y `state/embeddings-contexto.json`).
- Tests: `test_busqueda_semantica.py` (4, con codificador falso y verificación de
  caché); los 8 de embeddings de la wiki siguen verdes tras el refactor.

## [2.8.1] — 2026-10-08

### ⚡ Rendimiento del build (P2.1 del plan de revisión)

El benchmark de escala demostró que el cuello **no era el almacenamiento** (el
`graph.jsonl` son 0,3–4,5 MB) sino **algoritmos**:

- **Deduplicación de riesgos**: `distancia_levenshtein` era O(n²) en Python puro
  (44,5 M llamadas a `min()`). Ahora usa **corte por cota matemática** (si
  `0.6·jaccard + 0.4 < umbral`, ningún Levenshtein lo salvaría), recorte de
  prefijo/sufijo común y límite con salida temprana. El resultado es **idéntico**
  (verificado: misma deduplicación y 0 discrepancias en 59 pares).
- **`_safe_filename`, `_archivo_en_titulo` y `_minusculas` memoizadas**: se
  invocaban entre **1,1 y 2,3 millones** de veces por build.
- `conexiones_de_nodo`: invariante sacado del bucle interno.

| Nodos | Antes | Ahora |
|---|---|---|
| 300 | 17,9 s | **5,5 s** |
| 1.000 | >180 s (no terminaba) | **14,3 s** |
| 10.000 | no terminaba en 30 min | **17,6 min** (genera 7.817 notas) |

**Conclusión**: SQLite **no** era la respuesta; el límite restante a 10k nodos es
el render del vault (miles de ficheros). Hasta ~2.000–5.000 nodos es ágil.

## [2.8.0] — 2026-10-08

### 🔎 Búsqueda de contexto con citas (P1.1)

- Nueva **`ctxmap search "<tema>"`** y tool MCP **`context_search`**: BM25 local
  sobre **nodos del grafo + notas del vault**, devolviendo los pasajes más afines
  con su **cita** (`nodo:<id>` o la ruta real del fichero). El agente recupera lo
  que necesita en vez de leer ficheros completos. Sin red y sin dependencias.
- Nuevo paquete `domain/retrieval/` (`buscar_contexto`, `formatear_resultados`).

### 📉 Brief por capas (P1.2)

- `ctxmap build --brief` genera **dos capas**: `CONTEXT.md` (completo) y
  `CONTEXT.min.md` (identidad + estado + títulos de riesgos y pendientes + cómo
  ampliar). **Medido en este proyecto: 1.860 tk → 797 tk (−57,2%)**.
- La tool MCP `context` acepta **`minimo=True`** y el CLI tiene **`ctxmap brief --min`**.

### ✅ Tests

- `test_busqueda_contexto.py` (6) y `test_brief_minimo.py` (4); **386** en total.

## [2.7.4] — 2026-10-08

### 🧰 Visibilidad del peso (P0.2/P0.3 del plan de revisión)

- **`ctxmap doctor --sizes`**: desglose del peso de `.context-map` por áreas
  (vault, historial, archivo comprimido, estado, `_legacy`…) con aviso si supera
  el tope. También en `--json`.
- **`ctxmap check`**: nueva línea **«📦 Peso del contexto»** con el total, los
  snapshots vivos y las áreas principales; avisa si el contexto pasa de 100 MB o
  de 200 snapshots vivos (con sugerencia accionable).
- Módulo `domain/health/pesos.py` (medición testeada; nunca lanza excepción).

### 🗜️ Archivo de snapshots: un tar por mes

- El archivado de la retención creaba **un tar pequeño por cada poda** (≈22 KB,
  una por build) → habría vuelto a acumular cientos de ficheros. Ahora se
  completa **un único `maps/archive/<YYYY-MM>.tar.gz`** al mes (fusión atómica con
  `os.replace`, sin duplicar nombres). Consolidados aquí: 461 snapshots en un tar
  de 5,7 MB.
- Limpieza: restos de `.tmp-tests` (85 directorios vacíos).

### 🧩 Paquete de pi: `@kudawa/pi-contextmap`

- Publicado en npm el paquete que trae ContextMap a [pi](https://pi.dev):
  extensión que **registra el servidor MCP** (avisa si falta el CLI), skill
  `contextmap` y los prompts `/contextmap-contexto`, `/contextmap-cierre` y
  `/contextmap-preguntar`.
- Install: `pi install npm:@kudawa/pi-contextmap`. Repo propio con publicación
  automática en npm por **Trusted Publishing (OIDC, sin tokens)**:
  https://github.com/kudawasama/pi-contextmap
- Guía: `docs/PI_PACKAGE.md`. (El nombre `pi-contextmap` fue rechazado por npm
  por parecido a `pi-context-map`; se publicó con ámbito `@kudawa`.)

## [2.7.3] — 2026-10-08

### 🚀 Rendimiento y peso

- **Retención de snapshots del historial**: el build escribía un snapshot en
  *cada* ejecución (482 ficheros y 54 MB = 93% del peso de `.context-map`, con el
  grafo en 0,3 MB). Ahora:
  - **Idempotencia**: si el mapa no cambió desde el último snapshot, no se crea otro.
  - **Retención**: se conservan los 20 más recientes **y** el último de cada uno
    de los últimos 7 días.
  - **Archivo**: el resto se comprime en `maps/archive/<fecha>-<n>snapshots.tar.gz`
    (nada se borra; `CTXMAP_SNAPSHOT_ARCHIVE=0` para borrar en su lugar).
  - Configurable: `CTXMAP_SNAPSHOT_KEEP`, `CTXMAP_SNAPSHOT_KEEP_DAYS`.
- **Resultado medido**: `.context-map` **59 MB → 16 MB**; snapshots 485 → 26, con
  459 archivados en un `.tar.gz` de 5,5 MB (compresión ~10×). Coste: 2 ms.
- Tests: `test_snapshots_retencion.py` (7); suite **369/369**.

## [2.7.2] — 2026-10-08

### 🐛 Arreglado

- **Ruido de TODO en el Diario**: `render_nota_dia` volcaba los TODO del código
  (`TODO (ruta.py:Ln): …`) en la nota del día. Ahora aplica el mismo filtro
  `_es_todo_codigo` que ya usaban backlog, historial e ideas: la deuda técnica
  vive en `5.0-BACKLOG/5.1-Tareas`, no en el diario.
- **Falsos positivos del extractor de TODO**: en archivos `.py` se analizan
  **solo comentarios reales** con `tokenize` (un docstring o un string que
  *menciona* el marcador ya no cuenta) y `**TODO**` en negrita Markdown dejó de
  parecer un comentario. Descubierto al documentar el propio filtro, que generó
  nodos fantasma.
- Tests: `test_analyzers_content.py` (8) y `test_diario_consolidado.py` (6);
  suite **362/362**.

## [2.7.1] — 2026-10-08

### 🐛 Arreglado

- **Acentos en el portapapeles (Windows)**: `ctxmap inbox add --clipboard` leía la
  salida de PowerShell con la codificación de la consola (cp850) y corrompía el
  texto (`Recuperación` → `Recuperaci¢n`). PowerShell ahora fuerza salida UTF-8 y
  la lectura se decodifica **siempre** como UTF-8. Detectado al estrenar el
  Second Brain con una captura real (`·`, tildes y eñes).
- **Respuestas extractivas con ruido**: `wiki ask` citaba títulos Markdown,
  avisos de redirección y bloques de fórmulas (`\displaystyle`) en lugar de la
  definición. `wiki._frases` descarta estructura y ruido matemático y devuelve
  prosa limpia (sin `**`, sin `[texto](url)`, sin viñetas).

## [2.7.0] — 2026-10-07

### 🗺️ G8 y G9 evaluados: BM25 ya estaba · MOC en una sola pasada

- **G8 (`personal query`)**: el ítem pedía evaluar BM25 y **ya estaba
  implementado** (`bm25(fts) AS puntaje ORDER BY puntaje` en
  `core/personal/bd.py`). Se cierra con un test de regresión de relevancia
  (`test_buscar_ordena_por_relevancia_bm25`).
- **G9 (MOC por concepto)**: se **descarta** fragmentar el índice en páginas por
  concepto (cada nota debe colgar de un único padre → ruido en el grafo). En su
  lugar, `generar_moc` ahora lee cada resumen **una sola vez** (antes releía
  todos los resúmenes por cada concepto: O(conceptos × resúmenes)). Criterio de
  revisión documentado: ~25 conceptos o ~40 resúmenes.
- Tests: `test_moc_agrupa_conceptos_con_sus_fuentes` y la regresión de BM25.

### 🤖 Síntesis generativa con LLM opcional (G6 · plan v2.7)

- Nuevo módulo `domain/knowledge/llm.py`: hook de generación con cliente HTTP
  **sin dependencias** (stdlib `urllib`) contra cualquier endpoint compatible
  con la API de OpenAI.
- `wiki.sintetizar` acepta `generador` (hook inyectable) y `usar_llm`; la
  respuesta se marca con `motor` (`extractivo` | `llm`) y, cuando el LLM actúa,
  se conserva `respuesta_extractiva` para trazabilidad. Ante cualquier fallo
  vuelve a la extracción local.
- CLI: `ctxmap wiki ask --llm|--no-llm` y `ctxmap wiki llm [--probar] [--json]`.
- MCP: `knowledge_wiki_ask` acepta `llm` (por defecto `false`: nunca red).
- Configuración por entorno: `CTXMAP_LLM_API_KEY`, `CTXMAP_LLM_MODEL`,
  `CTXMAP_LLM_BASE_URL`. Guía: `docs/LLM.md`. Tests: `test_llm_opcional.py` (12).

### 📥 Web Clipper real (G5 · plan v2.7)

- Nuevo módulo `domain/knowledge/clip.py`: **portapapeles nativo**
  (`pbpaste` · PowerShell `Get-Clipboard` · `wl-paste`/`xclip`/`xsel`) y
  **bookmarklet** de una línea que copia `- [título](url)` + selección.
- `ctxmap inbox add --clipboard` captura el portapapeles en el inbox, con
  **título legible** y **URL como fuente** desglosados del enlace Markdown.
- `ctxmap inbox bookmarklet [--html] [--json]` imprime el bookmarklet y genera
  `.context-map/clip-bookmarklet.html` (enlace arrastrable a favoritos).
- El texto posicional de `inbox add` pasa a ser opcional (`--clipboard` y
  `--stdin` ya no exigen argumento).
- Guía de uso: `docs/WEB_CLIPPER.md`. Tests: `test_web_clipper.py` (10).

### 🔧 Hooks de Git con el intérprete del proyecto

- Los hooks `pre-commit`/`post-commit` usan el `python` del venv del proyecto
  (o `uv run python`) antes que el `python` global del PATH: elimina avisos
  falsos en cada commit cuando faltan extras (`pymupdf`, etc.).
- Regresión cubierta en `test_hooks.py` (`test_hooks_usan_el_interprete_del_venv`).

### 🧠 Búsqueda semántica opcional en la wiki (G3 · plan v2.7)

- Nuevo módulo `domain/knowledge/embeddings.py`: índice vectorial **opcional**
  con `sentence-transformers` detectado en tiempo de ejecución. Sin la librería
  nada cambia: `wiki query` / `wiki ask` siguen con BM25.
- `wiki.consultar` **fusiona** BM25 normalizado + similitud semántica, así una
  paráfrasis sin solape léxico recupera su página manteniendo las citas.
- Índice cacheado en `.context-map/state/embeddings.json` con invalidación por
  *hash* del contenido (si la wiki no cambia, no se recalcula).
- Nuevo `ctxmap wiki embeddings [--rebuild] [--json]` y tool MCP
  `knowledge_wiki_embeddings` para diagnosticar/precalcular.
- **Cero dependencias base y cero red en `build`**: no se crea extra (el CI usa
  `uv sync --all-extras`); la instalación es opt-in del usuario.
- Tests: `test_embeddings_opcionales.py` (8); suite **327/327**.

### 🔍 OCR opcional de PDF escaneado (G2 · plan v2.7)

- Si un PDF no tiene capa de texto, `ingest` intenta OCR **best-effort** con
  `pytesseract` + `Pillow` + binario `tesseract` (detección en tiempo de
  ejecución, sin dependencias base). Si falta cualquier pieza, mensaje
  accionable; nunca revienta la ingesta.
- Tests: `test_ingesta_rica.py` (2 nuevos); suite **319/319**.

### 📄 Ingesta de `.docx` sin dependencias (G1 · plan v2.7)

- `ctxmap ingest <archivo.docx>` extrae el texto con `zipfile` +
  `ElementTree` (un `.docx` es un ZIP con `word/document.xml`), **sin
  dependencias externas**.
- Un `.docx` corrupto produce un `ValueError` con mensaje claro.
- Añadido a las extensiones soportadas en lote (`.docx`).
- Tests: `test_ingesta_rica.py` (6); suite **317/317**.

### 🔧 `check`: sin falso positivo de carpeta de tests (G7 · plan v2.7)

- La sugerencia "Agregar una carpeta de pruebas (tests/)" usaba una lista de
  directorios sin `context_map/__tests__`, así que se mostraba en proyectos con
  los tests dentro del paquete. Ahora usa `DIRECTORIOS_TESTS` (el mismo criterio
  que la señal "Tests").

### 🗺️ Plan v2.7 documentado

OCR de PDF, embeddings opcionales (fallback BM25), captura móvil, Web Clipper y
síntesis LLM opcional, todos como **extras opcionales** (local-first). Ver
`7.0-MANUAL/MEJORAS/PLAN-MEJORA-v2.7-2026-10-07.md`.

---

## [2.6.0] — 2026-10-07

### 🐛 Corregido (P0) — el brief ya no puede ser "extranjero"

- **`export`**: `exportar_contexto` invocaba `generar_brief` sin `output_path`,
  por lo que el default `.context-map/CONTEXT.md` (relativo al CWD)
  **sobrescribía el brief del proyecto real** con el de un proyecto temporal
  — tanto al ejecutar `ctxmap export` como al correr la suite de tests. Ahora
  el brief se genera siempre dentro del proyecto exportado.
- **`check`**: la detección de nombre fragmentado compara ahora también el
  **H1 del brief** (`# <Proyecto> — Brief para Agentes`) además del
  frontmatter, de modo que un brief ajeno se reporta en el readiness.

### ✨ Humanización de las notas narrativas (F7)

- Nuevo módulo `core/normalization/humanizacion.py` con predicados de ruido:
  métricas del scanner (`Proyecto 'X' — N archivos`), TODOs crudos, mensajes
  de chat/IDE (por `source`, no solo por texto) y entrypoints de directorios
  de trabajo/scratch.
- `1.1-Mapa-Mental-Narrativo`: el diagrama global ya no muestra métricas del
  scan, TODOs ni mensajes de conversación.
- `1.3-Proposito`: las REGLAS del proyecto se muestran como principios (sin
  el resumen plantilla de la ingesta); el ruido ya no entra.
- `2.4-Ideas-Relevantes`: sin TODOs crudos del código mezclados con ideas.

### 🧠 Puente knowledge → agentes (F8)

- **`wiki.listar_paginas()`**: API pública que lista resúmenes y entidades con
  su wikilink, para exponer el Second Brain sin cargar su contenido.
- **`brief.extractors.panorama_conocimiento()`**: resume la wiki (páginas +
  total + inbox pendiente) para el brief.
- El brief (`CONTEXT.md`) incorpora la sección **"Conocimiento Relevante
  (Second Brain)"** en su **bloque dinámico** (después del boundary de
  prompt-cache), sin romper el prefijo invariante.
- La tool MCP `context` devuelve esa sección automáticamente: los agentes ya
  ven el conocimiento capturado por el usuario.
- Con wiki vacía, la sección guía la captura sin romper el build.

### 🧭 Wiki 2.0 — síntesis extractiva, contradicciones y MOC (F9)

- **`wiki ask`** (CLI) / **`knowledge_wiki_ask`** (MCP): respuesta **extractiva
  y local** (sin LLM ni red) que encadena las frases más afines de la wiki y
  cita cada fuente como `[n]`. Determinista y trazable.
- **Lint de contradicciones**: detecta la misma afirmación apareciendo afirmada
  y negada en páginas distintas (aviso, no error).
- **MOC** (`wiki moc` / `knowledge_wiki_moc`): mapa de contenido autogenerado
  (cada concepto con las fuentes que lo tratan); se regenera en cada ingesta y
  cuelga del índice `05-WIKI.md`.
- Nuevas tools MCP: `knowledge_wiki_ask`, `knowledge_wiki_moc` → **26 tools**.

### 🔎 Recuperación BM25 (F10)

- El ranking de `wiki query` / `wiki ask` pasa de solape de tokens a **BM25**
  (k1=1.5, b=0.75): pondera frecuencia del término, su rareza (IDF) y la
  longitud del documento.
- Tokenización **insensible a acentos**: `recuperacion` encuentra `recuperación`.
- Sin dependencias nuevas: matemática local y determinista.

### 🔁 Repaso espaciado SM-2 (F11)

- Nuevo módulo `domain/knowledge/review.py`: algoritmo **SM-2** local.
- `ctxmap review due` (qué toca hoy) y `ctxmap review grade "<página>" <0-5>`
  (califica y reprograma). Estado en `.context-map/state/review.json`.
- El brief muestra **"Repaso pendiente (SM-2)"** cuando hay páginas vencidas.
- Nuevas tools MCP: `knowledge_review_due`, `knowledge_review_grade`.

### 🌐 Ingesta rica (F12)

- **HTML local**: `ctxmap ingest <archivo.html>` convierte la página guardada
  por el navegador a Markdown (mismo extractor stdlib que `--url`).
- **Video genérico**: `ctxmap ingest --video <url>` (yt-dlp para cualquier
  sitio soportado; `--youtube` se mantiene por compatibilidad).
- **Captura por stdin**: `ctxmap inbox add -` (o `--stdin`) permite pegar desde
  el portapapeles o un bookmarklet sin plugins.

### 🧪 Tests

- Nuevo `test_ingesta_rica.py` (4 tests): HTML local, extensión soportada,
  alias `--video` y captura por stdin.
- Nuevo `test_review.py` (5 tests): SM-2 (primer acierto, fallo, secuencia),
  páginas vencidas y persistencia del estado.
- Nuevo `test_wiki_avanzado.py` (7 tests): síntesis con citas, sin-match,
  determinismo, contradicciones y MOC.
- Nuevo `test_brief_identidad.py` (3 tests): el export no contamina el CWD;
  un brief extranjero se detecta; un brief coherente no da falsos positivos.
- Nuevo `test_humanizacion.py` (2 tests): predicados de ruido + verificación
  de que 1.1/1.3/2.4 no muestran ruido y sí el contenido legítimo.
- Nuevo `test_conocimiento_brief.py` (3 tests): el panorama lista páginas e
  inbox, y el conocimiento entra en el bloque dinámico del brief.
- Suite: **314/314** verdes (antes 290); `ruff` y `mypy` limpios.

### 📝 Documentación

- Conteo real unificado en `README.md`, `README_EN.md` y `README_TECNICO.md`:
  **314** tests y **28** herramientas MCP (antes 288 y 16).

---

## [2.5.0] — 2026-09-28

### 🧠 Modo Conocimiento (PKM): Second Brain + LLM Wiki en islas separadas

Fusión del enfoque del curso de Obsidian (vault + Second Brain de Tiago Forte +
patrón LLM Wiki de Karpathy) con la memoria de proyecto de ContextMap, **sin
colisionar**: dos `namespace` ortogonales (`code` y `knowledge`), un solo vault,
cero wikilinks cruzados y doble topología validada por test.

- **feat(`vault`) F1**: Esqueleto del mundo PKM `90-CONOCIMIENTO/` (PARA +
  WIKI) sembrado de forma idempotente; campo `namespace` en `Node`;
  `90-CONOCIMIENTO` en `ZONAS_MANUALES` (el build jamás lo borra); el render
  filtra por namespace y el test valida la doble topología con 0 cruces.
- **feat(`inbox`) F2**: Comandos `ctxmap inbox add|list|move|purge` — captura
  cruda y clasificación heurística PARA con actualización de wikilinks (sin
  enlaces rotos al mover). Módulo `domain/knowledge/inbox.py` y 4 tools MCP
  (`knowledge_inbox_add/list/move`, `knowledge_purge`).
- **feat(`wiki`) F3**: LLM Wiki — `ctxmap wiki ingest|query|lint` con páginas de
  resumen, entidades (upsert canónico), entry log y ranking **con citas** para
  respuestas trazables. Módulo `domain/knowledge/wiki.py` y 3 tools MCP.
- **feat(`captura`) F4**: Captura de fuentes tipo Web Clipper —
  `ctxmap ingest --url <web>` (HTML→Markdown con stdlib) y `--youtube <video>`
  (transcripción vía yt-dlp con fallback de cliente). Tool MCP `knowledge_ingest`.
- **feat(`obsidian`) F5**: Config real de Obsidian — `.obsidian/community-plugins.json`,
  `core-plugins.json`, `daily-notes.json` (nota del día → inbox) y
  `templates/nota-pkm.md`, sembrados idempotentes. **`.obsidian` pasó a zona
  preservada**: la configuración del usuario (plugins, tema) ya no se pierde en
  cada build (verificado con `--clean`). Doc de sync móvil en `8.0-KNOWLEDGE`.
- **Helpers compartidos**: `domain/knowledge/indices.py` (slugs, enlaces, índices)
  reutilizado por inbox y wiki.
- **fix(`models`)**: `Node.to_dict` omite el `namespace` por defecto para no
  romper binarios/herramientas previas al rehidratar (`Node(**data)`).
- **fix(`diario`)**: `render_nota_dia` conserva el contenido del agente que está
  DESPUÉS de la sección del scanner (antes se descartaba al reescribir).
- **fix(`hooks`)**: Los hooks pre/post-commit priorizan el código local
  (`python -m context_map.cli`) sobre el binario global desactualizado.
- **fix(`scanner`)**: `_es_ruta_test` ignora carpetas/archivos de prueba al
  recolectar TODOs y medir complejidad; filtro de ruido semántico en chats
  (`es_mensaje_ruido`) y blindaje de `_es_todo_codigo` (summary/evidence).
- **test**: Suite **288/288** (nuevos: `test_inbox`, `test_wiki`,
  `test_captura`, `test_obsidian_config`, `test_hooks` de local-first,
  `test_diario_consolidado` de preservación). 0 errores ruff y mypy.
## [2.4.1] — 2026-09-26

### 🔧 Correcciones — Refresco automático del watcher restaurado

- **fix(`watcher`)**: `_ejecutar_refresco_default` entrega ahora un `argparse.Namespace` (`target`, `project`, `quiet=True`) a `cmd_refresh` en lugar del `dict` anterior. Tanto `cmd_refresh` como los comandos que delega (`cmd_scan`, `project_name`) acceden a `args.target` / `args.project` como atributos, así que el daemon fallaba ante cada cambio de archivo con `'dict' object has no attribute 'target'` y **el refresco automático nunca llegaba a ejecutarse**: el contexto solo se actualizaba con un `ctxmap refresh` manual. Con `quiet=True` el daemon además deja de imprimir el banner de refresh en cada evento.
- **fix(`refresh`)**: `cmd_refresh` normaliza mappings entrantes a `SimpleNamespace` (aceptando `target` o `target_dir`, más `project`/`quiet`/`clean`), como red de seguridad para llamadores externos que aún pasen un diccionario.
- **test**: dos pruebas de regresión en `context_map/__tests__/test_watcher.py` (contrato de atributos del callback por defecto y normalización de mappings). La primera falla con el código previo y pasa con el arreglo. PR #6.

---

## [2.4.0] — 2026-09-23

### 🚀 Evolución Arquitectónica, Modularización, Prompt Caching Determinista & Skills Nativas

- **refactor(`personal`)**: Modularización completa del módulo monolítico `personal.py` (1.054 líneas) en el subpaquete desacoplado `context_map/application/commands/personal/` (`common.py`, `sync.py`, `export.py`, `query.py`, `panorama.py`, `timeline.py`, `repair.py` e `__init__.py`) bajo Clean Architecture y principio de responsabilidad única (SRP), garantizando retrocompatibilidad y soporte dinámico de monkeypatching en tests.
- **feat(`brief`/`caching`)**: Optimizador determinista de Prompt Caching para Claude 3.7 Sonnet, Gemini 2.5 Pro/Flash y GPT-4o en `CONTEXT.md`. Congela un prefijo invariante estático de 1.005 tokens (identidad, propósito y reglas inmutables) sin marcas de tiempo volátiles al inicio, inyecta el delimitador formal `<!-- PROMPT_CACHE_BOUNDARY: INVARIANT_PREFIX -->` y sitúa el bloque dinámico al final, logrando una tasa de Cache Hit >90%, reducción de latencia de 4s a <500ms y recorte de costos en 90%.
- **feat(`ecosystem`/`antigravity`)**: Generador nativo de la skill oficial de Antigravity en `.agents/skills/contextmap/SKILL.md` con frontmatter YAML estándar (`name: contextmap`) y directivas de memoria viva, complementado con el flujo declarativo `.hermes/workflows/contextmap.yaml`.
- **perf(`scanner`)**: Acelerador de escaneo incremental en `infrastructure/analyzers/content.py` con persistencia de caché sintáctica `.context-map/.scan_cache.json` basada en huellas `(mtime_ns, size)`, permitiendo re-escaneos sub-150ms.
- **ci(`mypy`)**: Saneamiento de 39 inconsistencias de tipado estricto (0 errores en 190 archivos) y promoción de MyPy a verificación 100% bloqueante en `.github/workflows/ci.yml`.
- **feat(`personal`)**: Nuevo comando `ctxmap personal panorama` para visualización ejecutiva del estado de actividad real de todos los proyectos con semáforo inteligente (`max(max_ts_ses, max_ts_ev)`), conteo de pendientes y directrices activas.
- **feat(`personal`)**: Nuevo comando `ctxmap personal timeline` para inspección cronológica unificada de sesiones de IA, commits y cambios relevantes con filtros por días, proyecto o tipo de evento.
- **feat(`personal`)**: Nuevo comando `ctxmap personal repair` para saneamiento automatizado de eventos de ruido técnico, deduplicación/fusión de proyectos duplicados, optimización de índices FTS5 y `VACUUM` de SQLite con respaldo previo `.bak`.
- **feat(`personal`)**: Exportación del Vault Personal v2 con notas ricas por proyecto, manejo determinista de colisiones de slugs y saneamiento de enlaces para 0 wikilinks rotos.
- **feat(`memory`/`multichannel`)**: Auto-importación multicanal de memoria viva en `ctxmap refresh .`: integración automática y tolerante de sesiones de Antigravity IDE (`~/.gemini/antigravity-ide/brain/`), exportaciones de chat externas en `.context-map/chats/` y auto-ingesta de documentos de dominio en `.context-map/raw/docs/` (`.md`, `.txt`, `.pdf`) como nodos `DOCUMENTO` en el grafo y Vault (`3.2-DOCUMENTOS/`), garantizando preservación histórica total.
- **test**: 264/264 pruebas unitarias pasando al 100% con suite de verificación de auto-ingesta multicanal, Prompt Caching y caché de escaneo incremental.

---

## [2.3.0] — 2026-08-21

### 🛡️ Novedades y Mejoras — Escáner de Secretos Avanzado, Entropía Shannon, Opt-Out Ollama & Automatización Release

- **feat(`security`)**: Detección ampliada de credenciales con soporte para Slack tokens (`xoxb-`), Stripe keys (`sk_live_`, `sk_test_`), Twilio SIDs (`AC`, `SK`), SendGrid (`SG.`), npm access tokens (`npm_`) y webhooks de Discord.
- **feat(`security`)**: Análisis matemático de alta entropía de Shannon (`calcular_entropia_shannon`) en asignaciones de variables sensibles para detectar llaves criptográficas no estructuradas.
- **feat(`ollama`)**: Soporte de opt-out mediante flag `--no-ollama` en `ctxmap enrich` y variable de entorno `CTXMAP_NO_OLLAMA=1` para forzar análisis puramente offline y estático AST.
- **feat(`ci/cd`)**: Creación automática de GitHub Releases (`softprops/action-gh-release@v2`) con notas generadas al publicar tags en `publish.yml`, y principio de mínimo privilegio en permisos de `docs.yml`.
- **feat(`personal`)**: Soporte para la variable `CTXMAP_GDRIVE_ROOTS` en `personal sync` y optimización de búsqueda acotada de unidades en Windows.

---

## [2.2.2] — 2026-08-21

### 🔧 Correcciones y Hardening — Saneamiento Técnico y Parche

- **fix(`enrich`)**: Persistencia real en disco de los docstrings generados en `ctxmap enrich` vía `filepath.write_text` con formateo adecuado de indentación y soporte completo para flag `--dry-run` de previsualización sin alterar archivos.
- **refactor(`complexity`/`cyclomatic`)**: Eliminación de la duplicación de código entre `domain/analysis/complexity.py` y `domain/analyzers/cyclomatic.py`. Consolidación unificada de métricas ciclomáticas de McCabe en `domain/analyzers/cyclomatic.py` (con soporte AST completo para `AsyncFor`, `AsyncWith`, `Assert`, `IfExp`, `BoolOp`).
- **security(`adaptador`)**: Endurecimiento de `_es_generado_ctxmap` para exigir estrictamente el marcador `CONTEXTMAP:BEGIN` evitando falsos positivos con archivos de usuario.
- **security(`hermes`)**: Parametrización segura de cláusulas `LIMIT ?` en SQLite para defensa en profundidad.
- **devops(`pre-commit`)**: Actualización de `.pre-commit-hooks.yaml` para invocar el módulo local `python -m context_map.cli` en lugar del binario global.
- **docs(`domain_extractor`)**: Corrección de docstrings clarificando análisis de frecuencia léxica local en lugar de TF-IDF.

---

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

## [Histórico · 2026-08] Brief con alma y zona protegida (sin versión asignada)

> Entradas de esa etapa que quedaron sin versión asignada. Se conservan tal cual
> (memoria del proyecto); el encabezado deja de confundirse con «Unreleased».

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

## [Histórico · 2026-08] Plan de Refactorización 5.2 (F0–F4, sin versión asignada)

> Entradas de esa etapa sin versión asignada. Se conservan tal cual.

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

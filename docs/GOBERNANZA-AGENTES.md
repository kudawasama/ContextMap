# Gobernanza de Agentes — Detalle y ejemplos

> Documento de **referencia** de [`AGENTS.md`](https://github.com/kudawasama/ContextMap/blob/master/AGENTS.md). `AGENTS.md` contiene
> las normas obligatorias (tersas y autosuficientes); aquí vive el **detalle**, los
> **diagramas** y los **ejemplos** que no hacen falta en cada sesión.

## 2. Arquitectura de Código (Clean Architecture Jerárquica)

El código de `context_map` se organiza por responsabilidad única en la convención
`modulo/submodulo/archivo.py`:

```
context_map/
├── core/                        # Fundamentos del dominio
│   ├── models/                  # Dataclasses (Node, Edge, Event)
│   ├── parsing/                 # Parser de eventos y deserialización JSONL
│   ├── storage/                 # Persistencia JSONL y snapshots
│   ├── normalization/           # Estandarización y clasificación semántica
│   └── generators/              # Generadores de resúmenes y Contexto Narrativo
├── domain/                      # Lógica de negocio
│   ├── scanning/                # Escáner estático del proyecto
│   ├── synchronization/         # Sincronización incremental del grafo
│   ├── ingestion/               # Ingesta de documentos externos (MD/TXT/PDF → DOCUMENTO)
│   ├── ecosystem/               # Detección de stack/IDE y adaptación de reglas agénticas
│   ├── analysis/                # Análisis de readiness del sistema
│   ├── health/                  # Diagnóstico y mantenimiento (doctor)
│   └── reporting/               # Reportes semanales de avance
├── application/                 # CLI y orquestación
│   ├── cli/                     # Parser principal de argumentos CLI
│   └── commands/                # Comandos unificados (build, scan, sync, etc.)
├── infrastructure/              # Integraciones externas
│   ├── integrations/            # Git, Hermes, Antigravity, Chat exports
│   └── analyzers/               # Analizadores AST de estructura y contenido
└── presentation/                # Generación de salidas visuales
    ├── vault/                   # Generador de Vault Obsidian (atomic, consolidated, templates)
    └── briefs/                  # Generador de CONTEXT.md para Agentes
```

## 3. Protocolo de Inicio para Agentes (Ponerse en Contexto)

Cualquier agente que tome una tarea **DEBE** seguir estos pasos antes de escribir
o modificar código:

1. **Verificar el PROYECTO correcto**: el vault de ESTE proyecto es
   `.context-map/vault-ContextMap/`. Si el usuario pregunta por OTRO proyecto
   (p. ej. mi-app-utm) o por un vault que no es este, dilo ANTES de responder —
   nunca respondas con el contexto de otro proyecto.
2. **Leer el Brief Ejecutivo**: consultar `.context-map/CONTEXT.md` para conocer
   métricas, riesgos críticos y tareas pendientes.
3. **Comprobar la FRESCURA del contexto**: si el brief avisa de que el diario
   manual es más nuevo que el build (sección "Estado del Contexto"), ejecuta
   `ctxmap refresh .` ANTES de responder sobre el estado del proyecto.
4. **Leer los PENDIENTES REALES y DOCUMENTOS**: además del backlog generado
   (5.0-BACKLOG), revisa SIEMPRE `.context-map/vault-ContextMap/7.0-MANUAL/BACKLOG.md`,
   los documentos de dominio en `.context-map/vault-ContextMap/3.2-DOCUMENTOS/` y el
   diario más reciente (`7.0-MANUAL/Diario/`). Los pendientes conversados y el
   conocimiento documental viven ahí.
5. **Revisar el Backlog y Vault**:
   `.context-map/vault-ContextMap/2.0-IDEAS/2.1-Ideas-Pendientes/` y `5.0-BACKLOG/5.1-Tareas.md`.
6. **No Suponer Rutas o Lógica**: inspeccionar el código fuente antes de formular
   hipótesis de cambio.
7. **Captura Autónoma del Dominio y Documentación**: al inicializar o ponerse en
   contexto, inspeccionar los submódulos de lógica nuclear (algoritmos, ecuaciones
   implícitas, reglas de negocio) y documentar lo descubierto en
   `7.0-MANUAL/DOMINIO.md` o en las notas del Vault. Para fuentes documentales
   externas (.pdf, .md, .txt), depositarlas en `.context-map/raw/docs/` y ejecutar
   `ctxmap refresh .`.
8. **Memoria Viva Multicanal**: todo chat de Antigravity IDE, Hermes o exportación
   depositada en `.context-map/chats/` se procesa automáticamente en
   `ctxmap refresh .` para preservar decisiones y evitar pérdida de contexto histórico.

> ⚠️ **NUNCA respondas "¿qué quedó pendiente?" basándote solo en un documento
> suelto (auditoría, CHANGELOG, docs/)** — cruza SIEMPRE el brief + backlog manual
> + diario más reciente + documentos ingeridos. Esa es la fuente de verdad.

## 4. Topología Estricta en Árbol para Obsidian (Graph View)

> **Esta es la regla MÁS IMPORTANTE del renderizador. Ningún agente, refactor o
> "mejora" puede violarla. El Graph View de Obsidian DEBE verse como un árbol
> puro: cada nota cuelga de EXACTAMENTE UN padre; las ramas de ideas pendientes
> (2.1), futuras (2.2) y completadas (2.3) son INDEPENDIENTES y NUNCA se cruzan
> entre sí ni con otras secciones.**

### 4.1 Estructura del Árbol (obligatoria)

```
00-INDICE.md                      ← raíz (padre de todos)
├── 1.0-PROPOSITO/                ← sección raíz
│   └── 1.1, 1.2, 1.3             ← hojas → SOLO a su sección padre
├── 2.0-IDEAS/                    ← sección raíz
│   ├── 2.1-Ideas-Pendientes/     ← RAMA INDEPENDIENTE
│   │   └── DEVOPS/DEVOPS-Pendientes.md      ← índice de concepto (nombre ÚNICO)
│   │       └── idea_*.md                     ← nota → SOLO a su índice
│   ├── 2.2-Ideas-Futuras/        ← RAMA INDEPENDIENTE (solo si hay activas)
│   │   └── CONCEPTO/CONCEPTO-Futuras.md
│   ├── 2.3-Ideas-Completas-e-Implementadas/  ← RAMA INDEPENDIENTE
│   │   └── DEVOPS/DEVOPS-Completas.md
│   │       └── 01-DEVOPS-01-10.md            ← batch → SOLO a su índice
│   └── 2.4-Ideas-Relevantes.md
├── 3.0-ESTRUCTURA/ → 3.1
├── 4.0-RIESGOS/ → notas de riesgo
├── 5.0-BACKLOG/ → 5.1
└── 6.0-HISTORIAL/ → 6.1, 6.2, 6.3
```

### 4.2 Reglas Obligatorias (violarlas = bug)

1. **CADA NOTA TIENE EXACTAMENTE UN PADRE** (árbol puro). El padre se materializa
   como el ÚNICO wikilink con `⬅` (pie "Volver a..."). Ningún nodo enlaza a más de
   un nivel superior, ni a nodos hermanos, ni entre secciones de estado, ni a
   `00-INDICE.md` (salvo las 6 secciones raíz).
2. **Nivel 0 (`00-INDICE.md`)**: enlaza **únicamente** a los 6 Nodos de Sección
   Raíz (`1.0`, `2.0`, `3.0`, `4.0`, `5.0`, `6.0`).
3. **Nivel 1 (Secciones Raíz `X.0`)**: enlazan a `00-INDICE.md` (su padre) y a sus
   sub-nodos `X.Y` (sus hijos). Nada más.
4. **Nivel 2 y Nodos Hoja**: enlazan **exclusivamente a su Sección Padre** vía el
   pie `⬅ Volver a ...`. NUNCA de regreso a `00-INDICE.md`.
5. **Índices de concepto con nombre ÚNICO por estado**:
   `{CONCEPTO}-Pendientes.md`, `{CONCEPTO}-Futuras.md`, `{CONCEPTO}-Completas.md`.
   NUNCA `{CONCEPTO}.md` a secas: Obsidian fusiona archivos con el mismo nombre
   base y mezclaría ideas pendientes con completas.
6. **PROHIBIDO enlazar por nombre corto ambiguo**: todo wikilink a un índice de
   concepto usa su nombre único completo (con sufijo de estado). Las notas de idea
   muestran el concepto como texto plano (`` ``Concepto`` ``), SIN wikilink
   adicional al índice (el pie ya enlaza al padre).
7. **Los batches de ideas completadas** se nombran `NN-CONCEPTO-INICIO-FIN.md` y su
   índice DEBE enlazar a los batches reales (nunca a `idea_*.md` inexistentes →
   nodos fantasma).
8. **Enlaces a sub-secciones condicionales**: `2.0-IDEAS.md` solo enlaza a
   `2.1` / `2.2` / `2.3` si existen nodos de ese estado. Enlaces rotos = nodos
   fantasma = bug.
9. **`00-CONEXIONES.md` en modo jerárquico** se renderiza SIN wikilinks
   (`con_wikilinks=False`): los nombres de archivo del modo jerárquico no derivan
   del slug del título, así que los wikilinks crearían nodos fantasma.

### 4.3 Verificación Automática (inamovible)

- El test `context_map/__tests__/test_topologia_arbol.py` DEBE pasar antes de
  cualquier commit. Comprueba: 0 nodos sin padre (excepto `00-INDICE.md` y
  `00-CONEXIONES.md`), 0 colisiones de nombre base, 0 wikilinks rotos y que cada
  índice de concepto termina en `-Pendientes/-Futuras/-Completas.md`.
- El **pre-commit hook** regenera el vault con el código LOCAL
  (`python -m context_map.cli build`) — NUNCA con el binario global `ctxmap`
  desactualizado. Si el vault generado no pasa 4.3, el commit está roto.

### 4.4 Vault ÚNICO por proyecto

- El vault activo es `.context-map/vault-<NombreProyecto>` (ej: `vault-ContextMap`,
  sin guión extra). El nombre lo resuelve el repo GitHub.
- PROHIBIDO acumular vaults paralelos obsoletos (`vault-Context-Map`,
  `vault-TestAuto`, etc.): los que no se regeneran por `build` se mueven a
  `.context-map/_legacy/` o se eliminan. Solo debe existir UN vault por proyecto
  para que Obsidian no mezcle grafos.
- **Sincronización Multi-Vault**: todo cambio en `build` debe renderizarse en
  `.context-map/vault/` y en `.context-map/vault-<project>/` simultáneamente para
  que la vista de Obsidian se actualice en tiempo real.

## 5. Metodología de Contexto Narrativo con Alma

Toda nota generada para una entidad del Vault debe invocar
`generar_contexto_narrativo(node)` en `context_map/core/generators/generadores.py`
para inyectar su estructura polimórfica según el tipo de nodo:

* **`IDEA`**: ¿Por qué?, ¿De dónde surgió?, ¿Para qué?, ¿Cómo?, y tabla de **Pros y Contras**.
* **`RIESGO`**: ¿Qué riesgo es?, Ubicación, Impacto, Mitigación y **Matriz de Gravedad**.
* **`CAMBIO` / `CORRECCION`**: Modificación realizada, Razón del cambio, Archivos y **Verificación de No-Regresión**.
* **`BASE`**: Componente estructural, **Rol en la Arquitectura** e integraciones.
* **`PRUEBA`**: Funcionalidad validada, Criterios de Aceptación y comando `pytest`.
* **`FUTURO`**: Tarea pendiente (TODO), Ubicación en código y Prioridad.

### 5.1 HUMANIZAR TODOS LOS ARCHIVOS

Al actualizar el contexto, el agente debe revisar y **redactar TODOS los archivos
del vault** (no solo `7.0-MANUAL/`): índices con propósito (no conteos),
narrativas sin plantillas vacías, títulos legibles, riesgos deduplicados, historia
con los mensajes reales, ideas con alma. **Guardar siempre el contexto**: nunca
borrar información con historia ni notas manuales — lo tosco se redacta, no se elimina.

### 5.2 MEMORIA VIVA DEL PROYECTO

ContextMap es la **memoria del proyecto**, mantenida constantemente por el agente:
si durante el trabajo surge una idea, decisión o lección, se **documenta
automáticamente** (sin esperar a que lo pidan) en la nota del día
(`7.0-MANUAL/Diario/`) y, si es reutilizable, como conocimiento accionable en
`8.0-KNOWLEDGE/` (formato: Lección · Cómo se resolvió · Prompt específico ·
Instrucción específica · Conexiones). Lo conversado siempre queda.

## 6. Verificación Obligatoria y Commits

Antes de dar por completada cualquier tarea o comitear en Git:

```bash
.venv/Scripts/python.exe -m pytest                            # 1. tests (100%)
.venv/Scripts/python.exe -m context_map.cli scan .             # 2. escanear
.venv/Scripts/python.exe -m context_map.cli build --clean --brief   # 3. vault + brief
.venv/Scripts/python.exe -m context_map.cli check .            # 4. readiness
.venv/Scripts/python.exe -m context_map.cli doctor . --strict-warn  # 5. reglas fijas
```

El intérprete es **siempre** el del `.venv` del proyecto (regla `REG-EJE-001`): el
`python` global no trae el extra `[mcp]` y hace que la suite se recolecte a medias.

* **Commits**: *Conventional Commits* en español (`feat:`, `fix:`, `refactor:`, `docs:`…).

### 6.1 Reglas de conducta que sí se miden

De las 71 reglas del catálogo, 37 las comprueba la máquina. Cuatro de ellas no
miran el motor, miran **cómo se trabaja**, y viven en
`context_map/domain/health/reglas_proyecto.py`:

| Chequeo | Regla | Qué mide | Qué **no** hace |
|---|---|---|---|
| `commits_convencionales` | `REG-DOC-003` | asunto de los últimos 50 commits no-merge | no reescribe el historial |
| `changelog_commit` | `REG-DOC-004` | el commit de la **punta** que toca código, ¿toca `CHANGELOG.md`? | no mira la deuda vieja, que ya no es accionable |
| `diario_del_dia` | `REG-MEM-002` | si hoy hay commits, ¿hay `Diario/<hoy>.md`? | no escribe el diario |
| `secretos_versionados` | `REG-SEG-001` | patrones de clave en archivos rastreados por git | no imprime el valor, nunca |

Los cuatro son `WARN` y se ignoran entre sí: un chequeo roto no arrastra a los
demás. Los falsos positivos están declarados (`__tests__/`, `conftest.py`,
marcadores `example`/`fake`/`tu-token`), porque un aviso que se repite cada día
deja de leerse.

### 6.2 El repositorio y el vault también se miden

`reglas_calidad.py` mide el **estado del repo** y `reglas_vault.py` el del
**vault**. Son doce chequeos más, y con ellos **53 de las 71 reglas** tienen
verificación automática:

| Chequeo | Reglas | Qué mide |
|---|---|---|
| `version_documentada` | `PUB-001` | la versión de `pyproject.toml` está en el CHANGELOG |
| `derivados_fuera_de_git` | `LIM-003` | ni vault, ni estado, ni bases en el índice de git |
| `raiz_limpia` | `ARQ-002` | la raíz solo lleva lo declarado en la norma |
| `capas_respetadas` | `ARQ-001`, `ARQ-003` | las cinco capas existen y los imports no suben de capa |
| `modulos_con_test` | `ARQ-004` | todo submódulo de `domain/` aparece en un test |
| `docstrings_y_tipos` | `DOC-002` | docstring por módulo y suelo de anotaciones |
| `idioma_de_la_documentacion` | `DOC-001` | los documentos están en español |
| `dominio_documentado` | `DOC-005` | hay `7.0-MANUAL/DOMINIO.md` y no es un esqueleto |
| `fuentes_procesadas` | `DOC-006`, `MEM-001` | ninguna fuente de `raw/`/`chats/` es más nueva que el brief |
| `lecciones_completas` | `MEM-003` | cada lección tiene sus cinco secciones |
| `notas_sin_plantilla` | `HUM-001`, `HUM-005` | sin marcadores de plantilla ni relleno |
| `vault_acotado` | `LIM-001` | el vault no pasa de 15 MB |

Tres decisiones que conviene no deshacer:

1. **`capas_respetadas` es un trinquete.** La arquitectura real tiene deuda
   (imports `application <-> infrastructure`), y negarlo sería peor que
   congelarlo: `MAX_IMPORTS_CRUZADOS` fija el número de hoy y una violación
   nueva rompe la puerta. El tope **solo puede bajar**.
2. **Los umbrales se declaran con su número.** `TOPE_SIN_TIPOS = 0.20` y
   `TOPE_INGLES = 0.10` no son verdad revelada: son el suelo medido para que la
   regla no nazca en rojo ni deje de vigilar. Se bajan cuando se limpia.
3. **Una plantilla no se juzga como nota.** Las de `templates/` o `Plantilla-*`
   llevan `{{title}}` por definición; el chequeo las salta.

Lo que sigue en `manual` (18 reglas) no es lo que falta por medir: es lo que
**ocurre en la conversación** —pedir permiso antes de `adapt` o de `push`,
enseñar la salida real en vez del autoreporte, cruzar cuatro fuentes antes de
decir qué queda—. Eso no deja huella en el repositorio; se audita leyendo la
sesión.

## Auto-diagnóstico (doctor)

Antes de trabajar, el agente ejecuta `ctxmap doctor --json` (o `ctxmap check .`).
`check` = readiness del proyecto; `doctor` = salud del entorno + auto-reparación.
El arranque de sesión no se fuerza por hook: la skill base y `AGENTS.md` lo exigen.

### 6.3 Reglas de sesión: la bitácora

Las reglas que hablan de la sesión —diagnosticar antes de tocar, cerrar con la
puerta en verde, no reescribir reglas ni publicar sin permiso— no se pueden leer
en el código: ocurren en la conversación. Hasta ahora solo se podían creer de
palabra. La solución no fue bajar el listón, fue **fabricar la evidencia**: cada
comando de la CLI anota una línea en `.context-map/state/bitacora.jsonl`
(`context_map/core/audit/bitacora.py`).

La entrada es mínima a propósito: instante, comando, código de salida, duración,
banderas relevantes, número de notas del vault y si había permiso. Nunca copia
rutas de datos ni contenido.

| Chequeo | Reglas que cubre | Qué mide | Qué **no** hace |
|---|---|---|---|
| `bitacora_sesion` | `INI-001`, `INI-002`, `EJE-002`, `SAL-002` | brief leído, diagnóstico previo al primer commit del día y última puerta en verde | no juzga lo que el agente dice en el chat |
| `permisos_explicitos` | `EJE-004`, `SAL-003`, `PUB-003` | `adapt`, `doctor --fix` y `push` ejecutados sin `--confirmar` | no bloquea el comando: deja constancia |
| `tag_con_puerta_verde` | `PUB-002` | que el tag publicado tenga un doctor en verde previo | no reescribe ni retira tags |
| `secreto_en_el_historial` | `SEG-003` | credenciales **reales** en el historial (no en fixtures) | nunca imprime el valor |
| `historia_preservada` | `HUM-002` | caída de notas entre dos `build` consecutivos | no restaura: avisa |
| `doctor_rapido` | `LIM-002` | duración del último doctor (límite 120 s) | no acota el vault |
| `decisiones_con_porque` | `DOC-007` | decisiones guardadas en la memoria personal **sin** el campo `contexto` | no juzga si la decisión era relevante |

Tres decisiones que no conviene deshacer:

1. **Un registro cerrado no puede exigir evidencia retroactiva.** Ni los commits
   anteriores a la primera entrada de la bitácora ni los tags creados antes de
   que existiera se juzgan. Convertir el pasado en deuda produce un rojo
   perpetuo, y un rojo perpetuo enseña a ignorar el aviso.
2. **El valor del secreto no se copia al mensaje.** Se informa el tipo y el
   commit. Un reporte que reproduce la credencial la propaga al log.
3. **Un fixture no es una credencial.** Las coincidencias que solo aparecen en
   pruebas y documentación se cuentan aparte, con su nombre. Y se buscan las
   **expresiones reales**, no subcadenas: buscar `AKIA` a secas marcaba la propia
   definición del detector como si fuera una clave de AWS.

`DOC-007` entró por la única rendija medible: una decisión guardada sin
`--contexto` no explica su porqué, y eso el registro lo dice sin ambigüedad. No
se juzga si la decisión era relevante — eso es criterio, no dato.

Lo que sigue sin medirse, y por qué: cruzar cuatro fuentes (`INI-004`),
inspeccionar el código antes de proponer (`INI-006`), buscar en la memoria de
otros proyectos (`INI-007`), distinguir evidencia de autoreporte (`EJE-005`) y
anunciar el costo de una tarea larga (`LIM-004`). Dependen de lo que el agente **piensa y escribe**, no de lo que el
repositorio guarda. Fingir un chequeo ahí sería medir otra cosa con el mismo
nombre.

## 7. Etiquetas (tags) — creación y formato

Las etiquetas son el índice vivo del vault: una etiqueta mal escrita no rompe
ningún test, solo desaparece del grafo y de la búsqueda. Por eso son regla fija
y las audita `ctxmap doctor` (`vault_tags`).

**Formato obligatorio** (lo aplica `core/normalization/cleaning.py`):

| Regla | Correcto | Incorrecto |
|---|---|---|
| Minúsculas | `basededatos` | `BaseDeDatos` |
| Solo `a-z`, `0-9`, `-` y `:` | `context-map` | `context map`, `v2.7` |
| Un nivel de prefijo con `:` | `class:fix` | `class:fix:urgente` |
| Sin acentos ni eñes | `diseno` | `diseño` |
| Sin duplicados | `["ideas","ideas"]` → una | duplicadas |

* **Toda nota del vault declara `tags:` en su frontmatter.** Sin `tags:` la nota
  es invisible para el índice; el chequeo `vault_tags` la marca en WARN.
* **Crear una etiqueta nueva** = `kebab-case`, en singular y en el idioma del
  proyecto (aquí, español o el término técnico en inglés ya asentado:
  `basededatos`, `tui`, `context-map`). Nunca dos formas del mismo concepto:
  si existe el sinónimo, se añade a `TAG_MERGE` y se usa el canonónico.
* **Prohibidas** (`TAGS_ELIMINAR`): `todo`, `otro`, `docstring`, `__init__.py`.
  No informan de nada y ensucian el grafo.
* **Etiqueta de clasificación**: todo nodo del grafo lleva `class:<id>`
  (`class:fix`, `class:feature`…), inferido por `normalization/inference.py`.
  No se escribe a mano: la pone el motor.
* Antes de inventar una etiqueta, se busca si ya existe (`ctxmap search` o
  `/tags` del vault). Una etiqueta nueva que nadie más usa es ruido.

## 8. Documentación obligatoria

Un cambio sin documentar es un cambio que la próxima sesión va a repetir.

| Qué | Dónde | Cuándo |
|---|---|---|
| Decisión y su porqué | `docs/plans/` o nota de decisión | al decidir |
| Lógica nuclear del dominio | `7.0-MANUAL/DOMINIO.md` | al tocar el núcleo |
| Cambio visible | `CHANGELOG.md` (`[Unreleased]`, Keep a Changelog) | en el mismo commit |
| Norma nueva del proyecto | `AGENTS.md` (contrato) + `docs/GOBERNANZA-AGENTES.md` (detalle) | antes de la regla |
| Fuente externa | `.context-map/raw/docs/` + `ctxmap refresh .` | al ingerirla |
| Lo que pasó hoy | `7.0-MANUAL/Diario/YYYY-MM-DD.md` | al cerrar sesión |

* El `CHANGELOG.md` no se rellena al final: entra en el mismo commit que el
  cambio, con el tipo correcto (`Corregido`, `Añadido`, `Cambiado`, `Eliminado`).
* `7.0-MANUAL/DOMINIO.md` describe **cómo decide el sistema**, no la lista de
  archivos. Si el código y el documento discrepan, gana el documento hasta que
  alguien demuestre lo contrario con una prueba.
* Nada de documentación duplicada: un solo sitio por asunto y enlaces entre
  ellos, no copias.

## 9. Humanización de la prosa

El vault lo lee una persona (y un agente que debe entenderla). Una plantilla sin
redactar no es contexto: es ruido con formato.

* **Todos los archivos del vault se redactan**: índice, nota, resumen. Nada de
  «TODO: describir», «lorem», ni tablas con celdas vacías.
* **No se borra historia**: lo tosco se corrige, no se elimina.
* **Ruido fuera** (lo descartan los predicados de `normalization/humanizacion.py`):
  métricas repetitivas del scanner, `TODO`/`FIXME` crudos, mensajes de chat,
  entrypoints de carpetas de scratch y resúmenes plantilla.
* **Contexto narrativo por tipo**: `IDEA`, `RIESGO`, `CAMBIO`/`CORRECCION`,
  `BASE`, `PRUEBA`, `FUTURO`. Cada uno cuenta qué es, por qué importa y qué
  sigue; no todos con la misma frase.
* La prosa va **en español técnico profesional**: directo, sin relleno, sin
  «obviamente» ni signos de admiración.

## 10. Memoria viva y Second Brain

* Chats y exportaciones van a `.context-map/chats/` y se procesan en
  `ctxmap refresh .`; no se copian a mano al vault.
* El **Second Brain** se responde con citas (`knowledge_wiki_ask`): una respuesta
  sin fuente es una invención. Si no hay pasaje que lo respalde, se dice.
* Antes de preguntar «qué hicimos con X», se busca en la memoria multi-proyecto
  (`personal_query`): las lecciones de otros proyectos aplican a este.
* Lección reutilizable → `8.0-KNOWLEDGE/` con el formato Lección · Cómo se
  resolvió · Prompt · Instrucción · Conexiones. Una lección sin instrucción
  accionable no es lección.
* **Pendientes nunca con una sola fuente**: `7.0-MANUAL/BACKLOG.md` +
  `7.0-MANUAL/Diario/` + `5.0-BACKLOG/5.1-Tareas.md` + `3.2-DOCUMENTOS/`.

## 11. Secretos y datos sensibles

* **Nunca** un secreto en el repo, en el vault ni en un brief: ni claves, ni
  tokens, ni cadenas de conexión, ni datos personales de terceros.
* Los secretos se inyectan por el proxy (`core/secrets/proxy.py`:
  `entorno_con_secretos`) y la salida se sanea (`sanear_salida`) antes de
  escribirla o exportarla.
* El vault de secretos (`core/secrets/vault.py`) exige `cryptography`; sin ella
  **no** se cae a texto plano: se falla con un mensaje claro.
* Si un secreto aparece en el historial de git, se rota. Borrar el commit no
  basta: el objeto sigue ahí.
* Los IDs de variables se validan sin colisión (`validar_ids_sin_colision`)
  antes de exportar el entorno: dos claves con el mismo prefijo se pisan.

## 12. Publicación y versionado

* La versión vive en `pyproject.toml` y se refleja en el mismo commit en
  `CHANGELOG.md`. `version_local()` lee el `pyproject.toml` del árbol fuente:
  el binario editable no manda.
* Un cambio de comportamiento sube al menos el *minor*; una corrección, el
  *patch*. Se etiqueta `vX.Y.Z` **después** de la puerta de calidad en verde.
* El paquete de agentes (`@kudawa/pi-contextmap`) lleva su propia versión y su
  propia `SKILL.md` genérica (`vault-<Proyecto>`, sin nombres de proyecto); la
  skill específica del proyecto se genera en `.agents/skills/` del repo y **no**
  se publica en `~/.agents` cuando el proyecto es el home.
* `push` y `tag` solo con confirmación explícita del dueño.

## 13. Límites y rendimiento

* Un vault de más de ~15 MB o ~1.000 notas deja de ser «un contexto»: se
  mantiene acotado (build por secciones, `--brief` para el agente).
* El `doctor` debe terminar en minutos, no colgarse: los proyectos enormes
  (p. ej. gobernanza con 20 MB) necesitan modo acotado en lugar de un barrido
  completo silencioso.
* No se commitean artefactos derivados: `.context-map/state/`,
  `.context-map/history/`, `.context-map/vault-*/` regenerable y los `.db`.
* Las tareas caras (scan completo, ingesta, embeddings) se anuncian antes de
  ejecutarse: el dueño decide si paga el tiempo.

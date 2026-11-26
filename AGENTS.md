# Instrucciones para Agentes de IA — Context Map

Normas obligatorias para **todos** los agentes (Antigravity, Cursor, Hermes,
Claude, Windsurf, Copilot…). El detalle, los diagramas y los ejemplos viven en
[`docs/GOBERNANZA-AGENTES.md`](docs/GOBERNANZA-AGENTES.md).

---

## 1. Reglas globales
* **Idioma**: español técnico profesional en respuestas, comentarios y docstrings.
* **Docstrings** formales (Google / PEP 257) y **Type Hinting** estricto en Python.
* **Raíz limpia**: sin archivos sueltos. La raíz solo lleva lo declarado en
  `RAIZ_PERMITIDA` (`context_map/domain/health/reglas_calidad.py`): los README,
  `LICENSE`, `pyproject.toml`, `AGENTS.md`, `CLAUDE.md`, `CHANGELOG.md`,
  `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `Makefile`, `mkdocs.yml`,
  `action.yml`, `.pre-commit-hooks.yaml`, `.gitignore` y `uv.lock`. Un archivo
  nuevo en la raíz se declara en la norma o no existe; lo mide `raiz_limpia`.

## 2. Arquitectura
Clean Architecture jerárquica `modulo/submodulo/archivo.py`:
`core/` (models, parsing, storage, normalization, generators) ·
`domain/` (scanning, synchronization, ingestion, ecosystem, analysis, health, reporting) ·
`application/` (cli, commands) · `infrastructure/` (integrations, analyzers) ·
`presentation/` (vault, briefs). Árbol completo en el doc de gobernanza.

## 3. Protocolo de inicio (obligatorio antes de escribir código)
1. **Proyecto correcto**: el vault de ESTE repo es `.context-map/vault-ContextMap/`. Si preguntan por otro proyecto o vault, dilo **antes** de responder.
2. **Leer el brief**: `.context-map/CONTEXT.md` (o la tool `context(minimo=True)`).
3. **Frescura**: si el brief avisa de diario más nuevo que el build, ejecuta `ctxmap refresh .` antes de opinar sobre el estado.
4. **Pendientes reales**: ejecuta `ctxmap pendientes .` — el motor cruza el
   backlog manual + `5.0-BACKLOG/5.1-Tareas.md` + la última entrada del diario +
   `3.2-DOCUMENTOS/` y te dice qué fuente falta. Cruzar a mano cuatro archivos es
   lo que se olvida; el comando no se olvida (`REG-INI-004`).
5. **Backlog y vault**: `2.0-IDEAS/2.1-Ideas-Pendientes/` y `5.0-BACKLOG/5.1-Tareas.md`.
6. **No suponer rutas o lógica**: inspecciona el código fuente antes de proponer cambios.
7. **Dominio y documentos**: documenta la lógica nuclear en `7.0-MANUAL/DOMINIO.md`; las fuentes externas van a `.context-map/raw/docs/` + `ctxmap refresh .`.
8. **Memoria viva**: los chats/exportaciones en `.context-map/chats/` se procesan en `ctxmap refresh .`.

> ⚠️ Nunca respondas "¿qué queda pendiente?" con un único documento: el cruce
> lo hace `ctxmap pendientes .` (brief + backlog manual + tareas + diario +
> documentos), y si una fuente no existe el comando lo declara en vez de
> suponer que está vacía.

## 4. Topología del vault (Obsidian Graph View) — REGLA INAMOVIBLE
Árbol puro: **cada nota cuelga de EXACTAMENTE UN padre**; las ramas 2.1 / 2.2 / 2.3
son independientes y **nunca** se cruzan.

1. Un único wikilink de padre (el pie `⬅`). Nada de enlaces a hermanos, entre estados, ni a `00-INDICE.md` (salvo las 6 secciones raíz).
2. `00-INDICE.md` enlaza **solo** a las 6 secciones raíz (`1.0`–`6.0`).
3. Secciones raíz `X.0`: enlazan a `00-INDICE.md` y a sus hijos `X.Y`.
4. Hojas y nivel 2: enlazan **solo** a su sección padre; nunca a `00-INDICE.md`.
5. Índices de concepto con nombre único por estado: `{CONCEPTO}-Pendientes/-Futuras/-Completas.md` (nunca `{CONCEPTO}.md`).
6. Wikilinks siempre con el nombre único completo; dentro de la nota el concepto va como texto plano.
7. Batches `NN-CONCEPTO-INICIO-FIN.md`; su índice enlaza a batches reales (nada de nodos fantasma).
8. `2.0-IDEAS.md` solo enlaza a `2.1/2.2/2.3` si existen nodos de ese estado.
9. `00-CONEXIONES.md` en modo jerárquico se renderiza **sin wikilinks**.

* **Verificación (inamovible)**: `context_map/__tests__/test_topologia_arbol.py` DEBE pasar (0 sin padre, 0 colisiones de nombre, 0 wikilinks rotos). El pre-commit regenera el vault con el código **local** (`python -m context_map.cli build`), nunca con el binario global.
* **Vault único**: `.context-map/vault-<NombreProyecto>`; los obsoletos → `.context-map/_legacy/` o se eliminan.

## 5. Contexto narrativo y memoria viva
* Toda nota invoca `generar_contexto_narrativo(node)` (estructura por tipo: IDEA, RIESGO, CAMBIO/CORRECCION, BASE, PRUEBA, FUTURO). Detalle por tipo en el doc de gobernanza.
* **Humanizar**: redacta TODOS los archivos del vault (índices con propósito, sin plantillas vacías). Nunca borres historia ni notas manuales: lo tosco se redacta, no se elimina.
* **Memoria viva**: documenta ideas/decisiones/lecciones del día en `7.0-MANUAL/Diario/` y, si son reutilizables, en `8.0-KNOWLEDGE/` (Lección · Cómo se resolvió · Prompt · Instrucción · Conexiones).

## 6. Verificación y commits

> **Regla fija #0 — intérprete**: todos los comandos se ejecutan con el
> intérprete del venv del proyecto (`.venv/Scripts/python.exe` en Windows,
> `.venv/bin/python` en POSIX). El `python` global no trae el extra `[mcp]`
> (pydantic ≥ 2.13) y hace que la suite se recolecte a medias. Si invocas
> Python a mano, usa el del venv; `make`, cuando existe, lo resuelve solo.

```bash
# 1. Suite completa (con el intérprete del venv)
.venv/Scripts/python.exe -m pytest

# 2. PUERTA DE CALIDAD: reglas fijas (falla con FAIL o WARN)
.venv/Scripts/python.exe -m context_map.cli doctor . --strict-warn

# 3. Vault + brief
.venv/Scripts/python.exe -m context_map.cli build --clean --brief

# 4. Readiness
.venv/Scripts/python.exe -m context_map.cli check .

# 5. ¿Qué queda pendiente? (cruce de las cuatro fuentes)
.venv/Scripts/python.exe -m context_map.cli pendientes .

# 6. Tareas caras: `ingest` y `enrich` se anuncian y exigen --confirmar (REG-LIM-004)

# 7. Traza de lecturas de código (REG-INI-006)
.venv/Scripts/python.exe -m context_map.cli hook lectura . --instalar
#    Si tu harness no tiene hooks, anota lo que abriste con bash/grep:
.venv/Scripts/python.exe -m context_map.cli hook lectura . --ruta <archivo> --origen agente --quiet

# 8. Al informar: la evidencia se lee del registro, no se recuerda (REG-EJE-005)
.venv/Scripts/python.exe -m context_map.cli evidencia .
```

> Al reportar «tests pasan / doctor verde», enseña la salida real: `evidencia`
> dice qué se ejecutó hoy, con qué código y qué puertas faltan. `pytest` no deja
> rastro en la bitácora (no pasa por la CLI) y el informe lo declara fuera de
> alcance en vez de insinuar que lo cubre.

`make` es **opcional** (no está instalado en todas las máquinas): si existe,
`make verify` encadena los pasos 1 y 2 y resuelve el intérprete solo. Los
comandos de arriba son los que siempre funcionan.

* **Commits**: *Conventional Commits* en español (`feat:`, `fix:`, `refactor:`, `docs:`…).

## 7. Reglas fijas de estabilidad (invariantes)

Las reglas que sostienen la confianza en el diagnóstico están declaradas en
`context_map/domain/health/invariantes.py` y se miden con el `doctor`. No son
sugerencias: `ctxmap doctor --strict-warn` devuelve **código 1** si alguna se
incumple, y `make verify` es la puerta que debe estar en verde antes de cerrar.

| Invariante | Chequeo | Severidad | Reparación |
|---|---|---|---|
| `interprete_del_proyecto` | `interpreter` | WARN | usar el Python del `.venv` |
| `dependencias_mcp_importables` | `mcp_deps` | FAIL | `pip install -e ".[mcp]"` |
| `vault_unico_por_proyecto` | `vault_default` | WARN | `ctxmap doctor --fix .` |
| `notas_manuales_intactas` | `manual_notes_preservation` | WARN | `ctxmap doctor --fix .` |
| `topologia_de_arbol` | `topologia` | WARN | `ctxmap build --clean --brief .` |
| `indice_fts5_al_dia` | `vault_index` | WARN | `ctxmap build .` |
| `historial_acotado` | `history` | WARN | `ctxmap history prune .` |
| `contexto_fresco` | `context_freshness` | WARN | `ctxmap refresh .` |
| `etiquetas_del_vault` | `vault_tags` | WARN | corregir `tags:` en la nota señalada |
| `commits_validos` | `commits_convencionales` | WARN | usar `tipo(alcance): asunto` |
| `changelog_al_dia` | `changelog_commit` | WARN | registrar el cambio y commitearlo junto |
| `diario_del_dia` | `diario_del_dia` | WARN | escribir `7.0-MANUAL/Diario/<hoy>.md` |
| `sin_secretos` | `secretos_versionados` | WARN | rotar el secreto y sacarlo del historial |
| `version_anunciada` | `version_documentada` | WARN | anunciar la versión en `CHANGELOG.md` |
| `sin_derivados_versionados` | `derivados_fuera_de_git` | WARN | sacar `.context-map/` del índice |
| `raiz_sin_sueltos` | `raiz_limpia` | WARN | moverlo a su capa o declararlo |
| `capas_sin_retroceso` | `capas_respetadas` | WARN | resolver la dependencia hacia dentro |
| `dominio_con_test` | `modulos_con_test` | WARN | test del submódulo en `__tests__/` |
| `codigo_documentado` | `docstrings_y_tipos` | WARN | docstring de módulo + anotaciones |
| `documentacion_en_espanol` | `idioma_de_la_documentacion` | WARN | traducir o marcar como traducción |
| `dominio_explicado` | `dominio_documentado` | WARN | redactar `7.0-MANUAL/DOMINIO.md` |
| `fuentes_al_dia` | `fuentes_procesadas` | WARN | `ctxmap refresh .` |
| `lecciones_reutilizables` | `lecciones_completas` | WARN | completar las cinco secciones |
| `notas_redactadas` | `notas_sin_plantilla` | WARN | redactar la nota o borrarla |
| `vault_con_peso_acotado` | `vault_acotado` | WARN | podar o `build` por secciones |
| `sesion_con_evidencia` | `bitacora_sesion` | WARN | `ctxmap brief` al empezar y `ctxmap doctor` antes de commitear |
| `permisos_explicitos` | `permisos_explicitos` | WARN | repetir con `--confirmar` tras hablar con el dueño (`adapt`, `ingest`, `enrich`, `push`, `doctor --fix`) |
| `tag_amparado` | `tag_con_puerta_verde` | WARN | doctor en verde y volver a etiquetar |
| `credencial_rotada` | `secreto_en_el_historial` | WARN | rotar la credencial y purgar el historial |
| `historia_conservada` | `historia_preservada` | WARN | restaurar las notas perdidas |
| `diagnostico_rapido` | `doctor_rapido` | WARN | acotar el chequeo que se lleva el tiempo |
| `decision_con_porque` | `decisiones_con_porque` | WARN | completar el porqué al registrar la decisión |
| `codigo_leido` | `lecturas_previas` | WARN | `ctxmap hook lectura . --instalar` y leer antes de tocar |
| `memoria_de_otros_proyectos` | `memoria_consultada` | WARN | `ctxmap personal query "términos" --limite 5` |
| — (test) | `test_evidencia.py` | — | `ctxmap evidencia .` para enseñar la salida real, no la memoria |

* `context_map/__tests__/test_invariantes.py` es el contrato: falla si alguien
  borra o renombra un chequeo que sostiene una regla fija.
* Estas reglas son del **motor**. Las reglas de **negocio** del proyecto van al
  catálogo versionado `references/reglas/reglas_registro.yaml` (IDs `REG-XXX-###`,
  71 reglas en 12 categorías, 66 con verificación automática), que `context_map/domain/reglas/reglas.py`
  convierte en nodos `REGLA` y que el brief mínimo resume en «📜 Reglas fijas».
* Cuatro módulos aportan los 23 chequeos que no son del motor:
  `reglas_proyecto.py` mide **conducta** (commits, CHANGELOG, diario, secretos),
  `reglas_calidad.py` mide el **repo** (versión anunciada, derivados, raíz,
  capas, tests, docstrings, idioma) y `reglas_vault.py` mide el **vault**
  (dominio, fuentes, lecciones, plantillas, peso). `reglas_sesion.py` mide la
  **sesión** leyendo la bitácora (`.context-map/state/bitacora.jsonl`), que la CLI
  escribe sola en cada comando (`context_map/core/audit/bitacora.py`): qué se
  ejecutó, cuándo, con qué código de salida, cuánto tardó y si había permiso.
  Ninguno escribe archivos: lo
  que arreglan es contenido o historial, y eso lo decide una persona.
* `capas_respetadas` lleva **tope de no regresión** (`MAX_IMPORTS_CRUZADOS`):
  la deuda actual está congelada y una violación nueva rompe la puerta. El tope
  solo puede bajar.
* Añadir una regla fija = añadir el chequeo en `doctor.CHECKS` + su entrada en
  `INVARIANTES` + su fila en esta tabla. Sin las tres, no es una regla.

## 8. Reglas del proyecto como datos (`REG-XXX-###`)

El agente no debe deducir qué está obligado a hacer: lo lee. La fuente única de
verdad de **este** proyecto es `references/reglas/reglas_registro.yaml`
(versionada en el repo, no en el vault). Cada regla declara `id`, `nombre`,
`resumen` (una línea, para el brief mínimo), `categoria`, `prioridad`, `estado`,
`norma` (archivo real del repo) y `seccion` (dónde está escrita).

Flujo completo:

```
references/reglas/reglas_registro.yaml
   → ctxmap scan      (eventos REGLA)
   → .context-map/CONTEXT.md      «Reglas de Negocio» (catálogo completo)
   → .context-map/CONTEXT.min.md  «📜 Reglas fijas» (solo prioridad `critica`)
   → vault 2.0-IDEAS/… nodos REGLA en el grafo
```

Consulta (una regla que no se puede consultar acaba siendo un adorno):

```bash
.venv/Scripts/python.exe -m context_map.cli reglas .                  # todas
.venv/Scripts/python.exe -m context_map.cli reglas . --categoria VLT  # por categoría
.venv/Scripts/python.exe -m context_map.cli reglas . --verificar      # ¿cuáles incumplo?
```

`--verificar` cruza cada regla con el chequeo del doctor que la mide y sale con
código 1 si alguna está en WARN/FAIL: la misma puerta que `--strict-warn`, pero
dicha en reglas en vez de en chequeos.

* **Contrato ejecutable**: `context_map/__tests__/test_reglas_del_repo.py`
  exige catálogo con ≥10 reglas, IDs `REG-<CAT>-<NNN>` únicos, categoría = prefijo
  del ID, `prioridad`/`estado` en valores conocidos, `norma` existente en el repo
  y `seccion` presente dentro de esa norma. Si una regla miente, el test falla.
* **Añadir una regla**: primero se escribe la norma en `AGENTS.md` (o en
  `docs/`), después la entrada en el YAML. Al revés no: no hay reglas sin norma.
* **Una regla nueva no se improvisa en el chat.** Si no está en el catálogo, no
  es una regla del proyecto.

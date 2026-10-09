# Instrucciones para Agentes de IA — Context Map

Normas obligatorias para **todos** los agentes (Antigravity, Cursor, Hermes,
Claude, Windsurf, Copilot…). El detalle, los diagramas y los ejemplos viven en
[`docs/GOBERNANZA-AGENTES.md`](docs/GOBERNANZA-AGENTES.md).

---

## 1. Reglas globales
* **Idioma**: español técnico profesional en respuestas, comentarios y docstrings.
* **Docstrings** formales (Google / PEP 257) y **Type Hinting** estricto en Python.
* **Raíz limpia**: sin archivos sueltos; solo `README.md`, `LICENSE`, `pyproject.toml`, `AGENTS.md` y `.gitignore`.

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
4. **Pendientes reales**: cruza `.context-map/vault-ContextMap/7.0-MANUAL/BACKLOG.md` + `3.2-DOCUMENTOS/` + el diario más reciente.
5. **Backlog y vault**: `2.0-IDEAS/2.1-Ideas-Pendientes/` y `5.0-BACKLOG/5.1-Tareas.md`.
6. **No suponer rutas o lógica**: inspecciona el código fuente antes de proponer cambios.
7. **Dominio y documentos**: documenta la lógica nuclear en `7.0-MANUAL/DOMINIO.md`; las fuentes externas van a `.context-map/raw/docs/` + `ctxmap refresh .`.
8. **Memoria viva**: los chats/exportaciones en `.context-map/chats/` se procesan en `ctxmap refresh .`.

> ⚠️ Nunca respondas "¿qué queda pendiente?" con un único documento: cruza **brief + backlog manual + diario + documentos**.

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
```bash
python -m pytest                                  # 1. tests 100%
python -m context_map.cli scan .                  # 2. escanear
python -m context_map.cli build --clean --brief   # 3. vault + brief
python -m context_map.cli check .                 # 4. readiness
```
* **Commits**: *Conventional Commits* en español (`feat:`, `fix:`, `refactor:`, `docs:`…).

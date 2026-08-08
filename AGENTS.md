# Instrucciones para Agentes de IA — Context Map

Este documento establece las normas obligatorias, arquitectura y flujo de trabajo que **todos los Agentes de Inteligencia Artificial** (Antigravity, Cursor, Hermes, Claude, Windsurf, Copilot, etc.) deben seguir sin excepción al interactuar con este repositorio.

---

## 1. Reglas Globales de Comunicación y Código

* **Idioma**: Todas las respuestas, explicaciones y docstrings deben redactarse exclusivamente en **Español Técnico Profesional**.
* **Documentación**: Todo código generado debe incluir comentarios descriptivos y **Docstrings** formales (Google Style / PEP 257) en funciones, clases y módulos.
* **Tipado Fuerte**: Uso estricto de **Type Hinting** en Python (`List[Node]`, `Tuple[str, int]`, `Optional[Dict]`, etc.).
* **Limpieza de Raíz**: No crear archivos sueltos en la raíz (`PLAN.md`, `ROADMAP.txt`). Mantener únicamente los archivos de configuración e identidad (`README.md`, `LICENSE`, `pyproject.toml`, `AGENTS.md`, `.gitignore`).

---

## 2. Arquitectura de Código (Clean Architecture Jerárquica)

El código de `context_map` está organizado bajo el principio de responsabilidad única en la convención `modulo/submodulo/archivo.py`:

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

---

## 3. Protocolo de Inicio para Agentes (Ponerse en Contexto)

Cualquier agente que tome una tarea en este proyecto **DEBE** seguir estos pasos obligatorios antes de escribir o modificar código:

1. **Leer el Brief Ejecutivo**:
   Consultar [.context-map/CONTEXT.md](file:///c:/Users/jose.cespedes/Desktop/PruebaContext/.context-map/CONTEXT.md) para conocer las métricas, riesgos críticos y tareas pendientes.
2. **Revisar el Backlog y Vault**:
   Inspeccionar `.context-map/vault-ContextMap/2.0-IDEAS/2.1-Ideas-Pendientes/` y `5.0-BACKLOG/5.1-Tareas.md`.
3. **No Suponer Rutas o Lógica**:
   Inspeccionar el código fuente antes de formular hipótesis de cambio.

---

## 4. Topología Estricta en Árbol para Obsidian (Graph View) — REGLA INAMOVIBLE

> **Esta es la regla MÁS IMPORTANTE del renderizador. Ningún agente, refactor
> o "mejora" puede violarla. El Graph View de Obsidian DEBE verse como un
> árbol puro: cada nota cuelga de EXACTAMENTE UN padre, las ramas de ideas
> pendientes (2.1), futuras (2.2) y completadas (2.3) son INDEPENDIENTES y
> NUNCA se cruzan entre sí ni con otras secciones.**

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

1. **CADA NOTA TIENE EXACTAMENTE UN PADRE** (árbol puro). El padre se
   materializa como el ÚNICO wikilink con `⬅` (pie "Volver a..."). Ningún
   nodo enlaza a más de un nivel superior, ni a nodos hermanos, ni entre
   secciones de estado, ni a `00-INDICE.md` (salvo las 6 secciones raíz).
2. **Nivel 0 (`00-INDICE.md`)**: Enlaza **únicamente** a los 6 Nodos de
   Sección Raíz (`1.0`, `2.0`, `3.0`, `4.0`, `5.0`, `6.0`).
3. **Nivel 1 (Secciones Raíz `X.0`)**: Enlazan a `00-INDICE.md` (su padre)
   y a sus sub-nodos `X.Y` (sus hijos). Nada más.
4. **Nivel 2 y Nodos Hoja**: Enlazan **exclusivamente a su Sección Padre**
   vía el pie `⬅ Volver a ...`. NUNCA de regreso a `00-INDICE.md`.
5. **Índices de concepto con nombre ÚNICO por estado**:
   `{CONCEPTO}-Pendientes.md`, `{CONCEPTO}-Futuras.md`, `{CONCEPTO}-Completas.md`.
   NUNCA `{CONCEPTO}.md` a secas: Obsidian fusiona archivos con el mismo
   nombre base y mezclaría ideas pendientes con completas.
6. **PROHIBIDO enlazar por nombre corto ambiguo**: todo wikilink a un índice
   de concepto usa su nombre único completo (con sufijo de estado). Las notas
   de idea muestran el concepto como texto plano (`` ``Concepto`` ``), SIN
   wikilink adicional al índice (el pie ya enlaza al padre).
7. **Los batches de ideas completadas se nombran `NN-CONCEPTO-INICIO-FIN.md`
   y su índice DEBE enlazar a los batches reales** (nunca a `idea_*.md`
   inexistentes → nodos fantasma).
8. **Enlaces a sub-secciones condicionales**: `2.0-IDEAS.md` solo enlaza a
   `2.1` / `2.2` / `2.3` si existen nodos de ese estado. Enlaces rotos =
   nodos fantasma = bug.
9. **`00-CONEXIONES.md` en modo jerárquico se renderiza SIN wikilinks**
   (`con_wikilinks=False`): los nombres de archivo del modo jerárquico no
   derivan del slug del título, así que los wikilinks crearían nodos fantasma.

### 4.3 Verificación Automática (inamovible)

- El test `context_map/__tests__/test_topologia_arbol.py` DEBE pasar antes
  de cualquier commit (verificado por `python -m pytest`). Comprueba:
  - 0 nodos sin padre (excepto `00-INDICE.md` y `00-CONEXIONES.md`)
  - 0 colisiones de nombre base entre archivos del vault
  - 0 wikilinks rotos (target que no existe como archivo)
  - Cada índice de concepto termina en `-Pendientes/-Futuras/-Completas.md`
- El **pre-commit hook** regenera el vault con el código LOCAL
  (`python -m context_map.cli build`) — NUNCA con el binario global `ctxmap`
  desactualizado. Si el vault generado no pasa 4.3, el commit está roto.

### 4.4 Vault ÚNICO por proyecto

- El vault activo es `.context-map/vault-<NombreProyecto>` (ej:
  `vault-ContextMap`, sin guión extra). El nombre lo resuelve el repo GitHub.
- PROHIBIDO acumular vaults paralelos obsoletos (`vault-Context-Map`,
  `vault-TestAuto`, etc.): cualquier vault que no se regenera por `build`
  debe moverse a `.context-map/_legacy/` o eliminarse. Solo debe existir UN
  vault por proyecto para que Obsidian no mezcle grafos.
- **Sincronización Multi-Vault**: Todo cambio en `build` debe renderizarse
  en `.context-map/vault/` y en `.context-map/vault-<project>/`
  simultáneamente para que la vista de Obsidian se actualice en tiempo real.

---

## 5. Metodología de Contexto Narrativo con Alma

Toda nota generada para una entidad en el Vault debe invocar `generar_contexto_narrativo(node)` en `context_map/core/generators/generadores.py` para inyectar su estructura polimórfica según el tipo de nodo:

* **`IDEA`**: ¿Por qué?, ¿De dónde surgió?, ¿Para qué?, ¿Cómo?, y tabla de **Pros y Contras**.
* **`RIESGO`**: ¿Qué riesgo es?, Ubicación, Impacto, Mitigación y **Matriz de Gravedad**.
* **`CAMBIO` / `CORRECCION`**: Modificación realizada, Razón del cambio, Archivos y **Verificación de No-Regresión**.
* **`BASE`**: Componente estructural, **Rol en la Arquitectura** e integraciones.
* **`PRUEBA`**: Funcionalidad validada, Criterios de Aceptación y comando `pytest`.
* **`FUTURO`**: Tarea pendiente (TODO), Ubicación en código y Prioridad.

---

## 6. Verificación Obligatoria y Commits

Antes de dar por completada cualquier tarea o comitear en Git:

```bash
# 1. Ejecutar tests unitarios (deben pasar 100%)
python -m pytest

# 2. Escanear y actualizar el mapa de contexto
python -m context_map.cli scan .

# 3. Reconstruir la bóveda de Obsidian y el brief de contexto
python -m context_map.cli build --clean --brief

# 4. Verificar readiness
python -m context_map.cli check .
```

* **Mensajes de Commit**: Usar la convención *Conventional Commits* en español (ej. `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`).

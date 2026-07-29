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
   Inspeccionar `.context-map/vault-Context-Map/2.0-IDEAS/2.1-Ideas-Pendientes/` y `5.0-BACKLOG/5.1-Tareas.md`.
3. **No Suponer Rutas o Lógica**:
   Inspeccionar el código fuente antes de formular hipótesis de cambio.

---

## 4. Topología Estricta en Árbol para Obsidian (Graph View)

Al modificar o extender el renderizador del Vault en `presentation/vault/`:

1. **Nivel 0 (`00-INDICE.md`)**: Enlaza **únicamente** a los 6 Nodos de Sección Raíz (`1.0`, `2.0`, `3.0`, `4.0`, `5.0`, `6.0`).
2. **Nivel 1 (Secciones Raíz `X.0`)**: Enlazan a `00-INDICE.md` hacia arriba y a sus sub-nodos `X.Y` hacia abajo.
3. **Nivel 2 y Nodos Hoja (`2.1-Pendientes`, `2.2-Futuras`, `2.3-Completadas`, `4.0-RIESGOS/*.md`)**: Enlazan **exclusivamente a su Sección Padre (`X.0` o `X.Y`)**, NUNCA de regreso a `00-INDICE.md`.
4. **Sincronización Multi-Vault**: Todo cambio en `build` debe renderizarse en `.context-map/vault/` y en `.context-map/vault-<project>/` simultáneamente para que la vista de Obsidian se actualice en tiempo real.

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

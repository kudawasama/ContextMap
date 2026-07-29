# Plan de Desarrollo — Context Map

## Estado Actual (v1.1.0)

### Completado ✅
- [x] Fase 1: Estructura modular jerárquica (`modulo/submodulo/archivo.py`)
- [x] Fase 2: Refactorización de paquetes principales (`core`, `domain`, `application`, `presentation`, `infrastructure`)
- [x] Fase 3: Briefs ejecutivos para agentes (`CONTEXT.md`)
- [x] Fase 5: Suite de pruebas unitarias (`context_map/__tests__` con `pytest`, 10/10 tests pasados)
- [x] Fase 6: Estandarización y clasificación semántica automática de nodos (*Conventional Commits*)
- [x] Fase 7: Carpetas jerárquicas y sub-clústeres por estado (`2.1-Pendientes`, `2.2-Futuras`, `2.3-Completadas`, `2.4-Relevantes`)
- [x] Fase 8: Consolidación automática de notas y topología en árbol de 3 niveles para Obsidian Graph View
- [x] **Metodología de Contexto Narrativo con Alma**: Despacho polimórfico por tipo de nodo (`IDEAS` con 5 preguntas + Pros/Contras; `RIESGOS` con Matriz de Gravedad; `CAMBIOS` con No-Regresión)
- [x] Integración con Antigravity IDE, Hermes y exportaciones de Chat
- [x] Comando `ctxmap update` (actualización automática)
- [x] Comando `ctxmap sync --migrate` (migración a nueva versión)

### Pendiente ⏳
- [ ] Fase 4: CI/CD con GitHub Actions para auto-generación de contexto en PRs
- [ ] Fase 9: Dashboard web interactivo para explorar el vault (opcional)
- [ ] Fase 10: Integración mediante plugins con VS Code / Cursor / Windsurf

---

## Arquitectura Implementada

```
context_map/
├── core/                        # Lógica fundamental y modelos
│   ├── models/                  # Dataclasses (Node, Edge, Event)
│   ├── parsing/                 # Parser de eventos y deserializadores JSONL
│   ├── storage/                 # Persistencia JSONL y snapshots
│   ├── normalization/           # Estandarización y clasificación semántica
│   └── generators/              # Generación de resúmenes y Contexto Narrativo con Alma
├── domain/                      # Lógica de negocio del dominio
│   ├── scanning/                # Escáner estático de proyecto
│   ├── synchronization/         # Sincronización incremental de grafos
│   ├── analysis/                # Análisis de readiness del proyecto
│   ├── health/                  # Diagnóstico del estado del mapa (doctor)
│   └── reporting/               # Reportes semanales de avance
├── application/                 # Capa de aplicación y CLI
│   ├── cli/                     # Parser principal de comandos
│   └── commands/                # 16 comandos unificados (build, scan, sync, etc.)
├── infrastructure/              # Integraciones externas y analizadores
│   ├── integrations/            # Git, Hermes, Antigravity IDE, Chat exports
│   └── analyzers/               # Analizadores AST de estructura y contenido Python
└── presentation/                # Generación de salidas visuales
    ├── vault/                   # Vault Obsidian jerárquico y MOC
    └── briefs/                  # Generador de CONTEXT.md para agentes
```

---

## Métricas Actuales

- **Nodos totales en el mapa**: >1,100 nodos registrados
- **Archivos Python analizados**: 68 módulos
- **Archivos escaneados**: >180 archivos
- **Comandos CLI**: 16 comandos unificados
- **Pruebas Automatizadas**: 10 tests en `context_map/__tests__/` (100% pasando)
- **Score de Readiness**: 39/100 (Pendiente configuración de CI/CD GitHub Actions)

---

## Próximos Pasos

### Prioridad Alta
1. **CI/CD Actions** — Configurar GitHub Actions en `.github/workflows/` para auditar el readiness y auto-generar el brief en cada PR.
2. **Documentación de Agentes** — Crear `AGENTS.md` con reglas explícitas para agentes de IA que consuman Context Map.

### Prioridad Media
3. **Dashboard web** — Interfaz web visual interactiva para explorar el vault de Obsidian.
4. **Mejorar readiness score a 80+** — Agregar CHANGELOG.md, pytest.ini y Makefile.

### Prioridad Baja
5. **Plugin para VS Code / IDEs** — Extensión nativa para visualización de contexto.

---

## Decisiones Técnicas Clave

1. **Clean Architecture Jerárquica** — Convención `modulo/submodulo/archivo.py` con bajo acoplamiento e inyección de dependencias.
2. **Contexto Narrativo con Alma** — Despacho polimórfico que adapta la narrativa según el tipo semántico de nodo.
3. **Topología en Árbol de 3 Niveles** — Estructura estricta sin mega-hubs para una visualización limpia en Obsidian Graph View.
4. **Persistencia JSONL Incremental** — Persistencia atómica, simple y git-friendly.

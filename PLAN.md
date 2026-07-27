# Plan de Desarrollo — Context Map

## Estado Actual (v1.0.0)

### Completado ✅
- [x] Fase 1: Estructura modular (core/domain/application/infrastructure/presentation)
- [x] Fase 2: Refactorizar archivos grandes (cli, parser, writer)
- [x] Fase 3: Briefs para agentes (CONTEXT.md)
- [x] Fase 6: Estandarización de nodos (tags, status, evidence)
- [x] Fase 7: Carpetas por estado (COMPLETADO, EN_PROGRESO, PENDIENTE, CANCELADO)
- [x] Fase 8: Consolidación automática de notas relacionadas
- [x] Integración con Antigravity IDE
- [x] Comando `ctxmap update` (actualización automática)
- [x] Comando `ctxmap sync --migrate` (migración a nueva versión)

### Pendiente ⏳
- [ ] Fase 4: CI/CD con GitHub Actions
- [ ] Fase 5: Tests y verificación (score 39/100)
- [ ] Fase 9: Dashboard web (opcional)

## Arquitectura Implementada

```
context_map/
├── core/                    # Lógica fundamental
│   ├── models.py            # Node, Edge, Event
│   ├── parser.py            # Clasificación de eventos
│   ├── store.py             # Persistencia JSONL
│   ├── standardize.py       # Estandarización de nodos
│   └── generadores.py       # Generación de resúmenes
├── domain/                  # Lógica de negocio
│   ├── scanner.py           # Escáner de proyecto
│   ├── sync.py              # Sincronización incremental
│   ├── checker.py           # Análisis de readiness
│   └── reporter.py          # Reportes semanales
├── application/             # CLI y comandos
│   ├── cli.py               # Parser principal
│   └── commands/__init__.py # 16 comandos unificados
├── infrastructure/          # Integraciones externas
│   ├── integrations/
│   │   ├── git.py           # Historial git
│   │   ├── hermes.py        # Sesiones de Hermes
│   │   ├── chat_export.py   # Chats multi-plataforma
│   │   └── antigravity.py   # Antigravity IDE
│   └── analyzers/
│       ├── structure.py     # Análisis de estructura
│       └── content.py       # Análisis de contenido
└── presentation/            # Generación de salida
    ├── writer.py            # Vault Obsidian
    └── brief.py             # CONTEXT.md
```

## Métricas Actuales

- **Nodos totales**: 246
- **Archivos en vault**: 41
- **Comandos CLI**: 16
- **Líneas de código**: ~4,500
- **Score readiness**: 39/100 (sin tests)

## Próximos Pasos

### Prioridad Alta
1. **Tests** — Crear directorio `__tests__/` con tests unitarios
2. **CI/CD** — GitHub Actions para auto-generar contexto

### Prioridad Media
3. **Dashboard web** — Interfaz visual para explorar el vault
4. **Mejorar readiness** — Agregar README, LICENSE, Makefile

### Prioridad Baja
5. **Plugin VS Code** — Extensión para VS Code
6. **Integración con más herramientas** — Cursor, Windsurf, etc.

## Decisiones Técnicas

1. **Arquitectura modular** — Estilo Clean Architecture (CotanoPet)
2. **Persistencia JSONL** — Simple, legible, Git-friendly
3. **Vault Obsidian** — Formato estándar para knowledge bases
4. **Estandarización automática** — Tags, status, evidence
5. **Actualización via git** — `ctxmap update` clona y reinstala

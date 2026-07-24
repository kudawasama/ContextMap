# Plan de Refactorización — Context Map

## Estado actual
- cli.py: 491 líneas (demasiado grande)
- parser.py: 426 líneas (demasiado grande)
- writer.py: 422 líneas (demasiado grande)
- 3279 líneas totales en 14 archivos

## Objetivo
Arquitectura modular estilo CotanoPet (Clean Architecture):
- Separación por responsabilidades
- Cada archivo < 150 líneas
- Dominio, aplicación e infraestructura separados

## Fase 1: Nueva estructura de directorios
```
context_map/
├── core/                          # Lógica de negocio
│   ├── models.py                  # Modelos de datos
│   ├── parser.py                  # Parser de eventos
│   └── store.py                   # Persistencia JSONL
├── domain/                        # Lógica de dominio
│   ├── scanner.py                 # Escáner de proyecto
│   ├── checker.py                 # Readiness score
│   ├── reporter.py                # Reportes semanales
│   └── sync.py                    # Sync incremental
├── application/                   # Comandos de aplicación
│   ├── cli.py                     # CLI principal
│   └── commands/                  # Comandos individuales
│       ├── __init__.py
│       ├── build.py               # Comando build
│       ├── scan.py                # Comando scan
│       ├── check.py               # Comando check
│       ├── sync.py                # Comando sync
│       └── ...
├── infrastructure/                # Integraciones externas
│   ├── integrations/
│   │   ├── git.py                 # Lector git
│   │   ├── hermes.py              # Lector sesiones
│   │   └── chat_export.py         # Parser chats
│   └── analyzers/                 # Análisis de código
│       ├── structure.py           # Análisis estructura
│       └── content.py             # Análisis contenido
├── presentation/                  # Generación de salida
│   ├── writer.py                  # Generador vault
│   ├── mermaid.py                 # Diagramas Mermaid
│   └── brief.py                   # Brief para agentes (NUEVO)
└── __tests__/                     # Tests
    └── smoke.py
```

## Fase 2: Refactorizar archivos grandes
1. cli.py → cli.py + commands/*.py
2. parser.py → parser.py + generadores.py
3. writer.py → writer.py + mermaid.py + brief.py

## Fase 3: Briefs para agentes (CONTEXT.md)
- Generar un archivo CONTEXT.md con resumen ejecutivo
- Cualquier agente puede leerlo en 30 segundos

## Fase 4: CI/CD con GitHub Actions
- workflow.yml para auto-actualizar contexto en cada push
- workflow_dispatch para ejecución manual

## Fase 5: Tests y verificación
- Actualizar tests para nueva estructura
- Verificar que todo funciona

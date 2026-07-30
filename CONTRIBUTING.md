# Contribuir a Context Map

Gracias por tu interés en contribuir a **ContextMap**.

## Desarrollo Local

```bash
# Clonar el repositorio
git clone https://github.com/kudawasama/ContextMap.git
cd ContextMap

# Instalar en modo desarrollo editable
pip install -e .

# Ejecutar tests unitarios (deben pasar 100%)
python -m pytest

# Verificar readiness
python -m context_map.cli check .
```

## Arquitectura del Proyecto (Clean Architecture Jerárquica)

```
context_map/
├── cli.py                          # Punto de entrada CLI
├── core/                           # Fundamentos del dominio
│   ├── models/                     # Dataclasses (Node, Edge, Event, Config)
│   ├── parsing/                    # Parser de eventos y deserialización JSONL
│   ├── storage/                    # Persistencia JSONL, config y snapshots
│   ├── normalization/              # Estandarización y clasificación semántica
│   └── generators/                 # Contexto Narrativo con Alma
├── domain/                         # Lógica de negocio
│   ├── scanning/                   # Escáner estático del proyecto
│   ├── synchronization/            # Sincronización incremental del grafo
│   ├── analysis/                   # Readiness (checker) y Complejidad (McCabe)
│   ├── health/                     # Diagnóstico y mantenimiento (doctor)
│   └── reporting/                  # Reportes semanales de avance
├── application/                    # CLI y orquestación
│   ├── cli/                        # Parser principal de argumentos CLI
│   └── commands/                   # Comandos unificados (build, scan, sync, hook)
├── infrastructure/                 # Integraciones externas
│   ├── integrations/               # Git, Hermes, Antigravity, Chat exports
│   └── analyzers/                  # Analizadores AST de estructura y contenido
├── presentation/                   # Generación de salidas visuales
│   ├── vault/                      # Generador Obsidian Vault (atomic, consolidated, templates)
│   └── briefs/                     # Generador de CONTEXT.md y AGENTS.md
└── __tests__/                      # Suite de tests unitarios
```

## Comandos del CLI

| Comando | Descripción |
|---------|-------------|
| `ctxmap auto [target]` | Automatización All-in-One completa (scan + git + build --clean --brief) |
| `ctxmap init` | Inicializa estructura `.context-map/` y `AGENTS.md` |
| `ctxmap scan [target]` | Escanea proyecto y genera eventos sintácticos |
| `ctxmap build` | Genera Vault Obsidian completo y briefs |
| `ctxmap build --clean --brief` | Reconstrucción limpia con brief para Agentes |
| `ctxmap sync` | Sincronización incremental de nodos |
| `ctxmap hook install [target]` | Instala el Git Pre-Commit Hook automático |
| `ctxmap check [target]` | Analiza el score de readiness del proyecto (0-100) |
| `ctxmap import-git [target]` | Importa historial de commits y tags de Git |
| `ctxmap import-antigravity` | Importa sesiones de chat de Antigravity IDE |
| `ctxmap import-sessions` | Importa sesiones de Hermes Agent |
| `ctxmap weekly` | Genera reporte semanal de avances |
| `ctxmap doctor` | Diagnóstico de salud y reparación de estado |

## Convención de Commits

Usa convención de commits:
- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` documentación
- `refactor:` refactoring
- `test:` tests
- `chore:` mantenimiento

## Pull Requests

1. Crea una rama para tu feature
2. Haz commits atómicos
3. Actualiza documentación si es necesario
4. Ejecuta tests antes de enviar
5. Crea PR con descripción clara

## Issues

- Usa templates de issues
- Incluye pasos para reproducir
- Incluye versión de Python y SO

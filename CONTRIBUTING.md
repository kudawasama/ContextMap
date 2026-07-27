# Contribuir a Context Map

Gracias por tu interés en contribuir.

## Desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/kudawasama/ContextMap.git
cd ContextMap

# Instalar en modo desarrollo con UV
uv tool install . // modo desarrollo

# Ejecutar tests
python -m pytest context_map/__tests__

# Verificar lint
python -m mypy context_map
python -m ruff check context_map
```

## Estructura del Proyecto

```
context_map/
├── cli.py                          # Punto de entrada
├── core/                           # Lógica fundamental
│   ├── models.py                   # Node, Edge, Event
│   ├── parser.py                   # Clasificación de eventos
│   ├── store.py                    # Persistencia JSONL
│   ├── standardize.py              # Estandarización de nodos
│   └── generadores.py              # Generación de resúmenes
├── domain/                         # Lógica de negocio
│   ├── scanner.py                  # Escáner de proyecto
│   ├── sync.py                     # Sincronización incremental
│   ├── checker.py                  # Análisis de readiness
│   └── reporter.py                 # Reportes semanales
├── application/                    # CLI y comandos
│   ├── cli.py                      # Parser principal (argparse)
│   └── commands/
│       └── __init__.py             # 16 comandos unificados
├── infrastructure/                 # Integraciones externas
│   ├── integrations/
│   │   ├── git.py                  # Historial git
│   │   ├── hermes.py               # Sesiones de Hermes
│   │   ├── chat_export.py          # Chats multi-plataforma
│   │   └── antigravity.py          # Antigravity IDE
│   └── analyzers/
│       ├── structure.py            # Análisis de estructura
│       └── content.py              # Análisis de contenido
├── presentation/                   # Generación de salida
│   ├── writer.py                   # Vault Obsidian
│   └── brief.py                    # CONTEXT.md
├── scripts/                        # Scripts auxiliares
│   └── standardize.py              # CLI de estandarización
└── __tests__/                      # Tests
    └── smoke.py
```

## Comandos del CLI

| Comando | Descripción |
|---------|-------------|
| `ctxmap init` | Crea estructura `.context-map/` |
| `ctxmap scan [target]` | Escanea proyecto y genera eventos |
| `ctxmap import-git [target]` | Importa historial de commits |
| `ctxmap import-sessions` | Importa sesiones de Hermes |
| `ctxmap import-chat [file]` | Importa chats externos |
| `ctxmap import-antigravity` | Importa chats de Antigravity IDE |
| `ctxmap build` | Genera vault completo |
| `ctxmap sync` | Sync incremental (solo nuevos) |
| `ctxmap sync --migrate` | Migrar proyecto a nueva versión |
| `ctxmap check` | Verifica readiness (0-100) |
| `ctxmap weekly` | Genera reporte semanal |
| `ctxmap update` | Actualiza ContextMap desde GitHub |

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

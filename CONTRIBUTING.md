# Contribuir a Context Map

Gracias por tu interés en contribuir.

## Desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/kudawasama/ContextMap.git
cd ContextMap

# Instalar en modo desarrollo con UV
uv pip install -e .

# Ejecutar tests
python -m pytest context_map/__tests__

# Verificar lint
python -m mypy context_map
python -m ruff check context_map
```

## Estructura del Proyecto

```
context_map/
├── cli.py              # CLI principal
├── models.py           # Modelos de datos
├── parser.py           # Parser de eventos
├── store.py            # Persistencia JSONL
├── sync.py             # Sync incremental
├── writer.py           # Generador vault Obsidian
├── scanner.py          # Escáner de proyecto
├── checker.py          # Analizador de readiness
├── reporter.py         # Generador de reportes
├── analyzers/          # Análisis de proyecto
│   ├── structure.py
│   └── content.py
└── integrations/       # Integraciones externas
    ├── git.py
    ├── hermes.py
    └── chat_export.py
```

## Commits

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

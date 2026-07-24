# Contribuir a Context Map Generator

Gracias por tu interés en contribuir.

## Desarrollo

```bash
# Clonar el repositorio
git clone https://github.com/kudawasama/context-map-generator.git
cd context-map-generator

# Instalar en modo desarrollo
pip install -e .

# Ejecutar tests
python -m context_map.__tests__.smoke
```

## Estructura del Código

```
context_map/
├── __init__.py     # Package init
├── cli.py          # Comandos: init, build, sync, watch
├── models.py       # Node, Edge, Event
├── parser.py       # Clasificador de eventos
├── store.py        # Persistencia JSONL
├── sync.py         # Sync incremental
└── writer.py       # Generador de vault Obsidian
```

## Flujo de Trabajo

1. Haz tu cambio
2. Ejecuta `python -m context_map.__tests__.smoke`
3. Crea un commit con mensaje descriptivo
4. Abre un Pull Request

## Convenciones

- Código en español (comentarios, docstrings, UI)
- Type hints en todas las funciones
- Archivos menores a 100 líneas
- Sin imports cruzados entre módulos

## Issues

Si encuentras un bug o tienes una idea, abre un issue con:

- Descripción clara del problema
- Pasos para reproducir
- Comportamiento esperado vs actual

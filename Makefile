# Makefile — Automatización de tareas de desarrollo para ContextMap

.PHONY: test scan build refresh check clean watch doctor export help

help:
	@echo "Comandos disponibles:"
	@echo "  make test      - Ejecuta la suite de pruebas unitarias con pytest"
	@echo "  make scan      - Escanea el código fuente del proyecto"
	@echo "  make build     - Reconstruye la bóveda Obsidian y el brief CONTEXT.md"
	@echo "  make refresh   - Escanea, reconstruye el vault y realiza el chequeo de frescura"
	@echo "  make check     - Audita el índice de readiness (score 0-100)"
	@echo "  make watch     - Inicia el daemon de monitoreo de archivos en tiempo real"
	@echo "  make doctor    - Diagnostica y auto-repara la salud del vault y el proyecto"
	@echo "  make clean     - Limpia la bóveda y reconstruye desde cero sin borrar notas manuales"

test:
	python -m pytest

scan:
	python -m context_map.cli scan .

build:
	python -m context_map.cli build --brief

refresh:
	python -m context_map.cli refresh .

check:
	python -m context_map.cli check .

watch:
	python -m context_map.cli watch .

doctor:
	python -m context_map.cli doctor . --fix

clean:
	python -m context_map.cli build --clean --brief

# Makefile — Automatización de tareas de desarrollo para ContextMap

# Regla fija: TODO se ejecuta con el intérprete del venv del proyecto.
# El `python` global no tiene el extra [mcp] (pydantic >= 2.13) y, además, hace
# que la recolección del suite falle a medias. Si no hay venv, se avisa.
PY := $(shell if [ -x .venv/Scripts/python.exe ]; then echo .venv/Scripts/python.exe; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python; fi)

.PHONY: test scan build refresh check clean watch doctor verify rules export help

help:
	@echo "Comandos disponibles:"
	@echo "  make test      - Ejecuta la suite de pruebas unitarias con pytest"
	@echo "  make verify    - Puerta de calidad: tests + reglas fijas (doctor --strict-warn)"
	@echo "  make rules     - Solo las reglas fijas de estabilidad (invariantes)"
	@echo "  make scan      - Escanea el código fuente del proyecto"
	@echo "  make build     - Reconstruye la bóveda Obsidian y el brief CONTEXT.md"
	@echo "  make refresh   - Escanea, reconstruye el vault y realiza el chequeo de frescura"
	@echo "  make check     - Audita el índice de readiness (score 0-100)"
	@echo "  make watch     - Inicia el daemon de monitoreo de archivos en tiempo real"
	@echo "  make doctor    - Diagnostica y auto-repara la salud del vault y el proyecto"
	@echo "  make clean     - Limpia la bóveda y reconstruye desde cero sin borrar notas manuales"
	@echo ""
	@echo "Intérprete activo: $(PY)"

test:
	$(PY) -m pytest

verify: test rules

rules:
	$(PY) -m context_map.cli doctor . --strict-warn

scan:
	$(PY) -m context_map.cli scan .

build:
	$(PY) -m context_map.cli build --brief

refresh:
	$(PY) -m context_map.cli refresh .

check:
	$(PY) -m context_map.cli check .

watch:
	$(PY) -m context_map.cli watch .

doctor:
	$(PY) -m context_map.cli doctor . --fix

clean:
	$(PY) -m context_map.cli build --clean --brief

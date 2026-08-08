"""Test: Detección y adaptación del ecosistema agéntico.

Verifica que ContextMap detecta el stack técnico real del proyecto y
genera las reglas por agente (AGENTS.md contextual, CLAUDE.md,
.cursorrules, .windsurfrules, copilot-instructions, .hermes/).
"""

from __future__ import annotations

import os
import shutil
import tempfile

from context_map.domain.ecosystem import (
    adaptar_ecosistema,
    detectar_ecosistema,
    detectar_ide,
    detectar_stack,
)


def _crear_proyecto_python() -> str:
    """Crea un proyecto Python de prueba con pyproject.toml y tests."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_eco_")
    with open(os.path.join(temp_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
        f.write("[project]\nname = \"demo\"\n[tool.pytest.ini_options]\n")
    with open(os.path.join(temp_dir, "main.py"), "w", encoding="utf-8") as f:
        f.write("# entrypoint\n")
    os.makedirs(os.path.join(temp_dir, "tests"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, ".cursor"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, ".github"), exist_ok=True)
    return temp_dir


def test_detectar_stack_python() -> None:
    """Verifica la detección de stack Python con pytest."""
    temp_dir = _crear_proyecto_python()
    try:
        stack = detectar_stack(temp_dir)
        assert "Python" in stack.lenguajes
        assert stack.test_runner == "pytest"
        assert "main.py" in stack.entrypoints
        assert "tests" in stack.estructura
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_detectar_ide() -> None:
    """Verifica la detección de Cursor y GitHub."""
    temp_dir = _crear_proyecto_python()
    try:
        ide = detectar_ide(temp_dir)
        assert "Cursor" in ide.ides
        assert "VS Code" not in ide.ides
        # .github existe pero sin copilot-instructions → no marca Copilot
        assert "GitHub Copilot" not in ide.agentes
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_ecosistema_genera_reglas() -> None:
    """Verifica que adaptar_ecosistema genera las reglas por agente."""
    temp_dir = _crear_proyecto_python()
    try:
        eco = detectar_ecosistema(temp_dir)
        generados = adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir)

        assert "AGENTS.md" in generados, "Falta AGENTS.md contextual"
        # Cursor detectado → .cursorrules + .cursor/rules/
        assert ".cursor/rules/contextmap.mdc" in generados
        assert ".cursorrules" in generados
        # .github existe → copilot-instructions
        assert ".github/copilot-instructions.md" in generados
        # .hermes completo
        assert ".hermes/config.yaml" in generados
        assert ".hermes/workflows/dev-loop.md" in generados

        # AGENTS.md debe contener el stack real (pytest)
        with open(os.path.join(temp_dir, "AGENTS.md"), encoding="utf-8") as f:
            contenido = f.read()
        assert "pytest" in contenido.lower(), "AGENTS.md no contiene el test runner real"
        assert "DemoProj" in contenido

        # .cursorrules debe referenciar el stack
        with open(os.path.join(temp_dir, ".cursorrules"), encoding="utf-8") as f:
            cursor = f.read()
        assert "pytest" in cursor.lower()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_respeta_existentes() -> None:
    """Verifica que sin --overwrite no sobrescribe reglas existentes."""
    temp_dir = _crear_proyecto_python()
    try:
        # Crear CLAUDE.md manual previo
        claude_path = os.path.join(temp_dir, "CLAUDE.md")
        with open(claude_path, "w", encoding="utf-8") as f:
            f.write("# CLAUDE.md manual — NO SOBRESCRIBIR")

        # Simular que Claude Code está presente
        os.makedirs(os.path.join(temp_dir, ".claude"), exist_ok=True)

        eco = detectar_ecosistema(temp_dir)
        generados = adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir)

        # CLAUDE.md no debe sobrescribirse sin --overwrite
        with open(claude_path, encoding="utf-8") as f:
            contenido = f.read()
        assert "NO SOBRESCRIBIR" in contenido, "Se sobrescribió CLAUDE.md existente"

        # AGENTS.md SÍ se regenera (es el archivo de ContextMap)
        with open(os.path.join(temp_dir, "AGENTS.md"), encoding="utf-8") as f:
            contenido = f.read()
        assert "DemoProj" in contenido

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Test: Detección de stack ===")
    test_detectar_stack_python()
    print("   OK: test_detectar_stack_python PASO")

    print()
    print("=== Test: Detección de IDE ===")
    test_detectar_ide()
    print("   OK: test_detectar_ide PASO")

    print()
    print("=== Test: Adaptación de reglas ===")
    test_adaptar_ecosistema_genera_reglas()
    print("   OK: test_adaptar_ecosistema_genera_reglas PASO")

    print()
    print("=== Test: Respeto de reglas existentes ===")
    test_adaptar_respeta_existentes()
    print("   OK: test_adaptar_respeta_existentes PASO")

    print()
    print("Todos los tests pasaron correctamente.")

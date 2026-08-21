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


def _crear_proyecto_multiharness() -> str:
    """Crea un proyecto con todos los harnesses agénticos simulados."""
    temp_dir = _crear_proyecto_python()
    for d in [".opencode", ".codex", ".gemini", ".aider", ".roo", ".antigravity", ".claude", ".windsurf", ".idea", ".vscode"]:
        os.makedirs(os.path.join(temp_dir, d), exist_ok=True)
    # Archivos de reglas que activan la detección de Cline y Claude Code
    with open(os.path.join(temp_dir, ".clinerules"), "w", encoding="utf-8") as f:
        f.write("# cline\n")
    with open(os.path.join(temp_dir, "CLAUDE.md"), "w", encoding="utf-8") as f:
        f.write("# claude\n")
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


def test_detectar_ide_proceso() -> None:
    """Verifica la detección de IDE por proceso activo (mockeando tasklist/ps)."""
    import context_map.domain.ecosystem.detector as detector

    original = detector._listar_procesos
    try:
        detector._listar_procesos = lambda: [
            "cursor.exe", "code.exe", "python.exe", "explorer.exe",
        ]
        ides = detector.detectar_ide_proceso()
        assert "Cursor" in ides
        assert "VS Code" in ides
        assert len(ides) == 2, f"Esperaba 2 IDEs, obtuve: {ides}"
    finally:
        detector._listar_procesos = original


def test_detectar_ecosistema_fusiona_proceso() -> None:
    """Verifica que detectar_ecosistema fusiona IDEs por marcador y por proceso."""
    import context_map.domain.ecosystem.detector as detector

    temp_dir = _crear_proyecto_python()  # trae .cursor/
    original = detector._listar_procesos
    try:
        detector._listar_procesos = lambda: ["code.exe"]
        eco = detectar_ecosistema(temp_dir)
        # Cursor vino por marcador .cursor/; VS Code por proceso activo
        assert "Cursor" in eco.ide.ides
        assert "VS Code" in eco.ide.ides
        assert "VS Code" in eco.ide.ides_por_proceso
        assert "Cursor" not in eco.ide.ides_por_proceso
    finally:
        detector._listar_procesos = original
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
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir)

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


def test_detectar_multiharness() -> None:
    """Verifica la detección de todos los harnesses agénticos."""
    temp_dir = _crear_proyecto_multiharness()
    try:
        eco = detectar_ecosistema(temp_dir)
        print(f"   IDEs: {eco.ide.ides}")
        print(f"   Agentes: {eco.ide.agentes}")

        assert "VS Code" in eco.ide.ides
        assert "Cursor" in eco.ide.ides
        assert "Windsurf" in eco.ide.ides
        assert "JetBrains" in eco.ide.ides

        agentes = eco.ide.agentes
        assert "OpenCode" in agentes, f"Falta OpenCode en {agentes}"
        assert "OpenAI Codex" in agentes, f"Falta OpenAI Codex en {agentes}"
        assert "Gemini CLI" in agentes, f"Falta Gemini CLI en {agentes}"
        assert "Aider" in agentes, f"Falta Aider en {agentes}"
        assert "Roo Code" in agentes, f"Falta Roo Code en {agentes}"
        assert "Claude Code" in agentes, f"Falta Claude Code en {agentes}"
        assert "Antigravity" in agentes, f"Falta Antigravity en {agentes}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_multiharness_genera_reglas() -> None:
    """Verifica la generación de reglas para todos los harnesses."""
    temp_dir = _crear_proyecto_multiharness()
    try:
        eco = detectar_ecosistema(temp_dir)
        generados = adaptar_ecosistema("DemoMulti", eco, target_dir=temp_dir)

        esperados = [
            "AGENTS.md",
            ".cursor/rules/contextmap.mdc",
            ".cursorrules",
            ".windsurfrules",
            ".roo/rules/contextmap.md",
            "GEMINI.md",
            ".aider.conf.yml",
            "opencode.json",
            ".github/copilot-instructions.md",
            ".hermes/config.yaml",
        ]
        for ruta in esperados:
            assert ruta in generados, f"No se generó {ruta} (generados: {generados})"

        # CLAUDE.md existe en el fixture y se respeta (no se regenera sin --overwrite)
        assert os.path.exists(os.path.join(temp_dir, "CLAUDE.md")), "Falta CLAUDE.md"

        # Verificar contenido de archivos clave
        with open(os.path.join(temp_dir, "GEMINI.md"), encoding="utf-8") as f:
            gemini = f.read()
        assert "ContextMap" in gemini and "pytest" in gemini.lower()

        with open(os.path.join(temp_dir, "opencode.json"), encoding="utf-8") as f:
            opencode = f.read()
        assert "DemoMulti" in opencode and "pytest" in opencode.lower()

        with open(os.path.join(temp_dir, ".roo/rules/contextmap.md"), encoding="utf-8") as f:
            roo = f.read()
        assert "pytest" in roo.lower()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_merge_preserva_reglas_usuario() -> None:
    """Verifica que --merge anexa el bloque ContextMap sin borrar las reglas del usuario."""
    temp_dir = _crear_proyecto_python()
    try:
        # AGENTS.md existente con reglas propias del usuario
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Mi proyecto\n\n## Reglas del equipo\n- No tocar config sin preguntar\n- Commits en español\n")

        eco = detectar_ecosistema(temp_dir)
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="merge")

        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()

        # Reglas del usuario preservadas
        assert "Reglas del equipo" in contenido, "Se perdieron las reglas del usuario"
        assert "No tocar config sin preguntar" in contenido
        # Bloque ContextMap anexado con marcadores
        assert "CONTEXTMAP:BEGIN" in contenido, "Falta marcador de inicio"
        assert "CONTEXTMAP:END" in contenido, "Falta marcador de fin"
        assert "DemoProj" in contenido

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_merge_idempotente() -> None:
    """Verifica que merge repetido no duplica el bloque ContextMap."""
    temp_dir = _crear_proyecto_python()
    try:
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Mi proyecto\n\n## Reglas del equipo\n- Regla 1\n")

        eco = detectar_ecosistema(temp_dir)
        # Primer merge
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="merge")
        # Segundo merge (idempotente)
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="merge")

        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()

        assert contenido.count("CONTEXTMAP:BEGIN") == 1, (
            f"El bloque ContextMap se duplicó: {contenido.count('CONTEXTMAP:BEGIN')} veces"
        )
        assert "Regla 1" in contenido, "Se perdieron reglas del usuario en re-merge"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_merge_vs_overwrite() -> None:
    """Verifica que overwrite reemplaza completo y respect no toca."""
    temp_dir = _crear_proyecto_python()
    try:
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Reglas manuales SOLO")

        eco = detectar_ecosistema(temp_dir)

        # respect: no toca
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="respect")
        with open(agents_path, encoding="utf-8") as f:
            assert f.read().strip() == "# Reglas manuales SOLO", "respect modificó el archivo"

        # overwrite: reemplaza completo (sin marcadores, sin reglas del usuario)
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="overwrite")
        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()
        assert "CONTEXTMAP:BEGIN" not in contenido, "overwrite debería reemplazar, no fusionar"
        assert "DemoProj" in contenido

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_upgrade_memoria_viva_agents_generado() -> None:
    """Un AGENTS.md generado por una versión ANTERIOR de ContextMap (sin la regla
    de memoria viva) se actualiza en modo respect (hallazgo B, caso Bot_AX_Contable).

    El archivo contiene la marca de ContextMap (fue generado por ctxmap) pero NO
    la regla de memoria viva (v1.5+) → se le anexa el bloque ContextMap con las
    reglas nuevas, preservando el contenido previo.
    """
    temp_dir = _crear_proyecto_python()
    try:
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(
                "# Instrucciones — Bot Demo\n\n"
                "<!-- CONTEXTMAP:BEGIN -->\n"
                "Este proyecto utiliza ContextMap para gobernanza de contexto.\n"
                "## 1. Protocolo de Inicio\n- Leer el brief\n"
                "<!-- CONTEXTMAP:END -->\n"
            )

        eco = detectar_ecosistema(temp_dir)
        generados = adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="respect")

        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()

        # Reglas previas preservadas
        assert "Protocolo de Inicio" in contenido, "Se perdió el contenido previo"
        # Nueva regla de memoria viva propagada
        assert "memoria viva" in contenido.lower(), "No se propagó la regla de memoria viva"
        assert "CONTEXTMAP:BEGIN" in contenido, "Falta el marcador del bloque ContextMap"
        assert any("upgrade" in g for g in generados), f"Debe reportarse el upgrade (generados: {generados})"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_adaptar_respect_no_upgrade_manual() -> None:
    """Un AGENTS.md MANUAL (sin marca de ContextMap) NO se toca en modo respect,
    aunque le falte la memoria viva (el upgrade solo aplica a archivos generados)."""
    temp_dir = _crear_proyecto_python()
    try:
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Reglas manuales SOLO del equipo")

        eco = detectar_ecosistema(temp_dir)
        adaptar_ecosistema("DemoProj", eco, target_dir=temp_dir, modo="respect")

        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()
        assert contenido.strip() == "# Reglas manuales SOLO del equipo", (
            "respect modificó un AGENTS.md manual"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_cmd_adapt_overwrite_flag_funciona() -> None:
    """El flag --overwrite llega a adaptar_ecosistema (antes se ignoraba en cmd_adapt)."""
    from argparse import Namespace

    from context_map.application.commands.adapt import cmd_adapt

    temp_dir = _crear_proyecto_python()
    try:
        agents_path = os.path.join(temp_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write("# Reglas manuales SOLO")

        args = Namespace(target=temp_dir, project="DemoProj", overwrite=True, merge=False)
        cmd_adapt(args)

        with open(agents_path, encoding="utf-8") as f:
            contenido = f.read()
        assert "DemoProj" in contenido, "--overwrite no regeneró AGENTS.md"
        assert "Reglas manuales SOLO" not in contenido, "--overwrite debía reemplazar completo"
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
    print("=== Test: Detección por proceso activo ===")
    test_detectar_ide_proceso()
    print("   OK: test_detectar_ide_proceso PASO")
    test_detectar_ecosistema_fusiona_proceso()
    print("   OK: test_detectar_ecosistema_fusiona_proceso PASO")

    print()
    print("=== Test: Adaptación de reglas ===")
    test_adaptar_ecosistema_genera_reglas()
    print("   OK: test_adaptar_ecosistema_genera_reglas PASO")

    print()
    print("=== Test: Respeto de reglas existentes ===")
    test_adaptar_respeta_existentes()
    print("   OK: test_adaptar_respeta_existentes PASO")

    print()
    print("=== Test: Multi-harness detección ===")
    test_detectar_multiharness()
    print("   OK: test_detectar_multiharness PASO")

    print()
    print("=== Test: Multi-harness reglas ===")
    test_adaptar_multiharness_genera_reglas()
    print("   OK: test_adaptar_multiharness_genera_reglas PASO")

    print()
    print("=== Test: Merge preserva reglas usuario ===")
    test_adaptar_merge_preserva_reglas_usuario()
    print("   OK: test_adaptar_merge_preserva_reglas_usuario PASO")

    print()
    print("=== Test: Merge idempotente ===")
    test_adaptar_merge_idempotente()
    print("   OK: test_adaptar_merge_idempotente PASO")

    print()
    print("=== Test: Merge vs Overwrite ===")
    test_adaptar_merge_vs_overwrite()
    print("   OK: test_adaptar_merge_vs_overwrite PASO")

    print()
    print("Todos los tests pasaron correctamente.")

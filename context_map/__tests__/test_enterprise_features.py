import os
import shutil
import tempfile

from context_map.application.commands.hook import cmd_hook_install
from context_map.core.storage.config_loader import load_project_config
from context_map.domain.analysis.complexity import calcular_complejidad_archivo


def test_hook_install_creates_pre_commit_script() -> None:
    """Verifica que cmd_hook_install cree el archivo ejecutable .git/hooks/pre-commit."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_hook_")
    git_dir = os.path.join(temp_dir, ".git")
    os.makedirs(git_dir, exist_ok=True)

    try:
        class Args:
            target = temp_dir

        cmd_hook_install(Args())
        hook_path = os.path.join(git_dir, "hooks", "pre-commit")
        assert os.path.exists(hook_path)

        with open(hook_path, encoding="utf-8") as f:
            content = f.read()

        assert "ContextMap Auto-Sync Pre-Commit Hook" in content
        assert "ctxmap build" in content

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_load_project_config_reads_custom_toml() -> None:
    """Verifica la lectura de configuración desde .contextmap.toml."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_cfg_")
    toml_path = os.path.join(temp_dir, ".contextmap.toml")

    try:
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write('project_name = "TestEnterprise"\nmode = "hierarchical"\nignore_dirs = ["vendor"]\n')

        cfg = load_project_config(temp_dir)
        assert cfg.project_name == "TestEnterprise"
        assert cfg.mode == "hierarchical"
        assert "vendor" in cfg.ignore_dirs

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_calcular_complejidad_archivo() -> None:
    """Verifica el cálculo de complejidad ciclomática en un archivo Python."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_cc_")
    py_path = os.path.join(temp_dir, "sample.py")

    try:
        code = """def funcion_compleja(x):
    if x > 10:
        for i in range(x):
            if i % 2 == 0:
                print(i)
    elif x < 0:
        while x < 0:
            x += 1
    return x
"""
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(code)

        res = calcular_complejidad_archivo(py_path, temp_dir)
        assert res is not None
        assert res.max_complejidad_funcion >= 5
        assert len(res.funciones_complejas) > 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_git_repo_name_detection() -> None:
    """Verifica que _git_repo_name extraiga el nombre del repositorio de GitHub."""
    from context_map.application.commands._helpers import _git_repo_name
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_gitname_")
    git_dir = os.path.join(temp_dir, ".git")
    os.makedirs(git_dir, exist_ok=True)
    config_path = os.path.join(git_dir, "config")

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            f.write('[remote "origin"]\n\turl = https://github.com/usuario/MiRepoGithub.git\n')

        repo_name = _git_repo_name(temp_dir)
        assert repo_name == "MiRepoGithub"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_complexity_cross_drive_handling() -> None:
    """Verifica la tolerancia a diferentes unidades de disco en calcular_complejidad_archivo."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_crossdrive_")
    py_path = os.path.join(temp_dir, "sample.py")

    try:
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("def foo(): pass\n")

        res = calcular_complejidad_archivo(py_path, ruta_base="Z:\\DiferenteUnidad")
        assert res is not None

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_auto_command_orchestrates_full_workflow() -> None:
    """Verifica que cmd_auto ejecute el flujo de escaneo y generación en 1 solo paso."""
    from context_map.application.commands.auto import cmd_auto

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_auto_")
    py_path = os.path.join(temp_dir, "app.py")

    try:
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("# TODO: test auto command\ndef main(): pass\n")

        class Args:
            target = temp_dir
            project = "TestAuto"
            quiet = True
            mode = "hierarchical"
            raw = False

        cmd_auto(Args())

        context_dir = os.path.join(temp_dir, ".context-map")
        assert os.path.exists(context_dir)
        brief_path = os.path.join(context_dir, "CONTEXT.md")
        assert os.path.exists(brief_path)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_clean_vault_dir_preserva_manuales() -> None:
    """Verifica que build --clean NO borra la zona .manual/ ni las notas preserve:true."""
    from context_map.application.commands._helpers import clean_vault_dir, vault_dir

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_manual_")
    old_cwd = os.getcwd()
    try:
        os.chdir(temp_dir)
        vdir = vault_dir("TestManual")
        os.makedirs(os.path.join(vdir, ".manual"), exist_ok=True)
        os.makedirs(os.path.join(vdir, "2.0-IDEAS"), exist_ok=True)

        with open(os.path.join(vdir, ".manual", "SESION-2026-08-09.md"), "w", encoding="utf-8") as f:
            f.write("---\ntype: nota-manual\n---\n# Sesión\n")
        with open(os.path.join(vdir, "2.0-IDEAS", "idea-manual.md"), "w", encoding="utf-8") as f:
            f.write("---\npreserve: true\n---\n# Idea preservada\n")
        with open(os.path.join(vdir, "2.0-IDEAS", "idea-generada.md"), "w", encoding="utf-8") as f:
            f.write("---\ntype: idea\n---\n# Idea generada\n")

        n = clean_vault_dir("TestManual")

        assert os.path.exists(os.path.join(vdir, ".manual", "SESION-2026-08-09.md"))
        assert os.path.exists(os.path.join(vdir, "2.0-IDEAS", "idea-manual.md"))
        assert not os.path.exists(os.path.join(vdir, "2.0-IDEAS", "idea-generada.md"))
        assert n >= 2, f"Esperaba >=2 notas manuales preservadas, obtuve {n}"
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_refresh_command_actualiza_contexto_sin_clean() -> None:
    """Verifica que ctxmap refresh corre scan+build+check y NO usa --clean."""
    import json

    from context_map.application.commands.refresh import cmd_refresh

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_refresh_")
    py_path = os.path.join(temp_dir, "app.py")

    try:
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("# TODO: test refresh\ndef main(): pass\n")

        class Args:
            target = temp_dir
            project = "TestRefresh"
            quiet = True

        cmd_refresh(Args())

        context_dir = os.path.join(temp_dir, ".context-map")
        brief_path = os.path.join(context_dir, "CONTEXT.md")
        assert os.path.exists(brief_path)
        with open(brief_path, encoding="utf-8") as f:
            brief = f.read()
        assert "¿Qué es y por qué existe?" in brief

        # El refresh genera la skill de ContextMap (el CÓMO)
        skill_path = os.path.join(context_dir, "contextmap-skill.md")
        assert os.path.exists(skill_path)

        # El refresh NUNCA marca clean=True en el último build
        last_build = os.path.join(context_dir, "state", "last_build.json")
        assert os.path.exists(last_build)
        with open(last_build, encoding="utf-8") as f:
            info = json.load(f)
        assert info["clean"] is False
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_agents_md_es_que_y_skill_es_como() -> None:
    """Verifica la separación de niveles: AGENTS.md = QUÉ (referencias), skill = CÓMO."""
    from context_map.presentation.briefs import (
        generar_instrucciones_agentes,
        generar_skill_contextmap,
    )

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_que_como_")
    try:
        agents_path = generar_instrucciones_agentes(
            "Demo", target_dir=temp_dir, overwrite_if_exists=False
        )
        skill_path = generar_skill_contextmap("Demo", target_dir=temp_dir)

        with open(agents_path, encoding="utf-8") as f:
            agents_txt = f.read()
        with open(skill_path, encoding="utf-8") as f:
            skill_txt = f.read()

        # AGENTS.md: instrucciones QUÉ + referencia a la skill; SIN sintaxis de comandos
        assert "contextmap-skill.md" in agents_txt
        assert "LEE el contexto del proyecto ANTES" in agents_txt
        assert "Importar la historia del proyecto" in agents_txt
        assert "verifica el resultado" in agents_txt
        assert "python -m context_map.cli" not in agents_txt
        assert "ctxmap import-" not in agents_txt
        assert "ctxmap scan" not in agents_txt
        assert "ctxmap build --clean" not in agents_txt

        # Skill en .context-map/: el CÓMO — comandos exactos y metodología narrativa
        assert "import-git" in skill_txt
        assert "Cómo escribir las notas dándole vida" in skill_txt
        assert "Actualizar NO es solo correr el script" in skill_txt
        assert "CORRIGE" in skill_txt
        assert "7.0-MANUAL" in skill_txt
        assert "ctxmap refresh" in skill_txt
        assert "7.0-MANUAL/" in skill_txt
        assert "preserve: true" in skill_txt
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_brief_protocolo_anti_error_proyecto_equivocado() -> None:
    """Verifica que el AGENTS.md generado instruye verificar el proyecto correcto."""
    from context_map.presentation.briefs import generar_instrucciones_agentes

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_proyecto_")
    try:
        agents_path = generar_instrucciones_agentes(
            "MiApp", target_dir=temp_dir, overwrite_if_exists=False
        )
        with open(agents_path, encoding="utf-8") as f:
            txt = f.read()

        assert "Verificar el PROYECTO correcto" in txt
        assert "vault-MiApp" in txt
        assert "FRESCURA" in txt
        assert "ctxmap refresh" in txt
        assert "PENDIENTES REALES" in txt
        assert "BACKLOG.md" in txt
        assert "fuente de verdad" in txt
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_brief_refleja_pendientes_manuales_y_frescura() -> None:
    """Verifica que el brief incluye los pendientes del backlog manual y el estado de frescura.

    Este es el caso real del incidente Gemini/mi-app-utm: el backlog manual tenía
    pendientes pero el brief decía "No hay tareas pendientes" y el contexto estaba
    desactualizado sin aviso.
    """
    from context_map.core.models import Node
    from context_map.presentation.briefs import generar_brief

    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_brief_confiable_")
    try:
        # Crear el vault con backlog manual (pendientes conversados)
        vault = os.path.join(temp_dir, ".context-map", "vault-TestConfiable")
        manual = os.path.join(vault, "7.0-MANUAL")
        diario = os.path.join(manual, "Diario")
        state = os.path.join(temp_dir, ".context-map", "state")
        os.makedirs(diario, exist_ok=True)
        os.makedirs(state, exist_ok=True)

        with open(os.path.join(manual, "BACKLOG.md"), "w", encoding="utf-8") as f:
            f.write(
                "## ✅ HECHO\n- Algo listo\n\n"
                "## 📌 TAREAS PENDIENTES (con criterios de listo)\n\n"
                "### 1. Probar el flujo completo\n- **Qué**: validar la visión\n"
                "- **Cómo se sabe que está LISTO**: un proyecto real con vault\n\n"
                "### 2. Decidir el destino del Lienzo\n- **Qué**: decisión pendiente\n\n"
                "## 🚫 NO hacer\n- No tocar X\n"
            )
        # Diario manual MÁS NUEVO que el último build (contexto desactualizado)
        with open(os.path.join(diario, "2026-08-11.md"), "w", encoding="utf-8") as f:
            f.write("---\ntype: nota-dia\npreserve: true\n---\n# Diario\n")
        with open(os.path.join(state, "last_build.json"), "w", encoding="utf-8") as f:
            f.write('{"clean": false, "timestamp": "2026-08-10T10:00:00"}')

        nodo = Node(
            id="n1",
            type="FUTURO",
            title="TODO (modulo_x.py:L10): refactor pendiente",
            summary="deuda técnica",
        )
        brief_path = os.path.join(temp_dir, ".context-map", "CONTEXT.md")
        generar_brief("TestConfiable", [nodo], [], 90, brief_path, project_dir=temp_dir)

        with open(brief_path, encoding="utf-8") as f:
            brief = f.read()

        # Los pendientes manuales aparecen en el brief (el error que se cometió)
        assert "Probar el flujo completo" in brief
        assert "Decidir el destino del Lienzo" in brief
        assert "backlog manual" in brief
        # El TODO del código también aparece, pero etiquetado como deuda técnica
        assert "deuda técnica" in brief
        # Frescura: el diario es más nuevo que el build → aviso
        assert "Estado del Contexto" in brief
        assert "MÁS NUEVO" in brief
        assert "ctxmap refresh" in brief
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

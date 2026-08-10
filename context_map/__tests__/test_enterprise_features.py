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
        assert "python -m context_map.cli" not in agents_txt
        assert "ctxmap import-" not in agents_txt
        assert "ctxmap scan" not in agents_txt
        assert "ctxmap build --clean" not in agents_txt

        # Skill en .context-map/: el CÓMO — comandos exactos y metodología narrativa
        assert "import-git" in skill_txt
        assert "Cómo escribir las notas dándole vida" in skill_txt
        assert "ctxmap refresh" in skill_txt
        assert ".manual/" in skill_txt
        assert "preserve: true" in skill_txt
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

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

        with open(hook_path, "r", encoding="utf-8") as f:
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

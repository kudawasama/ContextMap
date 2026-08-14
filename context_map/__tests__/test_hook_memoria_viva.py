"""El pre-commit hook generado debe importar sesiones antes del build (R2).

Verifica que el script del hook (extraído a ``_script_hook``) invoque
``build --import-sessions`` para que cada commit registre la memoria viva
de las sesiones de Hermes del proyecto.
"""

from __future__ import annotations

import os
import shutil
import tempfile

from context_map.application.commands.hook import _script_hook, cmd_hook_install


def test_script_hook_incluye_import_sessions() -> None:
    """El script del hook usa ``--import-sessions`` en el build local."""
    script = _script_hook()
    assert "--import-sessions" in script
    # El fallback del binario global también debe importar sesiones.
    assert "ctxmap build --brief --quiet --import-sessions" in script


def test_hook_install_escribe_script_con_import_sessions() -> None:
    """``cmd_hook_install`` escribe el hook con la línea de importación."""
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_hook_r2_")
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

        assert "--import-sessions" in content
        assert "python -m context_map.cli build" in content
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

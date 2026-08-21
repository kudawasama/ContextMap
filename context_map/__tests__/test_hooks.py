"""Tests unitarios para hooks.py (instalador de Git hooks)."""

from __future__ import annotations

from context_map.domain.ecosystem.hooks import desinstalar_git_hooks, instalar_git_hooks


def test_instalar_git_hooks_en_repo_git(tmp_path):
    """Instala hooks pre-commit y post-commit en un directorio con .git."""
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)

    res = instalar_git_hooks(str(tmp_path))
    assert res["status"] == "OK"
    assert "éxito" in res["pre-commit"]
    assert "éxito" in res["post-commit"]

    pre = git_dir / "pre-commit"
    post = git_dir / "post-commit"
    assert pre.is_file()
    assert post.is_file()
    assert "ContextMap" in pre.read_text(encoding="utf-8")


def test_desinstalar_git_hooks(tmp_path):
    """Desinstala correctamente hooks instalados por ContextMap."""
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)

    instalar_git_hooks(str(tmp_path))
    res_des = desinstalar_git_hooks(str(tmp_path))
    assert res_des["status"] == "OK"
    assert res_des["pre-commit"] == "desinstalado"
    assert not (git_dir / "pre-commit").exists()

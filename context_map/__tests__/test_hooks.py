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


def test_hooks_priorizan_codigo_local(tmp_path):
    """Los hooks usan el código local antes que el binario global (AGENTS.md §4.3).

    Regresión (2026-09-25): el post-commit llamaba directo a ``ctxmap`` (global,
    posiblemente desactualizado); con un binario viejo, ``refresh`` reescribía el
    vault con lógica previa y pisaba notas del diario.
    """
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    instalar_git_hooks(str(tmp_path))

    for nombre in ("pre-commit", "post-commit"):
        texto = (git_dir / nombre).read_text(encoding="utf-8")
        lineas = [ln.strip() for ln in texto.splitlines()]
        idx_local = next((i for i, ln in enumerate(lineas) if "-m context_map.cli" in ln), -1)
        idx_global = next((i for i, ln in enumerate(lineas) if ln.startswith("ctxmap ")), -1)
        assert idx_local != -1, f"{nombre} no invoca el código local"
        assert idx_global == -1 or idx_local < idx_global, (
            f"{nombre} prioriza el binario global sobre el código local"
        )


def test_hooks_usan_el_interprete_del_venv(tmp_path):
    """Los hooks prefieren el venv del proyecto antes que el `python` del PATH.

    Regresión (2026-10-07): el hook usaba el `python` global (sin `pymupdf`) y
    ensuciaba cada commit con avisos falsos de ingesta de documentos.
    """
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    instalar_git_hooks(str(tmp_path))

    for nombre in ("pre-commit", "post-commit"):
        texto = (git_dir / nombre).read_text(encoding="utf-8")
        assert "$CTXMAP_PY -m context_map.cli" in texto, f"{nombre} no usa el selector"
        # El venv (Windows y POSIX) se evalúa ANTES del `python` de último recurso.
        assert texto.index(".venv/Scripts/python.exe") < texto.index('CTXMAP_PY="python"')
        assert texto.index(".venv/bin/python") < texto.index('CTXMAP_PY="python"')
        assert 'command -v uv' in texto, "Debe considerar `uv run` como alternativa"

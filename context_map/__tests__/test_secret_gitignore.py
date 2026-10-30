"""El baúl y su auditoría no deben acabar en el repositorio por accidente."""

from __future__ import annotations

from context_map.application.commands.secrets import _asegurar_gitignore


def test_anade_entrada_idempotente(tmp_path) -> None:
    """Añade la entrada una sola vez, aunque se llame varias veces."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("dist/\n", encoding="utf-8")

    assert _asegurar_gitignore(str(tmp_path)) is True
    texto = (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert ".context-map/secure/" in texto

    assert _asegurar_gitignore(str(tmp_path)) is False
    assert texto.count(".context-map/secure/") == 1


def test_crea_gitignore_si_no_existe(tmp_path) -> None:
    """Si el repo no tiene .gitignore, lo crea con la entrada."""
    (tmp_path / ".git").mkdir()

    assert _asegurar_gitignore(str(tmp_path)) is True
    assert ".context-map/secure/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_no_toca_nada_sin_git(tmp_path) -> None:
    """Fuera de un repositorio Git no crea archivos."""
    assert _asegurar_gitignore(str(tmp_path)) is False
    assert not (tmp_path / ".gitignore").exists()


def test_detecta_entrada_sin_barra_final(tmp_path) -> None:
    """Una entrada equivalente ya presente no se duplica."""
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text(".context-map/secure\n", encoding="utf-8")

    assert _asegurar_gitignore(str(tmp_path)) is False


def test_busca_la_raiz_del_repositorio(tmp_path) -> None:
    """Si el proyecto es un subdirectorio, protege el .gitignore de la raíz."""
    (tmp_path / ".git").mkdir()
    proyecto = tmp_path / "sub" / "proyecto"
    proyecto.mkdir(parents=True)

    assert _asegurar_gitignore(str(proyecto)) is True
    assert ".context-map/secure/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_reconoce_worktree_con_git_archivo(tmp_path) -> None:
    """Un worktree tiene `.git` como archivo: también debe proteger su raíz."""
    (tmp_path / ".git").write_text("gitdir: ../otro/.git/worktrees/wt\n", encoding="utf-8")

    assert _asegurar_gitignore(str(tmp_path)) is True
    assert ".context-map/secure/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")

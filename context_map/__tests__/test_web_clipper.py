"""Web Clipper (G5): bookmarklet + captura desde el portapapeles del sistema."""

from __future__ import annotations

import glob
import os
from types import SimpleNamespace as NS

from context_map.application.commands import inbox as cmd_inbox
from context_map.domain.knowledge import clip


def test_bookmarklet_es_una_linea_y_pegable() -> None:
    """El bookmarklet debe ser pegable tal cual en un favorito o en un href."""
    js = clip.bookmarklet()
    assert js.startswith("javascript:")
    assert "\n" not in js, "Debe ser una sola línea"
    assert '"' not in js, "Sin comillas dobles: se incrusta en href=\"...\""
    assert "&" not in js, "Sin '&' para no requerir escapado HTML"
    assert "document.title" in js and "location.href" in js
    assert "navigator.clipboard" in js
    assert "ctxmap inbox add --clipboard" in js, "Debe recordar el comando de captura"


def test_html_bookmarklet_tiene_enlace_arrastrable() -> None:
    """El HTML expone el enlace arrastrable con instrucciones."""
    html = clip.html_bookmarklet()
    assert 'draggable="true"' in html
    assert 'href="javascript:' in html
    assert "ctxmap inbox add --clipboard" in html


def test_guardar_html_crea_el_archivo(tmp_path) -> None:
    """``guardar_html`` crea directorios y devuelve la ruta absoluta."""
    destino = os.path.join(str(tmp_path), ".context-map", "clip-bookmarklet.html")
    ruta = clip.guardar_html(destino)
    assert os.path.isfile(ruta)
    with open(ruta, encoding="utf-8") as f:
        assert "Web Clipper" in f.read()


def test_leer_portapapeles_usa_el_primer_comando_que_funciona(monkeypatch) -> None:
    """Si la herramienta existe y responde, se devuelve su salida limpia."""
    monkeypatch.setattr(clip.shutil, "which", lambda _cmd: "/usr/bin/falso")
    monkeypatch.setattr(
        clip.subprocess, "run",
        lambda *_a, **_k: NS(returncode=0, stdout="texto copiado\r\n"),
    )
    assert clip.leer_portapapeles([["falso"]]) == "texto copiado"


def test_leer_portapapeles_sin_herramienta_devuelve_vacio(monkeypatch) -> None:
    """Sin herramienta disponible degrada a cadena vacía (nunca revienta)."""
    monkeypatch.setattr(clip.shutil, "which", lambda _cmd: None)
    assert clip.leer_portapapeles([["inexistente"]]) == ""


def test_leer_portapapeles_tolera_fallos_y_prueba_el_siguiente(monkeypatch) -> None:
    """Un comando que falla no impide probar el siguiente de la lista."""
    monkeypatch.setattr(clip.shutil, "which", lambda _cmd: "/usr/bin/x")
    llamadas: list[list[str]] = []

    def _run(comando, **_kwargs):
        llamadas.append(list(comando))
        if len(llamadas) == 1:
            raise OSError("boom")
        return NS(returncode=1, stdout="")  # noqa: SIM300

    monkeypatch.setattr(clip.subprocess, "run", _run)
    assert clip.leer_portapapeles([["roto"], ["tambien_roto"]]) == ""
    assert len(llamadas) == 2, "Debe intentar todos los comandos"


def test_comandos_de_portapapeles_por_plataforma(monkeypatch) -> None:
    """Cada plataforma usa su herramienta nativa."""
    monkeypatch.setattr(clip.sys, "platform", "darwin")
    assert clip._comandos_portapapeles() == [["pbpaste"]]

    monkeypatch.setattr(clip.sys, "platform", "linux")
    monkeypatch.setattr(clip.os, "name", "posix")
    assert [c[0] for c in clip._comandos_portapapeles()] == ["wl-paste", "xclip", "xsel"]

    monkeypatch.setattr(clip.sys, "platform", "win32")
    monkeypatch.setattr(clip.os, "name", "nt")
    assert clip._comandos_portapapeles()[0][0] == "powershell"


def test_desglosar_markdown_extrae_titulo_y_url() -> None:
    """El texto del bookmarklet se desglosa en título legible + URL de origen."""
    titulo, url = clip.desglosar_markdown("- [RAG explicado](https://ejemplo.com/rag)\n\n> cita")
    assert titulo == "RAG explicado"
    assert url == "https://ejemplo.com/rag"
    assert clip.desglosar_markdown("texto suelto sin enlace") == ("", "")
    assert clip.desglosar_markdown("*") == ("", "")


def test_cli_inbox_add_desde_el_portapapeles(tmp_path, monkeypatch, capsys) -> None:
    """``ctxmap inbox add --clipboard`` guarda la nota en el inbox del vault."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    monkeypatch.setattr(cmd_inbox, "_resolver_vault", lambda _args: vdir)
    monkeypatch.setattr(
        clip, "leer_portapapeles", lambda: "- [Artículo](https://ejemplo.com)\n\n> cita"
    )

    cmd_inbox.cmd_inbox(NS(
        inbox_cmd="add", texto="", stdin=False, clipboard=True, title=None,
        tags="", source="", target=".",
    ))

    notas = glob.glob(os.path.join(vdir, "90-CONOCIMIENTO", "00-INBOX", "*.md"))
    assert notas, "Debe crear la nota en el inbox"
    assert "Nota capturada" in capsys.readouterr().out
    # El título viene del enlace Markdown y la URL queda como fuente.
    assert os.path.basename(notas[0]).endswith("articulo.md"), os.path.basename(notas[0])
    with open(notas[0], encoding="utf-8") as f:
        contenido = f.read()
    assert 'title: "Artículo"' in contenido
    assert 'source: "https://ejemplo.com"' in contenido, "Debe usar la URL como fuente"


def test_cli_inbox_add_con_portapapeles_vacio_no_crea_nota(tmp_path, monkeypatch, capsys) -> None:
    """Portapapeles vacío: mensaje claro y ninguna nota."""
    vdir = os.path.join(str(tmp_path), ".context-map", "vault-Test")
    monkeypatch.setattr(cmd_inbox, "_resolver_vault", lambda _args: vdir)
    monkeypatch.setattr(clip, "leer_portapapeles", lambda: "")

    cmd_inbox.cmd_inbox(NS(
        inbox_cmd="add", texto="", stdin=False, clipboard=True, title=None,
        tags="", source="", target=".",
    ))

    assert "Nada que capturar" in capsys.readouterr().out
    assert not glob.glob(os.path.join(vdir, "90-CONOCIMIENTO", "00-INBOX", "*.md"))


def test_cli_inbox_bookmarklet_genera_html(tmp_path, monkeypatch, capsys) -> None:
    """``ctxmap inbox bookmarklet --html`` deja el HTML arrastrable en .context-map."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        cmd_inbox, "_resolver_vault", lambda _args: os.path.join(".context-map", "vault-Test")
    )

    cmd_inbox.cmd_inbox(NS(inbox_cmd="bookmarklet", html=True, ruta="", json=False, target="."))
    salida = capsys.readouterr().out
    assert "Web Clipper" in salida
    assert os.path.isfile(os.path.join(".context-map", "clip-bookmarklet.html"))

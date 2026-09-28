"""Mundo CONOCIMIENTO: captura de fuentes (Web Clipper + YouTube).

Convierte fuentes externas en notas de la base de conocimiento PKM:

- ``--url``     → descarga el HTML y lo convierte a Markdown (equivalente al
  **Obsidian Web Clipper** del curso de HolaMundo).
- ``--youtube`` → baja la transcripción automática con ``yt-dlp`` y la limpia.

El resultado se captura en el inbox (``destino="inbox"``, por defecto) o directo
a la wiki como página de resumen (``destino="wiki"``), respetando siempre
``namespace: knowledge``.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import urllib.request
from html.parser import HTMLParser

from context_map.domain.knowledge import inbox, wiki

_IDIOMAS_SUBTITULOS = "es.*,en.*"


def _youtube_cmd(jsi: bool = True) -> list[str]:
    """Devuelve el comando (lista) para invocar yt-dlp (binario o vía uv).

    Args:
        jsi (bool): Si es True, agrega ``--js-runtimes deno`` (YouTube moderno
            exige un runtime JS para extraer; deno es el soportado por defecto).

    Returns:
        list[str]: Base del comando.
    """
    exe = shutil.which("yt-dlp")
    base = [exe] if exe else ["uv", "tool", "run", "yt-dlp"]
    if jsi:
        return base + ["--js-runtimes", "deno"]
    # Sin runtime JS: el cliente ``android`` extrae sin JavaScript.
    return base + ["--extractor-args", "youtube:player_client=android"]


def vtt_a_texto(vtt: str) -> str:
    """Convierte un subtítulo VTT (yt-dlp/YouTube) en texto plano continuo.

    Args:
        vtt (str): Contenido del archivo ``.vtt``.

    Returns:
        str: Texto limpio sin timestamps ni duplicados.
    """
    lineas = vtt.splitlines()
    texto: list[str] = []
    previo: str | None = None
    for ln in lineas:
        if ("-->" in ln or ln.strip() == "" or ln.startswith("WEBVTT")
                or ln.startswith("Kind:") or ln.startswith("Language:")):
            continue
        ln = re.sub(r"<[^>]+>", "", ln).strip()
        if not ln or ln == previo:
            continue
        previo = ln
        texto.append(ln)
    return re.sub(r"\s+", " ", " ".join(texto)).strip()


class _ExtractorHTML(HTMLParser):
    """Convierte HTML a Markdown plano (Web Clipper mínimo, sin dependencias).

    Maneja títulos, párrafos, encabezados, listas, enlaces, énfasis, código y
    bloques de cita; omite ``script/style/nav/header/footer``.
    """

    _IGNORAR = {"script", "style", "nav", "noscript", "svg", "iframe", "header", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.cola = ""
        self.titulo = ""
        self._en_titulo = False
        self._skip = 0
        self._en_pre = False
        self._pre: list[str] = []
        self._en_strong = 0
        self._en_em = 0
        self._en_code = 0
        self._en_a = 0
        self._a_href = ""

    def _flush(self) -> None:
        linea = re.sub(r"\s+", " ", self.cola).strip()
        if linea:
            self.parts.append(linea)
        self.cola = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in self._IGNORAR:
            self._skip += 1
            return
        if self._skip:
            return
        if t == "title":
            self._en_titulo = True
            return
        if t == "pre":
            self._en_pre = True
            return
        if t in ("strong", "b"):
            self._en_strong += 1
            self.cola += "**"
            return
        if t in ("em", "i"):
            self._en_em += 1
            self.cola += "*"
            return
        if t == "code":
            self._en_code += 1
            self.cola += "`"
            return
        if t == "a":
            self._en_a += 1
            self._a_href = str(dict(attrs).get("href") or "")
            self.cola += "["
            return
        if t == "br":
            self.cola += " "
            return
        if t in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.cola = "#" * int(t[1]) + " "
            return
        if t == "li":
            self.cola = "\n- "
            return
        if t == "blockquote":
            self._flush()
            self.cola = "> "
            return

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in self._IGNORAR:
            if self._skip:
                self._skip -= 1
            return
        if self._skip:
            return
        if t == "title":
            self.titulo = re.sub(r"\s+", " ", self.cola).strip()
            self.cola = ""
            self._en_titulo = False
            return
        if t == "pre":
            codigo = "\n".join(self._pre).strip()
            self.parts.append("```\n" + codigo + "\n```")
            self._pre = []
            self._en_pre = False
            return
        if t in ("strong", "b"):
            self._en_strong = max(0, self._en_strong - 1)
            self.cola += "**"
            return
        if t in ("em", "i"):
            self._en_em = max(0, self._en_em - 1)
            self.cola += "*"
            return
        if t == "code":
            self._en_code = max(0, self._en_code - 1)
            self.cola += "`"
            return
        if t == "a":
            self._en_a = max(0, self._en_a - 1)
            self.cola += f"]({self._a_href})" if self._a_href else ""
            return
        if t in ("p", "div", "ul", "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "table"):
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if self._en_pre:
            self._pre.append(data)
            return
        self.cola += data

    def markdown(self) -> str:
        self._flush()
        md = re.sub(r"\n{3,}", "\n\n", "\n".join(self.parts)).strip()
        return md


def html_a_markdown(html: str) -> tuple[str, str]:
    """Convierte HTML a (título, markdown).

    Args:
        html (str): Documento HTML crudo.

    Returns:
        tuple[str, str]: (título de la página, cuerpo en Markdown).
    """
    parser = _ExtractorHTML()
    parser.feed(html)
    parser.close()
    return parser.titulo, parser.markdown()


def descargar_html(url: str) -> str:
    """Descarga el HTML de una URL (best-effort, UA de navegador).

    Args:
        url (str): Dirección a descargar.

    Returns:
        str: HTML crudo.

    Raises:
        OSError: Si la descarga falla.
    """
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (ctxmap-captura; PKM)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return str(resp.read().decode("utf-8", errors="replace"))


def _titulo_youtube(url: str) -> str | None:
    """Intenta obtener el título del video con yt-dlp (best-effort)."""
    for jsi in (True, False):
        try:
            cmd = _youtube_cmd(jsi) + ["--skip-download", "--print", "title", url]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            continue
    return None


def descargar_transcripcion_youtube(
    url: str, titulo: str | None = None,
) -> tuple[str, str]:
    """Baja la transcripción automática de un video de YouTube y la limpia.

    Args:
        url (str): URL del video.
        titulo (str | None): Título a usar; si falta, se intenta obtener.

    Returns:
        tuple[str, str]: (título, texto de la transcripción).

    Raises:
        RuntimeError: Si yt-dlp no está disponible, falla o no hay subtítulos.
    """
    tmpdir = tempfile.mkdtemp(prefix="ctxmap_captura_")
    try:
        args_yt = [
            "--skip-download",
            "--write-auto-sub", "--write-sub",
            "--sub-langs", _IDIOMAS_SUBTITULOS,
            "--sub-format", "vtt",
            "-o", os.path.join(tmpdir, "captura.%(ext)s"),
            url,
        ]
        # yt-dlp puede devolver rc != 0 (p. ej. un idioma falla o hay avisos)
        # pero igual dejar subtítulos escritos. Se acepta el resultado si hay
        # archivos .vtt; si no, se reintenta sin runtime JS (cliente android).
        args_yt = [
            "--skip-download",
            "--write-auto-sub", "--write-sub",
            "--sub-langs", _IDIOMAS_SUBTITULOS,
            "--sub-format", "vtt",
            "-o", os.path.join(tmpdir, "captura.%(ext)s"),
            url,
        ]
        vtts: list[str] = []
        stderr_acumulado = ""
        for jsi in (True, False):
            res = subprocess.run(_youtube_cmd(jsi) + args_yt, capture_output=True, text=True, timeout=300)
            stderr_acumulado = (res.stderr or res.stdout or "")[-300:]
            vtts = sorted(f for f in os.listdir(tmpdir) if f.endswith(".vtt"))
            if vtts:
                break
        if not vtts:
            raise RuntimeError(f"yt-dlp no obtuvo transcripción: {stderr_acumulado}")
        with open(os.path.join(tmpdir, vtts[0]), encoding="utf-8", errors="ignore") as f:
            texto = vtt_a_texto(f.read())
        if not texto:
            raise RuntimeError("La transcripción salió vacía.")
        titulo_final = titulo or (_titulo_youtube(url) or "Transcripción de YouTube")
        return titulo_final, texto
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def capturar(
    vault_dir: str, contenido: str, titulo: str, fuente: str,
    destino: str = "inbox", entidades: str = "",
) -> dict[str, str]:
    """Guarda una captura en el mundo conocimiento (inbox o wiki).

    Args:
        vault_dir (str): Directorio raíz del vault.
        contenido (str): Texto o Markdown de la fuente.
        titulo (str): Título descriptivo.
        fuente (str): Origen (URL, video, archivo…).
        destino (str): ``"inbox"`` (defecto) o ``"wiki"``.
        entidades (str): Conceptos wiki separados por coma (solo con ``wiki``).

    Returns:
        dict[str, str]: Con ``destino`` y ``ruta`` (y ``entidades`` si aplica).

    Raises:
        ValueError: Si el destino es desconocido.
    """
    if destino == "wiki":
        res = wiki.ingresar(vault_dir, titulo, contenido, fuente=fuente, entidades=entidades)
        return {"destino": "wiki", "ruta": res["ruta"], "entidades": res["entidades"]}
    if destino == "inbox":
        ruta = inbox.crear_nota(vault_dir, contenido, titulo=titulo or None, fuente=fuente)
        return {"destino": "inbox", "ruta": ruta}
    raise ValueError(f"Destino desconocido: {destino!r} (usa 'inbox' o 'wiki')")


def capturar_desde_url(
    vault_dir: str, url: str, titulo: str = "", destino: str = "inbox",
    entidades: str = "",
) -> dict[str, str]:
    """Descarga una URL, la convierte a Markdown y la captura.

    Args:
        vault_dir (str): Directorio raíz del vault.
        url (str): Dirección web.
        titulo (str): Título opcional (si falta, se infiere del HTML).
        destino (str): ``"inbox"`` o ``"wiki"``.
        entidades (str): Conceptos wiki (si aplica).

    Returns:
        dict[str, str]: Detalle de la captura.
    """
    html = descargar_html(url)
    titulo_html, markdown = html_a_markdown(html)
    return capturar(
        vault_dir, markdown, titulo or titulo_html or "Captura web", url, destino, entidades,
    )

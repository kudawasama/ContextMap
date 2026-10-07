"""Web Clipper de ContextMap: portapapeles del sistema + bookmarklet.

Cierra el flujo **local-first** de captura web sin servidor ni extensiones:

1. El usuario arrastra el bookmarklet a su barra de favoritos: al pulsarlo copia
   la página actual (título + URL + selección en Markdown) al portapapeles.
2. En la terminal ejecuta ``ctxmap inbox add --clipboard`` y la nota cae en el
   inbox del Second Brain (``90-CONOCIMIENTO/00-INBOX``).

Todo con **librería estándar** (``subprocess`` para el portapapeles nativo) y
sin red: si no hay herramienta de portapapeles disponible, se devuelve ``""`` y
el usuario puede pegar el texto a mano (``ctxmap inbox add -``).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

# Enlace Markdown al inicio del texto: ``- [Título](https://url)``.
_PATRON_ENLACE = re.compile(r"^\s*[-*]?\s*\[([^\]]+)\]\((https?://[^)\s]+)\)")

# El bookmarklet se construye por partes y SIN comillas dobles ni '&': así puede
# incrustarse tal cual en un atributo ``href="..."`` de HTML.
_BOOKMARKLET_PARTES: tuple[str, ...] = (
    "javascript:(function(){",
    "var s='';try{s=window.getSelection().toString();}catch(e){s='';}",
    r"var m='- ['+document.title+']('+location.href+')';",
    r"if(s){m=m+'\n\n> '+s.replace(/\n+/g,'\n> ');}",
    "var ta=document.createElement('textarea');ta.value=m;",
    "document.body.appendChild(ta);ta.select();",
    "try{document.execCommand('copy');}catch(e){}",
    "if(navigator.clipboard){navigator.clipboard.writeText(m);}",
    "ta.remove();",
    "alert('ContextMap: copiado. Ahora ejecuta: ctxmap inbox add --clipboard');",
    "})();",
)


def bookmarklet() -> str:
    """Devuelve el bookmarklet (JavaScript de una sola línea) del Web Clipper.

    Copia al portapapeles un Markdown con ``- [título](url)`` y, si hay texto
    seleccionado, una cita en bloque.

    Returns:
        str: Código ``javascript:`` listo para pegar en un favorito.
    """
    return "".join(_BOOKMARKLET_PARTES)


def desglosar_markdown(texto: str) -> tuple[str, str]:
    """Extrae ``(título, url)`` de un enlace Markdown al inicio del texto.

    El bookmarklet copia ``- [Título](url)``; sin esto, la nota del inbox se
    titularía con el Markdown crudo. Si el texto no empieza por un enlace, se
    devuelve ``("", "")`` y el inbox usa su heurística normal.

    Args:
        texto (str): Texto capturado (normalmente del portapapeles).

    Returns:
        tuple[str, str]: Título y URL detectados, o ``("", "")``.
    """
    coincidencia = _PATRON_ENLACE.match(texto or "")
    if not coincidencia:
        return "", ""
    return coincidencia.group(1).strip(), coincidencia.group(2).strip()


def _comandos_portapapeles() -> list[list[str]]:
    """Comandos nativos para leer el portapapeles, en orden de preferencia.

    Returns:
        list[list[str]]: Comandos a probar según la plataforma (macOS, Windows,
        Linux/Wayland/X11). Lista vacía si la plataforma es desconocida.
    """
    if sys.platform == "darwin":
        return [["pbpaste"]]
    if os.name == "nt":
        return [["powershell", "-NoProfile", "-Command", "Get-Clipboard"]]
    return [
        ["wl-paste", "-n"],
        ["xclip", "-selection", "clipboard", "-o"],
        ["xsel", "--clipboard", "--output"],
    ]


def leer_portapapeles(comandos: list[list[str]] | None = None, timeout: int = 10) -> str:
    """Lee el portapapeles del sistema con herramientas nativas (sin dependencias).

    Args:
        comandos (list[list[str]] | None): Comandos a probar (inyectable en
            tests). Si es None, se autodetectan por plataforma.
        timeout (int): Segundos máximos por intento (default 10).

    Returns:
        str: Contenido del portapapeles, o ``""`` si no hay herramienta
        disponible o todas fallan (nunca lanza excepción).
    """
    for comando in comandos if comandos is not None else _comandos_portapapeles():
        if shutil.which(comando[0]) is None:
            continue
        try:
            resultado = subprocess.run(
                comando, capture_output=True, text=True, timeout=timeout, check=False,
            )
        except Exception:  # noqa: BLE001 — portapapeles es best-effort
            continue
        if resultado.returncode == 0:
            return resultado.stdout.rstrip("\r\n")
    return ""


def html_bookmarklet() -> str:
    """Página HTML mínima con el bookmarklet arrastrable a favoritos.

    Returns:
        str: Documento HTML con un enlace ``draggable`` e instrucciones.
    """
    return (
        "<!doctype html>\n"
        '<html lang="es">\n'
        "<head><meta charset=\"utf-8\">\n"
        "<title>ContextMap · Web Clipper</title></head>\n"
        "<body>\n"
        "<h1>ContextMap · Web Clipper</h1>\n"
        "<p>Arrastra este enlace a tu barra de favoritos:</p>\n"
        f'<p><a href="{bookmarklet()}" draggable="true">📥 Capturar en ContextMap</a></p>\n'
        "<p>Después, en la terminal:</p>\n"
        "<pre>ctxmap inbox add --clipboard</pre>\n"
        "</body>\n"
        "</html>\n"
    )


def guardar_html(ruta: str) -> str:
    """Escribe la página del bookmarklet en disco (crea los directorios).

    Args:
        ruta (str): Ruta del archivo ``.html`` a generar.

    Returns:
        str: La ruta absoluta escrita.
    """
    directorio = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(directorio, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html_bookmarklet())
    return os.path.abspath(ruta)

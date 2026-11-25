"""Registro de lecturas de archivos (evidencia de ``REG-INI-006``).

La regla dice: no propongas cambios sobre código que no has leído. Hasta ahora
eso solo se podía creer de palabra. Aquí se guarda la huella: cada vez que un
harness con hooks lee un archivo, se anota una línea con la ruta. El chequeo
``lecturas_previas`` cruza esa huella con los archivos que el commit tocó.

Tres decisiones:

* **El registro nunca estorba.** Si no se puede escribir, se pierde la evidencia,
  no la sesión: ningún método lanza excepciones.
* **Solo se guardan rutas relativas al proyecto y el origen.** Ni contenido ni
  rutas absolutas de la máquina: la huella no debe convertirse en una fuga.
* **Es un registro, no una bitácora de comandos.** Por eso vive aparte
  (``state/lecturas.jsonl``) y se rota por conteo, no por día.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Optional

#: Ruta relativa del registro dentro del proyecto.
RUTA_RELATIVA = os.path.join(".context-map", "state", "lecturas.jsonl")

#: Entradas que se conservan antes de rotar.
MAX_LINEAS = 5000

#: Claves que se aceptan en una entrada; cualquier otra se descarta.
CLAVES = ("ts", "ruta", "origen")

#: Nombres de campo donde los distintos harnesses ponen la ruta del archivo.
CAMPOS_RUTA = ("file_path", "path", "filePath", "notebook_path", "absolute_path")


def ruta_lecturas(project_dir: str = ".") -> str:
    """Ruta absoluta del registro de lecturas.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        str: Ruta del JSONL (exista o no).
    """
    return os.path.abspath(os.path.join(project_dir, RUTA_RELATIVA))


def _relativa(ruta: str, project_dir: str) -> str:
    """Normaliza una ruta para guardarla y compararla.

    Args:
        ruta (str): Ruta absoluta o relativa.
        project_dir (str): Raíz del proyecto.

    Returns:
        str: Ruta relativa al proyecto con separador ``/`` y sin distinguir
        mayúsculas en Windows.
    """
    try:
        absoluta = os.path.abspath(os.path.join(project_dir, ruta))
        relativa = os.path.relpath(absoluta, os.path.abspath(project_dir))
    except (OSError, ValueError):
        relativa = ruta
    return os.path.normcase(relativa).replace(os.sep, "/")


def registrar_lectura(
    ruta: str,
    project_dir: str = ".",
    origen: str = "hook",
) -> bool:
    """Anota que un archivo se leyó. Nunca falla.

    Args:
        ruta (str): Ruta leída (absoluta o relativa al proyecto).
        project_dir (str): Raíz del proyecto.
        origen (str): Harness o mecanismo que lo reporta.

    Returns:
        bool: ``True`` si la entrada se escribió.
    """
    if not ruta:
        return False
    try:
        archivo = ruta_lecturas(project_dir)
        os.makedirs(os.path.dirname(archivo), exist_ok=True)
        entrada = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "ruta": _relativa(ruta, project_dir)[:300],
            "origen": str(origen)[:40],
        }
        with open(archivo, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        _rotar(archivo)
        return True
    except Exception:  # noqa: BLE001 - el registro no puede romper la sesión
        return False


def leer_lecturas(project_dir: str = ".") -> list[dict[str, Any]]:
    """Lee el registro entero tolerando líneas corruptas.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        List[Dict[str, Any]]: Entradas válidas, en orden de escritura.
    """
    entradas: list[dict[str, Any]] = []
    try:
        with open(ruta_lecturas(project_dir), encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    datos = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if isinstance(datos, dict) and datos.get("ruta"):
                    entradas.append({k: datos.get(k) for k in CLAVES if k in datos})
    except OSError:
        return []
    return entradas


def rutas_leidas(project_dir: str = ".") -> set[str]:
    """Conjunto de rutas leídas, normalizadas para comparar.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Set[str]: Rutas relativas normalizadas.
    """
    return {
        str(entrada["ruta"]).replace(os.sep, "/").lower()
        for entrada in leer_lecturas(project_dir)
    }


def primera_lectura(project_dir: str = ".") -> Optional[str]:
    """Instante de la primera lectura registrada.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Optional[str]: ISO 8601 de la primera entrada, o ``None``.
    """
    entradas = leer_lecturas(project_dir)
    if not entradas or not entradas[0].get("ts"):
        return None
    return str(entradas[0]["ts"])


def hay_registro(project_dir: str = ".") -> bool:
    """Indica si existe el registro (aunque esté vacío).

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        bool: ``True`` si el archivo existe.
    """
    return os.path.exists(ruta_lecturas(project_dir))


def extraer_ruta(datos: Any) -> str:
    """Busca la ruta del archivo dentro del JSON que envía un harness.

    Los hooks de ``PreToolUse`` no tienen un formato único: cambian el nombre del
    campo y a veces lo anidan en ``tool_input``. Se prueban las formas conocidas
    y, si ninguna aparece, se devuelve cadena vacía (no se inventa una ruta).

    Args:
        datos (Any): JSON ya parseado.

    Returns:
        str: Ruta encontrada o ``""``.
    """
    if isinstance(datos, str):
        return datos.strip()
    if not isinstance(datos, dict):
        return ""
    for campo in CAMPOS_RUTA:
        valor = datos.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    for anidado in ("tool_input", "toolInput", "input", "arguments", "args"):
        if anidado in datos:
            encontrada = extraer_ruta(datos[anidado])
            if encontrada:
                return encontrada
    return ""


def _rotar(archivo: str) -> None:
    """Rota el registro cuando pasa de :data:`MAX_LINEAS`.

    Args:
        archivo (str): Ruta del JSONL.
    """
    try:
        with open(archivo, encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
        if len(lineas) <= MAX_LINEAS:
            return
        recorte = lineas[-MAX_LINEAS:]
        with open(archivo, "w", encoding="utf-8", newline="\n") as f:
            f.writelines(recorte)
    except OSError:
        return

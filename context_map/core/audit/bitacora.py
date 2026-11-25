"""Bitácora de ejecuciones del motor (evidencia de lo que se hizo, no de lo que se dice).

Las reglas de conducta del catálogo —diagnosticar antes de tocar, cerrar con la
puerta en verde, no ejecutar `adapt` sin permiso— hablan de actos que ocurren en
la sesión y que, sin registro, solo se pueden creer de palabra. Este módulo deja
la huella mínima: cada comando de la CLI anota **qué** se ejecutó, **cuándo**,
**con qué resultado** y **cuánto tardó**.

Tres decisiones que no conviene deshacer:

1. **El registro lo escribe el motor, no el agente.** Un agente que declara «ya
   ejecuté el doctor» no produce evidencia; el proceso que corre sí.
2. **La bitácora nunca copia datos sensibles.** Solo el nombre del comando, sus
   banderas y un código de salida: nada de rutas de secretos ni contenido.
3. **Rotación acotada.** Es un archivo de estado, no un histórico: se conservan
   las últimas ``MAX_LINEAS`` entradas para que un proyecto viejo no arrastre un
   log infinito.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

#: Ruta relativa de la bitácora dentro del proyecto.
RUTA_RELATIVA = os.path.join(".context-map", "state", "bitacora.jsonl")

#: Entradas que se conservan antes de rotar (con la más antigua de resumen).
MAX_LINEAS = 2000

#: Comandos que modifican el proyecto y por tanto exigen autorización explícita.
COMANDOS_CON_PERMISO = ("adapt", "ingest", "enrich", "push")

#: Código de salida de una tarea cara que se negó a correr sin ``--confirmar``.
#: No es un fallo: es la puerta haciendo su trabajo, y la bitácora no lo cuenta
#: como ejecución no autorizada (nada se ejecutó).
CODIGO_RECHAZO = 2

#: Claves que se aceptan en una entrada; cualquier otra se descarta.
CLAVES = ("ts", "comando", "exit", "duracion_s", "flags", "notas", "autorizado")


def ruta_bitacora(project_dir: str = ".") -> str:
    """Devuelve la ruta absoluta de la bitácora de un proyecto.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        str: Ruta del archivo ``bitacora.jsonl``.
    """
    return os.path.join(os.path.abspath(project_dir), RUTA_RELATIVA)


def registrar(
    comando: str,
    exit_code: int = 0,
    duracion_s: float | None = None,
    flags: list[str] | None = None,
    notas: int | None = None,
    autorizado: bool | None = None,
    project_dir: str = ".",
) -> None:
    """Añade una entrada a la bitácora del proyecto.

    Nunca lanza: si el proyecto no tiene ``.context-map/`` o el disco no deja
    escribir, la ejecución del comando sigue. Un registro que tumba el comando
    que registra es peor que no tener registro.

    Args:
        comando (str): Nombre del comando ejecutado (``doctor``, ``check``…).
        exit_code (int): Código de salida del proceso.
        duracion_s (Optional[float]): Segundos que tardó la ejecución.
        flags (Optional[List[str]]): Banderas relevantes, sin valores de rutas.
        notas (Optional[int]): Notas del vault tras el comando (solo ``build``).
        autorizado (Optional[bool]): Para comandos que exigen permiso, si lo hubo.
        project_dir (str): Raíz del proyecto.
    """
    try:
        entrada: dict[str, Any] = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "comando": str(comando),
            "exit": int(exit_code),
        }
        if duracion_s is not None:
            entrada["duracion_s"] = round(float(duracion_s), 2)
        if flags:
            entrada["flags"] = sorted(str(f) for f in flags)
        if notas is not None:
            entrada["notas"] = int(notas)
        if autorizado is not None:
            entrada["autorizado"] = bool(autorizado)

        ruta = ruta_bitacora(project_dir)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        _rotar(ruta)
    except Exception:  # noqa: BLE001 - la bitácora jamás interrumpe el comando
        pass


def leer(project_dir: str = ".", limite: int | None = None) -> list[dict[str, Any]]:
    """Lee las entradas de la bitácora, de la más antigua a la más reciente.

    Una línea corrupta se salta: el archivo lo escribe el propio motor, pero un
    corte de luz a mitad de escritura no debe invalidar el resto.

    Args:
        project_dir (str): Raíz del proyecto.
        limite (Optional[int]): Máximo de entradas recientes a devolver.

    Returns:
        List[Dict[str, Any]]: Entradas válidas en orden cronológico.
    """
    ruta = ruta_bitacora(project_dir)
    if not os.path.isfile(ruta):
        return []

    entradas: list[dict[str, Any]] = []
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                try:
                    dato = json.loads(linea)
                except json.JSONDecodeError:
                    continue
                if isinstance(dato, dict) and "comando" in dato:
                    entradas.append(dato)
    except OSError:
        return []

    if limite is not None and limite > 0:
        return entradas[-limite:]
    return entradas


def del_dia(project_dir: str = ".", fecha: str | None = None) -> list[dict[str, Any]]:
    """Entradas registradas en una fecha (por defecto, hoy).

    Args:
        project_dir (str): Raíz del proyecto.
        fecha (Optional[str]): Fecha en formato ``YYYY-MM-DD``.

    Returns:
        List[Dict[str, Any]]: Entradas de ese día.
    """
    dia = fecha or datetime.now().strftime("%Y-%m-%d")
    return [e for e in leer(project_dir) if str(e.get("ts", "")).startswith(dia)]


def primera_del_dia(project_dir: str = ".", comando: str = "") -> dict[str, Any] | None:
    """Primera entrada de hoy, opcionalmente de un comando concreto.

    Args:
        project_dir (str): Raíz del proyecto.
        comando (str): Si se indica, filtra por nombre de comando.

    Returns:
        Optional[Dict[str, Any]]: La entrada más antigua que cumpla el filtro.
    """
    for entrada in del_dia(project_dir):
        if not comando or entrada.get("comando") == comando:
            return entrada
    return None


def ultima(project_dir: str = ".", comando: str = "") -> dict[str, Any] | None:
    """Última entrada registrada, opcionalmente de un comando concreto.

    Args:
        project_dir (str): Raíz del proyecto.
        comando (str): Si se indica, filtra por nombre de comando.

    Returns:
        Optional[Dict[str, Any]]: La entrada más reciente que cumpla el filtro.
    """
    for entrada in reversed(leer(project_dir)):
        if not comando or entrada.get("comando") == comando:
            return entrada
    return None


def resumen(project_dir: str = ".") -> dict[str, Any]:
    """Cuenta las entradas por comando y resume las últimas ejecuciones.

    Args:
        project_dir (str): Raíz del proyecto.

    Returns:
        Dict[str, Any]: ``total``, ``por_comando`` (dict) y ``ultima`` (entrada).
    """
    entradas = leer(project_dir)
    por_comando: dict[str, int] = {}
    for entrada in entradas:
        nombre = str(entrada.get("comando", "?"))
        por_comando[nombre] = por_comando.get(nombre, 0) + 1
    return {
        "total": len(entradas),
        "por_comando": dict(sorted(por_comando.items())),
        "ultima": entradas[-1] if entradas else None,
    }


def _rotar(ruta: str, maximo: int = MAX_LINEAS) -> None:
    """Recorta la bitácora conservando las últimas ``maximo`` entradas.

    Args:
        ruta (str): Archivo de bitácora.
        maximo (int): Número de líneas a conservar.
    """
    try:
        if os.path.getsize(ruta) < 400_000:
            return
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lineas = [l for l in f if l.strip()]
        if len(lineas) <= maximo:
            return
        temporal = ruta + ".tmp"
        with open(temporal, "w", encoding="utf-8") as f:
            f.writelines(lineas[-maximo:])
        os.replace(temporal, ruta)
    except Exception:  # noqa: BLE001 - la rotación es una cortesía, no un deber
        pass

"""Evidencia de la sesión: lo que el motor ejecutó, no lo que se cuenta.

``REG-EJE-005`` pide verificar con la salida real de los comandos y nunca con el
autoreporte. La diferencia no vive en el repositorio —está en si el número que
se enseña salió de un comando o de la memoria de quien lo cuenta—, así que no se
audita la prosa: se **lee el registro**.

Este módulo arma ese informe a partir de dos fuentes que el propio motor
escribe: la bitácora (``.context-map/state/bitacora.jsonl``) y la huella de
lecturas (``.context-map/state/lecturas.jsonl``). Nunca interpreta texto libre:
si un dato no está en el registro, se declara ausente en vez de suponerse.

Lo que la bitácora no puede ver también se declara: ``pytest`` no pasa por la
CLI, así que un «los tests pasan» no tiene evidencia aquí. Decirlo es más útil
que fingir cobertura.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from context_map.core.audit.bitacora import del_dia, leer
from context_map.core.audit.lecturas import leer_lecturas

# Puertas que dejan huella en la bitácora y su regla asociada.
PUERTAS: dict[str, str] = {
    "brief": "REG-INI-002",
    "doctor": "REG-INI-001",
    "check": "REG-EJE-002",
    "reglas": "REG-EJE-004",
}

# Lo que ocurre fuera de la CLI y por tanto no deja rastro medible.
FUERA_DE_ALCANCE = (
    "pytest (se ejecuta con el intérprete, no con la CLI)",
    "lo que el agente escribe en el chat",
)

CAMPOS_EJECUCION = ("ts", "comando", "exit", "duracion_s", "flags", "fallos", "autorizado")

LIMITE_EJECUCIONES = 20


def _ruta_proyecto(project_dir: str) -> str:
    """Devuelve el nombre del proyecto a partir de su ruta."""
    return os.path.basename(os.path.abspath(project_dir)) or project_dir


def _ejecucion(entrada: dict[str, Any]) -> dict[str, Any]:
    """Extrae de una entrada solo los campos declarados.

    La bitácora es un archivo del usuario: puede tener campos de versiones
    futuras o escritos a mano. Se copia lo que se conoce y nada más, para que el
    informe no transporte datos que no le tocan (ni rutas ni texto de comandos).
    """
    limpia: dict[str, Any] = {}
    for campo in CAMPOS_EJECUCION:
        if campo in entrada:
            limpia[campo] = entrada[campo]
    limpia.setdefault("comando", "?")
    limpia.setdefault("exit", 0)
    return limpia


def _puerta(entradas: list[dict[str, Any]], comando: str) -> dict[str, Any]:
    """Resume la última ejecución de una puerta.

    ``ok`` distingue aviso de fallo igual que la bitácora: si la entrada trae
    ``fallos``, manda ese número —``--strict-warn`` sale con código 1 también
    cuando solo hay avisos—; si no lo trae, manda el código de salida.
    """
    suyas = [e for e in entradas if e.get("comando") == comando]
    if not suyas:
        return {"comando": comando, "ejecutada": False, "ok": False, "ts": None}

    ultima = suyas[-1]
    fallos = ultima.get("fallos")
    if fallos is not None:
        ok = int(fallos) == 0
        avisos = int(ultima.get("exit", 0)) != 0 and ok
    else:
        ok = int(ultima.get("exit", 0)) == 0
        avisos = False

    return {
        "comando": comando,
        "ejecutada": True,
        "ok": ok,
        "avisos": avisos,
        "exit": int(ultima.get("exit", 0)),
        "ts": ultima.get("ts"),
        "fallos": fallos,
        "regla": PUERTAS.get(comando),
    }


def construir_evidencia(
    project_dir: str = ".",
    fecha: str | None = None,
    limite: int = LIMITE_EJECUCIONES,
) -> dict[str, Any]:
    """Arma el informe de evidencia de un día.

    Args:
        project_dir (str): Raíz del proyecto.
        fecha (Optional[str]): Día en formato ``YYYY-MM-DD`` (por defecto, hoy).
        limite (int): Máximo de ejecuciones a listar (no a contar).

    Returns:
        Dict[str, Any]: ``proyecto``, ``fecha``, ``total``, ``ejecuciones``,
        ``puertas``, ``lecturas``, ``estado``, ``faltantes`` y
        ``fuera_de_alcance``. ``sin_registro`` es ``True`` cuando no hay
        bitácora: sin registro no se juzga, se declara.
    """
    dia = fecha or datetime.now().strftime("%Y-%m-%d")
    entradas = [_ejecucion(e) for e in del_dia(project_dir, dia)]

    puertas = {nombre: _puerta(entradas, nombre) for nombre in PUERTAS}
    faltantes = [n for n, p in puertas.items() if not p["ejecutada"]]
    en_rojo = [n for n, p in puertas.items() if p["ejecutada"] and not p["ok"]]

    hay_historia = bool(leer(project_dir))
    if not hay_historia:
        estado = "sin-registro"
    elif not entradas:
        estado = "sin-actividad"
    elif en_rojo:
        estado = "incompleta"
    elif faltantes:
        estado = "incompleta"
    else:
        estado = "completa"

    lecturas = [x for x in leer_lecturas(project_dir) if str(x.get("ts", "")).startswith(dia)]

    recortadas = entradas[-limite:] if limite and limite > 0 else entradas

    return {
        "proyecto": _ruta_proyecto(project_dir),
        "fecha": dia,
        "total": len(entradas),
        "ejecuciones": recortadas,
        "omitidas": max(0, len(entradas) - len(recortadas)),
        "puertas": puertas,
        "faltantes": faltantes,
        "en_rojo": en_rojo,
        "lecturas": len(lecturas),
        "archivos_leidos": sorted({str(x.get("ruta", "")) for x in lecturas if x.get("ruta")}),
        "estado": estado,
        "sin_registro": not hay_historia,
        "fuera_de_alcance": list(FUERA_DE_ALCANCE),
    }


def formatear_evidencia_texto(reporte: dict[str, Any]) -> str:
    """Devuelve el informe de evidencia en texto legible.

    Args:
        reporte (Dict[str, Any]): Salida de :func:`construir_evidencia`.

    Returns:
        str: Texto listo para imprimir.
    """
    lineas: list[str] = []
    lineas.append("")
    lineas.append(f"🔎 Evidencia de la sesión — {reporte['fecha']}")
    lineas.append("=" * 60)
    lineas.append(f"  proyecto: {reporte['proyecto']} · {reporte['total']} ejecución(es) registrada(s)")

    if reporte["sin_registro"]:
        lineas.append("")
        lineas.append("  ⚠️  Sin bitácora en este proyecto: no hay evidencia que leer.")
        lineas.append("      Sin registro no se juzga (la primera entrada la escribe el primer comando).")
        return "\n".join(lineas) + "\n"

    if not reporte["total"]:
        lineas.append("")
        lineas.append("  (sin ejecuciones registradas hoy: no se puede juzgar la sesión)")
        return "\n".join(lineas) + "\n"

    lineas.append("")
    for e in reporte["ejecuciones"]:
        hora = str(e.get("ts", ""))[11:19] or "--:--:--"
        duracion = f"{float(e['duracion_s']):6.1f}s" if e.get("duracion_s") is not None else " " * 7
        extra = ""
        if e.get("fallos") is not None:
            extra = f"  fallos={e['fallos']}"
        elif e.get("flags"):
            extra = "  " + " ".join(f"--{f}" for f in e["flags"])
        lineas.append(f"  {hora}  {str(e.get('comando', '?')):10} exit {e.get('exit', 0)}{extra}  {duracion}")

    if reporte["omitidas"]:
        lineas.append(f"  … y {reporte['omitidas']} ejecución(es) más antiguas de hoy")

    lineas.append("")
    partes = []
    for nombre in PUERTAS:
        puerta = reporte["puertas"][nombre]
        if not puerta["ejecutada"]:
            partes.append(f"{nombre} ❌")
        elif not puerta["ok"]:
            partes.append(f"{nombre} ❌")
        elif puerta.get("avisos"):
            partes.append(f"{nombre} ⚠️")
        else:
            partes.append(f"{nombre} ✅")
    lineas.append("  Puertas: " + " · ".join(partes))

    if reporte["faltantes"]:
        lineas.append(f"  Faltan: {', '.join(reporte['faltantes'])} (no se ejecutó, no se supone)")
    lineas.append(f"  Lecturas registradas: {reporte['lecturas']} archivo(s)")
    lineas.append(f"  Sin evidencia aquí: {', '.join(reporte['fuera_de_alcance'])}")
    return "\n".join(lineas) + "\n"

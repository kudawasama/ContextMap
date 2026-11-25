"""Comando CLI 'reglas': consulta el catálogo de reglas fijas del proyecto.

Hasta ahora el catálogo solo se podía leer abriendo el YAML o el brief. Este
comando lo hace consultable y, con ``--verificar``, dice **cuáles están
incumplidas ahora mismo** cruzando cada regla con el chequeo del doctor que la
mide. Una regla que no se puede consultar acaba siendo un adorno.
"""

from __future__ import annotations

import json
import sys
from typing import Any

from context_map.domain.health.doctor import diagnosticar_salud
from context_map.domain.reglas.reglas import reglas_del_proyecto

#: Orden de presentación: primero lo que más se rompe en la práctica.
ORDEN_CATEGORIAS = (
    "REG-VLT", "REG-ETQ", "REG-EJE", "REG-INI", "REG-SAL",
    "REG-HUM", "REG-DOC", "REG-MEM", "REG-ARQ", "REG-SEG",
    "REG-PUB", "REG-LIM",
)

SIMBOLO_PRIORIDAD = {"critica": "🔴", "alta": "🟠", "media": "🟡"}
SIMBOLO_ESTADO = {"OK": "✅", "WARN": "⚠️", "FAIL": "❌", "test": "🧪"}


def _orden(regla: dict[str, Any]) -> tuple[int, str]:
    categoria = str(regla.get("categoria", ""))
    posicion = (
        ORDEN_CATEGORIAS.index(categoria)
        if categoria in ORDEN_CATEGORIAS
        else len(ORDEN_CATEGORIAS)
    )
    return (posicion, str(regla.get("id", "")))


def _filtrar(reglas: list[dict], categoria: str, prioridad: str) -> list[dict]:
    """Aplica los filtros de categoría y prioridad (vacíos = sin filtro)."""
    salida = reglas
    if categoria:
        buscada = categoria.upper()
        if not buscada.startswith("REG-"):
            buscada = f"REG-{buscada}"
        salida = [r for r in salida if str(r.get("categoria", "")).upper() == buscada]
    if prioridad:
        salida = [
            r for r in salida
            if str(r.get("prioridad", "")).lower() == prioridad.lower()
        ]
    return salida


def _estados_del_doctor(target_dir: str) -> dict[str, str]:
    """Mapa ``chequeo -> estado`` del doctor, para saber qué regla se incumple."""
    report = diagnosticar_salud(target_dir)
    return {check.name: check.status for check in report.checks}


def _resumen(regla: dict[str, Any]) -> str:
    """Resumen de una línea, también para catálogos con otro esquema.

    Los catálogos escritos a mano antes de esta convención no tienen
    ``resumen``: ahí se corta el ``nombre`` para no imprimir ``None``.
    """
    resumen = str(regla.get("resumen") or "").strip()
    if resumen:
        return resumen
    nombre = str(regla.get("nombre") or regla.get("id") or "").strip()
    return nombre if len(nombre) <= 60 else nombre[:57] + "..."


def _verificacion(regla: dict[str, Any]) -> str:
    """Cómo se comprueba la regla, entendiendo los dos esquemas en uso.

    El esquema nuevo usa ``verificacion`` (``doctor:x``/``test:x``/``manual``);
    los catálogos antiguos declaraban ``test: nombre_del_test.py``.
    """
    verif = str(regla.get("verificacion") or "").strip()
    if verif:
        return verif
    test = str(regla.get("test") or "").strip()
    return f"test:{test}" if test else "manual"


def _es_automatica(regla: dict[str, Any]) -> bool:
    """¿La comprueba la máquina (un chequeo del doctor o un test)?"""
    return _verificacion(regla).startswith(("doctor:", "test:"))


def _estado_de(regla: dict[str, Any], estados: dict[str, str]) -> str:
    """Estado de la regla según su verificación.

    ``doctor:`` se resuelve contra el reporte del doctor; ``test:`` se marca
    como tal sin ejecutar la suite (demasiado caro para un listado); el resto
    es conducta auditable y se muestra como ``·``.
    """
    verif = _verificacion(regla)
    if verif.startswith("doctor:"):
        return estados.get(verif.split(":", 1)[1], "?")
    if verif.startswith("test:"):
        return "test"
    return "·"


def cmd_reglas(args: dict[str, Any]) -> None:
    """Manejador del comando CLI ``ctxmap reglas``.

    Args:
        args (dict[str, Any]): Argumentos parseados de la CLI.
    """
    target_dir = args.get("target_dir") or "."
    categoria = str(args.get("categoria") or "")
    prioridad = str(args.get("prioridad") or "")
    verificar = bool(args.get("verificar"))
    como_json = bool(args.get("json"))

    reglas = sorted(reglas_del_proyecto(target_dir), key=_orden)
    if not reglas:
        mensaje = (
            "No hay catálogo de reglas en este proyecto "
            "(references/reglas/reglas_registro.yaml)."
        )
        if como_json:
            print(json.dumps({"reglas": [], "aviso": mensaje}, ensure_ascii=False))
        else:
            print(f"⚠️  {mensaje}", file=sys.stderr)
            print(
                "   Una regla sin norma escrita no existe: escribe la norma en el\n"
                "   repo (AGENTS.md / docs/GOBERNANZA-AGENTES.md) y luego la regla.",
                file=sys.stderr,
            )
        return

    reglas = _filtrar(reglas, categoria, prioridad)
    estados = _estados_del_doctor(target_dir) if verificar else {}
    automaticas = sum(1 for r in reglas if _es_automatica(r))

    if como_json:
        payload = []
        for regla in reglas:
            item = dict(regla)
            if verificar:
                item["estado_actual"] = _estado_de(regla, estados)
            payload.append(item)
        print(json.dumps(
            {
                "total": len(payload),
                "verificadas_por_la_maquina": automaticas,
                "reglas": payload,
            },
            ensure_ascii=False,
            indent=2,
        ))
        return

    titulo = "Reglas fijas del proyecto"
    if categoria:
        titulo += f" · {categoria.upper()}"
    if prioridad:
        titulo += f" · {prioridad.lower()}"
    print(f"\n📜 {titulo}")
    print("=" * 60)
    print(
        f"  {len(reglas)} regla(s) · {automaticas} las comprueba la máquina "
        f"(doctor/test) · {len(reglas) - automaticas} son conducta auditable"
    )

    categoria_actual = ""
    for regla in reglas:
        if str(regla.get("categoria")) != categoria_actual:
            categoria_actual = str(regla.get("categoria"))
            print(f"\n  ── {categoria_actual} · {regla.get('categoria_nombre', '')}")
        marca = SIMBOLO_PRIORIDAD.get(str(regla.get("prioridad", "")), "·")
        linea = f"   {marca} {regla.get('id')}  {_resumen(regla)}"
        if verificar:
            estado = _estado_de(regla, estados)
            linea += f"  {SIMBOLO_ESTADO.get(estado, estado)}"
        print(linea)
        print(
            f"      {_resumen(regla)}\n"
            f"      norma: {regla.get('norma')}"
            f"{(' → ' + str(regla['seccion'])) if regla.get('seccion') else ''}\n"
            f"      verifica: {_verificacion(regla)}"
        )

    incumplidas = [
        r for r in reglas
        if verificar and _estado_de(r, estados) in {"WARN", "FAIL"}
    ]
    print("\n" + "=" * 60)
    if verificar:
        if incumplidas:
            print(f"⚠️  {len(incumplidas)} regla(s) incumplida(s) ahora mismo:")
            for regla in incumplidas:
                print(f"   - {regla.get('id')}: {_resumen(regla)}")
            sys.exit(1)
        print("✅ Todas las reglas que la máquina comprueba están en verde.")
        return
    print(
        "🔎 `ctxmap reglas --verificar` cruza cada regla con el doctor y dice\n"
        "   cuáles están incumplidas ahora mismo."
    )

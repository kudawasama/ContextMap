"""Comando CLI 'doctor' para diagnóstico y auto-reparación Self-Healing."""

from __future__ import annotations

import json
from typing import Any

from context_map.domain.health.doctor import diagnosticar_salud, reparar_salud
from context_map.domain.health.pesos import ETIQUETAS, medir_pesos


def _imprimir_pesos(target_dir: str) -> None:
    """Imprime el desglose de peso de ``.context-map`` (``doctor --sizes``)."""
    datos = medir_pesos(target_dir)
    print("\n📦 Peso del contexto (.context-map)")
    print("=" * 50)
    if not datos["existe"]:
        print("  (este proyecto no tiene `.context-map` todavía)")
        return
    print(f"  TOTAL: {datos['total_bytes'] / 1048576:.1f} MB")
    print(
        f"  snapshots vivos: {datos['snapshots_vivos']}"
        f" · archivos comprimidos: {datos['archivos_comprimidos']}"
    )
    for area, bytes_ in sorted(datos["areas"].items(), key=lambda x: -x[1]):
        print(f"  {ETIQUETAS.get(area, area):38} {bytes_ / 1048576:8.1f} MB")
    if datos["alerta"]:
        print(f"  ⚠️ {datos['alerta']} — {datos['sugerencia']}")
    else:
        print("  ✅ peso dentro del tope")
    print("=" * 50)


def cmd_doctor(args: dict[str, Any]) -> None:
    """Manejador del comando CLI `ctxmap doctor`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI.
    """
    target_dir = args.get("target_dir") or "."
    fix = bool(args.get("fix", False))
    as_json = bool(args.get("json", False))
    sizes = bool(args.get("sizes", False))

    if sizes:
        datos = medir_pesos(target_dir)
        if as_json:
            print(json.dumps(datos, indent=2, ensure_ascii=False))
        else:
            _imprimir_pesos(target_dir)
        return

    report = reparar_salud(target_dir) if fix else diagnosticar_salud(target_dir)

    if as_json:
        data = {
            "ok": report.ok,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "fix_applied": c.fix_applied,
                    "fix_message": c.fix_message,
                }
                for c in report.checks
            ],
        }
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return

    modo_str = " (Modo Self-Healing --fix)" if fix else ""
    print(f"\n🏥 ContextMap Doctor Report{modo_str}")
    print("=" * 50)

    for c in report.checks:
        icono = "✅" if c.status == "OK" else ("⚠️" if c.status == "WARN" else "❌")
        fix_str = f" 🛠️ [Fix: {c.fix_message}]" if c.fix_applied else ""
        print(f"{icono} [{c.status}] {c.name}: {c.message}{fix_str}")

    print("=" * 50)
    if report.ok:
        print("✨ [OK] Sistema saludable y libre de fallos críticos.")
    else:
        print(f"⚠️ [ATENCIÓN] Encontrados {len(report.failed)} fallos. Corre `ctxmap doctor --fix` para reparar.")

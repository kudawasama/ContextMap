"""Comando CLI 'doctor' para diagnóstico y auto-reparación Self-Healing."""

from __future__ import annotations

import json
from typing import Any

from context_map.domain.health.doctor import diagnosticar_salud, reparar_salud


def cmd_doctor(args: dict[str, Any]) -> None:
    """Manejador del comando CLI `ctxmap doctor`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI.
    """
    target_dir = args.get("target_dir") or "."
    fix = bool(args.get("fix", False))
    as_json = bool(args.get("json", False))

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

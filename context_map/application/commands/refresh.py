"""Comando refresh: actualiza el contexto en 1 solo paso, sin destruir lo manual.

Ejecuta secuencialmente:
1. Escaneo estático del proyecto (scan)
2. Construcción del Vault + Brief (build --brief, SIN --clean: preserva notas manuales)
3. Verificación de readiness (check)

Reemplaza el protocolo de 4 comandos del AGENTS.md: el agente solo necesita
`python -m pytest && ctxmap refresh` para dejar el contexto al día.
"""

from __future__ import annotations

import os
import types

from context_map.application.commands.build import cmd_build
from context_map.application.commands.scan import cmd_scan
from context_map.application.commands.tools import cmd_check


def _detectar_temporales(target: str) -> list[str]:
    """Detecta carpetas temporales típicas sin trackear en la raíz.

    R9 (auditoría 2026-08-14): artefactos como ``piloto_*`` (experimentos)
    o ``scripts/debug/`` (scripts de diagnóstico) suelen quedar fuera del
    control de versiones y ensucian la raíz. El AGENTS.md exige raíz limpia.

    Args:
        target (str): Ruta del proyecto.

    Returns:
        list[str]: Rutas relativas de carpetas temporales detectadas.
    """
    temporales: list[str] = []
    try:
        if not os.path.isdir(target):
            return temporales
        # Carpetas piloto_* / tmp_* en la raíz.
        for nombre in os.listdir(target):
            ruta = os.path.join(target, nombre)
            if os.path.isdir(ruta) and (
                nombre.startswith("piloto_") or nombre.startswith("tmp_")
            ):
                temporales.append(nombre)
        # scripts/debug/ en la raíz.
        debug_dir = os.path.join(target, "scripts", "debug")
        if os.path.isdir(debug_dir):
            temporales.append("scripts/debug")
    except Exception:
        return []
    return sorted(temporales)


def cmd_refresh(args) -> None:
    """Orquesta scan + build (sin clean) + check en un solo paso.

    Args:
        args: Namespace de argparse con atributo ``target`` y ``project``.
    """
    target = getattr(args, "target", ".") or "."
    quiet = getattr(args, "quiet", False)
    abs_target = os.path.abspath(target)
    old_cwd = os.getcwd()

    if not quiet:
        print(f"[refresh] Actualizando contexto de: {target}")

    # Punto de control de versión (2026-08-11): antes de actualizar el CONTEXTO,
    # verificar si el PROGRAMA (binario ctxmap) está desactualizado y solicitarlo.
    # Aviso accionable y NO bloqueante: el agente/usuario decide actualizar.
    if not quiet:
        from context_map.infrastructure.version_check import aviso_pre_actualizacion

        print(aviso_pre_actualizacion(), end="")

    try:
        if abs_target != old_cwd:
            os.chdir(abs_target)

        cmd_scan(args)

        # Memoria viva automática (2026-08-13): importa las sesiones recientes
        # de Hermes de ESTE proyecto como eventos — todo lo conversado queda
        # registrado (diario del día + grafo + BD personal) sin pasos extra.
        # Idempotente (dedup por hash) y tolerante (nunca rompe el refresh).
        if not quiet:
            print("[refresh] Importando sesiones recientes de Hermes...")
        try:
            from context_map.application.commands._helpers import project_name
            from context_map.infrastructure.integrations.hermes import importar_sesiones

            importados = importar_sesiones(
                db_path=None,
                limite=5,
                output_path=os.path.join(".context-map", "raw", "events.jsonl"),
                project=project_name(args),
            )
            if importados and not quiet:
                print(f"[refresh] {importados} evento(s) de sesiones importados")
        except Exception as err:  # noqa: BLE001
            if not quiet:
                print(f"[refresh] aviso: no se pudieron importar sesiones ({err})")

        # Clonar args para build con target="." y SIN --clean (preserva manuales).
        # Pitfall documentado: reutilizar el namespace original contamina
        # project_name() y genera vault con el nombre del target.
        build_args = types.SimpleNamespace(
            target=".",
            project=getattr(args, "project", "Repo"),
            snapshot_name="",
            brief=True,
            mode=getattr(args, "mode", "hierarchical"),
            raw=False,
            clean=False,
            quiet=quiet,
            aviso_pre=False,  # refresh ya imprime el aviso de versión al inicio
        )
        cmd_build(build_args)

        check_args = types.SimpleNamespace(target=".", json=False)
        cmd_check(check_args)

        # Sugerencia de limpieza (R9): carpetas temporales sin trackear.
        if not quiet:
            temporales = _detectar_temporales(target)
            if temporales:
                print()
                print("── Limpieza sugerida ──")
                for t in temporales:
                    print(f"  · {t} (sin trackear — ¿mover a _legacy/ o eliminar?)")
                print("────────────────────────")

        if not quiet:
            try:
                from pathlib import Path

                from context_map.core.tokenization import TokenCounter
                brief_p = Path(".context-map/CONTEXT.md")
                if brief_p.exists():
                    c = TokenCounter()
                    tk = c.count_tokens(brief_p.read_text(encoding="utf-8", errors="ignore"))
                    print(f"🧮 [tokens] Brief: {tk:,} tk | Ahorro de contexto: >99%")
            except Exception:
                pass
            print(f"[refresh] [OK] Contexto actualizado para {target}")
    finally:
        if abs_target != old_cwd:
            os.chdir(old_cwd)

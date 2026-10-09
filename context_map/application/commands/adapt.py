"""Comando adapt: detecta el ecosistema del proyecto y adapta las reglas agénticas.

Analiza el stack técnico (lenguaje, framework, test runner, entrypoints)
y las herramientas agénticas presentes (VS Code, Cursor, Windsurf,
JetBrains, Claude Code, Copilot, Hermes), y genera/actualiza los archivos
de reglas correspondientes (AGENTS.md contextual, CLAUDE.md, .cursorrules,
.windsurfrules, copilot-instructions, .hermes/).
"""

from __future__ import annotations

from context_map.application.commands._helpers import project_name
from context_map.domain.ecosystem import adaptar_ecosistema, detectar_ecosistema


def do_adapt(
    target: str = ".",
    project_name: str = "Repo",
    modo: str = "respect",
    quiet: bool = False,
) -> list[str]:
    """Detecta el ecosistema y genera las reglas agénticas adaptadas.

    Función reutilizable invocable desde el CLI (``ctxmap adapt``) o desde
    otros comandos (``init``, ``build``) para auto-adaptar el proyecto.

    Args:
        target (str): Ruta del proyecto a analizar.
        project_name (str): Nombre del proyecto.
        modo (str): 'respect' | 'merge' | 'overwrite'.
        quiet (bool): Si True, no imprime el reporte de detección.

    Returns:
        list[str]: Rutas de los archivos generados/actualizados.
    """
    eco = detectar_ecosistema(target)

    if not quiet:
        print()
        print(eco.resumen_texto())
        print()

    generados = adaptar_ecosistema(
        project_name=project_name,
        eco=eco,
        target_dir=target,
        modo=modo,
    )

    if generados and not quiet:
        print("✅ Reglas agénticas generadas/actualizadas:")
        for ruta in generados:
            print(f"   + {ruta}")
        print()
        print("💡 Reglas existentes que no se sobreescribieron (usa --overwrite para forzar):")
        print("   (ver 'Reglas existentes' en el reporte de arriba)")
    elif not generados and not quiet:
        print("⚠️ No se generaron reglas nuevas (todas ya existían).")

    return generados


def _reportar_revision(revision: dict[str, list[str]], quiet: bool) -> None:
    """Imprime el resultado de la revisión idempotente (salvo en modo quiet)."""
    if quiet:
        return
    creadas = len(revision["creados"])
    actualizadas = len(revision["actualizados"])
    if creadas or actualizadas:
        print(f"🔁 Reglas puestas al día: {creadas} nueva(s), {actualizadas} actualizada(s)")
    else:
        print("✅ Reglas agénticas ya al día (sin cambios).")


def cmd_adapt(args) -> None:
    """Detecta el ecosistema y genera/actualiza las reglas agénticas adaptadas.

    Con ``--revisar`` solo ejecuta la revisión idempotente de las reglas propias
    de ContextMap (sin tocar AGENTS.md ni `.hermes/`), ideal para hooks/arranque.

    Args:
        args: Namespace con ``target``, ``--project``, ``--overwrite``, ``--merge``,
            ``--revisar`` y ``--quiet``.
    """
    target = getattr(args, "target", None) or "."
    proj = project_name(args)
    quiet = bool(getattr(args, "quiet", False))

    from context_map.domain.ecosystem.adaptador import revisar_reglas_agente

    if getattr(args, "revisar", False):
        _reportar_revision(revisar_reglas_agente(proj, target_dir=target), quiet)
        return

    if not quiet:
        print(f"🔍 Analizando ecosistema de '{target}'...")
    if getattr(args, "overwrite", False):
        modo = "overwrite"
    elif getattr(args, "merge", False):
        modo = "merge"
    else:
        modo = "respect"

    do_adapt(target=target, project_name=proj, modo=modo, quiet=quiet)
    # Revisión idempotente: pone al día SOLO lo nuestro (si ya está, no reescribe).
    _reportar_revision(revisar_reglas_agente(proj, target_dir=target), quiet)

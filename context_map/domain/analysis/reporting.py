"""Formateadores de reportes de readiness en formato Markdown y JSON."""

from __future__ import annotations

import os

from context_map.domain.analysis.models import ResultadoReadiness


def formatear_readiness(resultado: ResultadoReadiness, salud_vault_fn=None) -> str:
    """Formatea el resultado del análisis de readiness como Markdown legible.

    Args:
        resultado (ResultadoReadiness): Resultado del análisis.
        salud_vault_fn: Función auxiliar para consultar salud del vault (opcional).

    Returns:
        str: Reporte formateado en Markdown.
    """
    lineas = [
        "# Readiness Report",
        "",
        f"**Proyecto**: {os.path.basename(resultado.ruta_raiz)}",
        f"**Score**: {resultado.score}/100",
        f"**Veredicto**: {resultado.veredicto}",
        "",
        "## Señales",
        "",
    ]

    for s in resultado.senales:
        icono = "[OK]" if s.presente else "[X]"
        lineas.append(f"- {icono} {s.nombre} (peso: {s.peso})")
        if s.detalle and not s.presente:
            lineas.append(f"  - _{s.detalle}_")

    # Salud del vault si está disponible la función
    if salud_vault_fn:
        salud = salud_vault_fn(resultado.ruta_raiz)
        lineas.extend(["", "## Salud del Vault (ContextMap)", ""])
        lineas.append(f"- 📝 Notas manuales: **{salud['notas_manuales']}**")
        lineas.append(f"- 🗂️ Vaults activos: **{salud['vaults']}**")
        if salud["ultimo_build_clean"]:
            lineas.append(
                f"- ⚠️ Último build usó **--clean** (destructivo): se preservaron "
                f"**{salud['manuales_preservadas']}** notas manuales. "
                "Prefiere `ctxmap refresh` para builds no destructivos."
            )
        else:
            lineas.append("- ✅ Último build fue no destructivo (sin --clean).")
        if salud["notas_manuales"] == 0:
            lineas.append(
                "- 💡 Consejo: crea tus notas de sesión/decisiones en "
                "`.context-map/vault-*/.manual/` — el build JAMÁS las borra."
            )

    # Frescura del contexto
    if resultado.frescura.get("aviso"):
        lineas.extend(["", "## Frescura del Contexto", ""])
        lineas.append(f"- {resultado.frescura['aviso']}")
        if resultado.frescura.get("commits_posteriores"):
            lineas.append(
                "- 🔄 Corre `ctxmap refresh .` para importar los commits "
                "y sesiones recientes (memoria viva automática)."
            )

    # Métrica de memoria viva
    if resultado.cobertura_memoria:
        cm = resultado.cobertura_memoria
        lineas.extend(["", "## Memoria Viva", ""])
        lineas.append(
            f"- 📊 Cobertura estimada: **{cm['porcentaje']}%** "
            f"({cm['eventos']} eventos registrados / {cm['sesiones']} sesiones sin importar)"
        )
        if cm["sesiones"] and cm["porcentaje"] < 50:
            lineas.append(
                "- 💡 Hay sesiones recientes sin importar — el contexto pierde "
                "memoria viva. Corre `ctxmap refresh .` (o el pre-commit ya lo hará)."
            )

    # Consistencia del nombre
    if resultado.nombre_fragmentado:
        lineas.extend(["", "## Nombre del Proyecto", ""])
        lineas.append(f"- {resultado.nombre_fragmentado}")

    if resultado.gaps:
        lineas.extend(["", "## Faltante", ""])
        for gap in resultado.gaps:
            lineas.append(f"- {gap}")

    if resultado.sugerencias:
        lineas.extend(["", "## Sugerencias", ""])
        for sug in resultado.sugerencias:
            lineas.append(f"- {sug}")

    return "\n".join(lineas)

"""Analizador de readiness para Context Map.


Evalúa qué tan preparado está un proyecto para que un agente de IA trabaje en él,
analizando indicadores de documentación, tests, configuración y CI/CD.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from context_map.presentation.vault.preservar import ZONAS_MANUALES


@dataclass
class SenalReadiness:
    """Una señal o indicador individual de readiness del proyecto.

    Attributes:
        nombre (str): Nombre de la señal.
        peso (int): Peso de la señal en la evaluación (1-10).
        presente (bool): Indica si la señal está presente en el repositorio.
        detalle (str): Descripción detallada del indicador.
    """

    nombre: str
    peso: int
    presente: bool
    detalle: str = ""


@dataclass
class ResultadoReadiness:
    """Resultado del análisis completo de readiness del proyecto.

    Attributes:
        ruta_raiz (str): Ruta raíz del proyecto analizado.
        senales (List[SenalReadiness]): Lista de señales evaluadas.
        score (int): Puntaje global calculado (0-100).
        veredicto (str): Veredicto final ('ready', 'partial', 'not-ready').
        gaps (List[str]): Lista de elementos o señales faltantes.
        sugerencias (List[str]): Lista de recomendaciones de mejora.
    """

    ruta_raiz: str
    senales: list[SenalReadiness] = field(default_factory=list)
    score: int = 0
    veredicto: str = "unknown"
    gaps: list[str] = field(default_factory=list)
    sugerencias: list[str] = field(default_factory=list)


def _verificar_archivo(ruta: str, nombres: list[str]) -> bool:
    """Verifica si existe al menos uno de los archivos indicados en la ruta raíz.

    Args:
        ruta (str): Ruta del directorio base.
        nombres (List[str]): Lista de nombres de archivos a buscar.

    Returns:
        bool: True si existe al menos un archivo, False de lo contrario.
    """
    return any(os.path.exists(os.path.join(ruta, nombre)) for nombre in nombres)


def _verificar_directorio(ruta: str, nombres: list[str]) -> bool:
    """Verifica si existe al menos uno de los directorios indicados.

    Args:
        ruta (str): Ruta del directorio base.
        nombres (List[str]): Lista de nombres de carpetas a buscar.

    Returns:
        bool: True si existe alguna carpeta, False de lo contrario.
    """
    return any(os.path.isdir(os.path.join(ruta, nombre)) for nombre in nombres)


def analizar_readiness(ruta_raiz: str) -> ResultadoReadiness:
    """Ejecuta la auditoría de readiness del proyecto en la ruta especificada.

    Args:
        ruta_raiz (str): Ruta al directorio raíz del proyecto.

    Returns:
        ResultadoReadiness: Objeto con el puntaje, señales y recomendaciones.
    """
    resultado = ResultadoReadiness(ruta_raiz=ruta_raiz)

    senales = [
        SenalReadiness(
            nombre="README",
            peso=10,
            presente=_verificar_archivo(ruta_raiz, ["README.md", "README.rst", "README.txt"]),
            detalle="Archivo de documentación principal",
        ),
        SenalReadiness(
            nombre="CHANGELOG",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["CHANGELOG.md", "CHANGES.md", "HISTORY.md"]),
            detalle="Historial de cambios",
        ),
        SenalReadiness(
            nombre="LICENSE",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["LICENSE", "LICENSE.md", "LICENSE.txt"]),
            detalle="Licencia del proyecto",
        ),
        SenalReadiness(
            nombre="pyproject.toml/setup.py",
            peso=8,
            presente=_verificar_archivo(ruta_raiz, ["pyproject.toml", "setup.py", "setup.cfg"]),
            detalle="Configuración de paquete Python",
        ),
        SenalReadiness(
            nombre="requirements.txt/pyproject",
            peso=6,
            presente=_verificar_archivo(ruta_raiz, ["requirements.txt", "requirements-dev.txt", "pyproject.toml", "uv.lock"]),
            detalle="Dependencias del proyecto",
        ),
        SenalReadiness(
            nombre=".gitignore",
            peso=4,
            presente=_verificar_archivo(ruta_raiz, [".gitignore"]),
            detalle="Archivos ignorados por git",
        ),
        SenalReadiness(
            nombre="Tests",
            peso=9,
            presente=_verificar_directorio(ruta_raiz, ["tests", "test", "__tests__", "context_map/__tests__"]) or _verificar_archivo(ruta_raiz, ["pytest.ini"]),
            detalle="Directorio de pruebas",
        ),
        SenalReadiness(
            nombre="pytest.ini/conftest",
            peso=5,
            presente=_verificar_archivo(ruta_raiz, ["pytest.ini", "conftest.py", "tox.ini", "pyproject.toml"]),
            detalle="Configuración de testing",
        ),
        SenalReadiness(
            nombre="CI/CD",
            peso=7,
            presente=_verificar_directorio(ruta_raiz, [".github", ".gitlab-ci.yml", ".circleci"]),
            detalle="Integración continua",
        ),
        SenalReadiness(
            nombre="AGENTS.md/CLAUDE.md",
            peso=6,
            presente=_verificar_archivo(ruta_raiz, ["AGENTS.md", "CLAUDE.md", "CURSOR.md"]),
            detalle="Instrucciones para agentes de IA",
        ),
        SenalReadiness(
            nombre="Makefile/Justfile",
            peso=4,
            presente=_verificar_archivo(ruta_raiz, ["Makefile", "Justfile", "pyproject.toml"]),
            detalle="Comandos comunes del proyecto",
        ),
    ]

    resultado.senales = senales

    peso_total = sum(s.peso for s in senales)
    peso_presente = sum(s.peso for s in senales if s.presente)
    resultado.score = int((peso_presente / peso_total) * 100) if peso_total > 0 else 0

    resultado.gaps = [s.nombre for s in senales if not s.presente]

    if not any(s.nombre == "README" and s.presente for s in senales):
        resultado.sugerencias.append("Crear un README.md con descripción del proyecto")
    if not any(s.nombre == "Tests" and s.presente for s in senales):
        resultado.sugerencias.append("Agregar directorio de tests")
    if not any(s.nombre == "CI/CD" and s.presente for s in senales):
        resultado.sugerencias.append("Configurar CI/CD (GitHub Actions)")
    if not any(s.nombre == "AGENTS.md/CLAUDE.md" and s.presente for s in senales):
        resultado.sugerencias.append("Crear AGENTS.md con instrucciones para agentes")

    if resultado.score >= 80:
        resultado.veredicto = "ready"
    elif resultado.score >= 50:
        resultado.veredicto = "partial"
    else:
        resultado.veredicto = "not-ready"

    return resultado


def _salud_vault(ruta_raiz: str) -> dict[str, object]:
    """Evalúa la salud del vault de ContextMap (notas manuales y último build).

    Cuenta las notas manuales (zona protegida ``.manual/`` + notas con
    frontmatter ``preserve: true``) y lee ``state/last_build.json`` para
    saber si el último build usó ``--clean`` (destructivo).

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        dict[str, object]: Resumen de salud del vault.
    """
    import json as _json

    context_dir = os.path.join(ruta_raiz, ".context-map")
    vault_dirs: list[str] = []
    if os.path.isdir(context_dir):
        vault_dirs = [
            os.path.join(context_dir, d)
            for d in os.listdir(context_dir)
            if d.startswith("vault") and os.path.isdir(os.path.join(context_dir, d))
        ]

    n_manuales = 0
    for vdir in vault_dirs:
        # Zonas manuales visibles/ocultas (7.0-MANUAL y .manual)
        zonas_set = set(ZONAS_MANUALES)
        for zona in ZONAS_MANUALES:
            zona_dir = os.path.join(vdir, zona)
            if os.path.isdir(zona_dir):
                for _raiz, _dirs, archivos in os.walk(zona_dir):
                    n_manuales += sum(1 for a in archivos if a.endswith(".md"))
        # preserve:true en cualquier parte del vault (excepto zonas manuales)
        for raiz, _dirs, archivos in os.walk(vdir):
            if zonas_set & set(raiz.split(os.sep)):
                continue
            for fname in archivos:
                if not fname.endswith(".md"):
                    continue
                try:
                    with open(os.path.join(raiz, fname), encoding="utf-8") as f:
                        primeras = [next(f, "") for _ in range(10)]
                    if primeras and primeras[0].strip() == "---":
                        for linea in primeras[1:]:
                            if linea.strip().startswith("---"):
                                break
                            clave = linea.strip().lower().replace(" ", "")
                            if clave.startswith("preserve:") and "true" in clave:
                                n_manuales += 1
                                break
                except Exception:
                    continue

    info_build: dict[str, object] = {}
    last_build = os.path.join(context_dir, "state", "last_build.json")
    if os.path.isfile(last_build):
        try:
            with open(last_build, encoding="utf-8") as f:
                info_build = _json.load(f)
        except Exception:
            info_build = {}

    return {
        "vaults": len(vault_dirs),
        "notas_manuales": n_manuales,
        "ultimo_build_clean": bool(info_build.get("clean", False)),
        "manuales_preservadas": int(info_build.get("manuales_preservadas", 0)),
    }


def formatear_readiness(resultado: ResultadoReadiness) -> str:
    """Formatea el resultado del análisis de readiness como Markdown legible.

    Args:
        resultado (ResultadoReadiness): Resultado del análisis.

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

    # Salud del vault (notas manuales + último build)
    salud = _salud_vault(resultado.ruta_raiz)
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

    if resultado.gaps:
        lineas.extend(["", "## Faltante", ""])
        for gap in resultado.gaps:
            lineas.append(f"- {gap}")

    if resultado.sugerencias:
        lineas.extend(["", "## Sugerencias", ""])
        for sug in resultado.sugerencias:
            lineas.append(f"- {sug}")

    return "\n".join(lineas)

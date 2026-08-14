"""Analizador de readiness para Context Map.


Evalúa qué tan preparado está un proyecto para que un agente de IA trabaje en él,
analizando indicadores de documentación, tests, configuración y CI/CD.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime

from context_map.infrastructure.integrations.hermes import leer_sesiones
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
    frescura: dict[str, object] = field(default_factory=dict)


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

    # Frescura del contexto (R1, auditoría 2026-08-14): si hay commits o
    # sesiones de Hermes posteriores al último build, la memoria viva está
    # atrasada y el siguiente agente quedaría ciego. El aviso es accionable.
    actividad = _ultima_actividad(ruta_raiz)
    resultado.frescura = actividad
    if actividad["aviso"]:
        resultado.sugerencias.append(str(actividad["aviso"]))

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


def _ejecutar_git(ruta: str, args: list[str]) -> str:
    """Ejecuta un comando git en la ruta y devuelve la salida (o vacío).

    Args:
        ruta (str): Directorio del repo.
        args (list[str]): Argumentos del comando git.

    Returns:
        str: Salida estándar del comando, o cadena vacía si falla.
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=ruta,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def _timestamp_build(ruta_raiz: str) -> float | None:
    """Lee el timestamp del último build desde ``state/last_build.json``.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        float | None: Epoch del último build, o None si no existe.
    """
    import json as _json

    last_build = os.path.join(ruta_raiz, ".context-map", "state", "last_build.json")
    if not os.path.isfile(last_build):
        return None
    try:
        with open(last_build, encoding="utf-8") as f:
            info = _json.load(f)
        ts = info.get("timestamp")
        if not ts:
            return None
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return None


def _ultima_actividad(ruta_raiz: str) -> dict[str, object]:
    """Detecta actividad posterior al último build (commits y sesiones).

    Compara el timestamp de ``last_build.json`` contra el último commit de git
    y las sesiones recientes de Hermes del proyecto. Si el build nunca existió,
    avisa con un mensaje de bootstrap.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        dict[str, object]: Con ``commits_posteriores`` (int) y ``aviso`` (str).
    """
    ts_build = _timestamp_build(ruta_raiz)
    if ts_build is None:
        return {
            "commits_posteriores": 0,
            "aviso": "⚠️ Nunca se ha hecho build del contexto: ejecuta `ctxmap refresh .` para inicializarlo.",
        }

    # Último commit: `git log -1 --format=%ct` devuelve epoch del commit.
    salida = _ejecutar_git(ruta_raiz, ["log", "-1", "--format=%ct"])
    commits_posteriores = 0
    if salida.isdigit():
        commits_posteriores = 1 if int(salida) > ts_build else 0

    n_sesiones = _sesiones_posteriores(ruta_raiz)

    aviso = ""
    partes = []
    if commits_posteriores:
        partes.append(f"{commits_posteriores} commit(s) posterior(es) al último build")
    if n_sesiones:
        partes.append(f"{n_sesiones} sesión(es) de Hermes sin importar")
    if partes:
        aviso = (
            "⚠️ Contexto desactualizado: " + " y ".join(partes)
            + ". Ejecuta `ctxmap refresh .` para registrar la memoria viva."
        )
    return {"commits_posteriores": commits_posteriores, "aviso": aviso}


def _sesiones_posteriores(ruta_raiz: str) -> int:
    """Cuenta sesiones de Hermes iniciadas después del último build.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        int: Número de sesiones recientes sin importar (0 si no se puede saber).
    """
    ts_build = _timestamp_build(ruta_raiz)
    if ts_build is None:
        return 0
    try:
        sesiones = leer_sesiones(db_path=None, limite=50)
    except Exception:
        return 0

    n = 0
    for s in sesiones:
        inicio = getattr(s, "fecha_inicio", "") or ""
        try:
            ts = float(inicio)
        except ValueError:
            try:
                ts = datetime.fromisoformat(inicio).timestamp()
            except ValueError:
                continue
        if ts > ts_build:
            n += 1
    return n


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

    # Frescura del contexto (R1, auditoría 2026-08-14)
    if resultado.frescura.get("aviso"):
        lineas.extend(["", "## Frescura del Contexto", ""])
        lineas.append(f"- {resultado.frescura['aviso']}")
        if resultado.frescura.get("commits_posteriores"):
            lineas.append(
                "- 🔄 Corre `ctxmap refresh .` para importar los commits "
                "y sesiones recientes (memoria viva automática)."
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

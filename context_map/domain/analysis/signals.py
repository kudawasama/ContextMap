"""Evaluador de señales e indicadores de readiness de proyecto."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime

from context_map.domain.analysis.models import ResultadoReadiness, SenalReadiness
from context_map.infrastructure.integrations.hermes import leer_sesiones
from context_map.presentation.vault.preservar import ZONAS_MANUALES


def verificar_archivo(ruta: str, nombres: list[str]) -> bool:
    """Verifica si existe al menos uno de los archivos indicados en la ruta raíz."""
    return any(os.path.exists(os.path.join(ruta, nombre)) for nombre in nombres)


def verificar_directorio(ruta: str, nombres: list[str]) -> bool:
    """Verifica si existe al menos uno de los directorios indicados."""
    return any(os.path.isdir(os.path.join(ruta, nombre)) for nombre in nombres)


def analizar_readiness(ruta_raiz: str) -> ResultadoReadiness:
    """Ejecuta la auditoría de readiness del proyecto en la ruta especificada."""
    resultado = ResultadoReadiness(ruta_raiz=ruta_raiz)

    senales = [
        SenalReadiness(
            nombre="README",
            peso=10,
            presente=verificar_archivo(ruta_raiz, ["README.md", "README.rst", "README.txt", "README"]),
            detalle="Documento principal de descripción e instrucciones del proyecto.",
        ),
        SenalReadiness(
            nombre="CHANGELOG",
            peso=5,
            presente=verificar_archivo(
                ruta_raiz, ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG.txt", "CHANGELOG", "HISTORY.md"]
            ),
            detalle="Historial de versiones y cambios del proyecto.",
        ),
        SenalReadiness(
            nombre="LICENSE",
            peso=5,
            presente=verificar_archivo(
                ruta_raiz, ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "COPYING"]
            ),
            detalle="Licencia de uso del proyecto.",
        ),
        SenalReadiness(
            nombre="pyproject.toml/setup.py",
            peso=8,
            presente=verificar_archivo(
                ruta_raiz, ["pyproject.toml", "setup.py", "setup.cfg", "package.json", "Cargo.toml", "go.mod"]
            ),
            detalle="Archivo de configuración de empaquetado o proyecto.",
        ),
        SenalReadiness(
            nombre="requirements.txt/pyproject",
            peso=6,
            presente=verificar_archivo(
                ruta_raiz,
                [
                    "requirements.txt",
                    "pyproject.toml",
                    "Pipfile",
                    "poetry.lock",
                    "package-lock.json",
                    "yarn.lock",
                    "pnpm-lock.yaml",
                    "Cargo.lock",
                    "go.sum",
                ],
            ),
            detalle="Archivo de especificación de dependencias.",
        ),
        SenalReadiness(
            nombre=".gitignore",
            peso=4,
            presente=verificar_archivo(ruta_raiz, [".gitignore", ".hgignore"]),
            detalle="Configuración de archivos a ignorar en el control de versiones.",
        ),
        SenalReadiness(
            nombre="Tests",
            peso=9,
            presente=verificar_directorio(
                ruta_raiz, ["tests", "test", "__tests__", "spec", "specs", "context_map/__tests__", "context_map/tests"]
            )
            or verificar_archivo(ruta_raiz, ["test.py", "tests.py"]),
            detalle="Directorio o archivo con pruebas automatizadas.",
        ),
        SenalReadiness(
            nombre="pytest.ini/conftest",
            peso=5,
            presente=verificar_archivo(
                ruta_raiz,
                [
                    "pytest.ini",
                    "conftest.py",
                    ".pytest_cache",
                    "tox.ini",
                    ".coveragerc",
                    "jest.config.js",
                    "tsconfig.json",
                ],
            ),
            detalle="Configuración del framework de pruebas.",
        ),
        SenalReadiness(
            nombre="CI/CD",
            peso=7,
            presente=verificar_directorio(ruta_raiz, [".github", ".gitlab", ".circleci", ".travis"])
            or verificar_archivo(ruta_raiz, [".gitlab-ci.yml", "Jenkinsfile", ".travis.yml", "azure-pipelines.yml"]),
            detalle="Configuración de integración y despliegue continuo.",
        ),
        SenalReadiness(
            nombre="AGENTS.md/CLAUDE.md",
            peso=6,
            presente=verificar_archivo(
                ruta_raiz,
                [
                    "AGENTS.md",
                    "CLAUDE.md",
                    "GEMINI.md",
                    ".cursorrules",
                    ".windsurfrules",
                    ".clinerules",
                    "opencode.json",
                ],
            )
            or verificar_directorio(ruta_raiz, [".cursor/rules", ".roo/rules"]),
            detalle="Reglas de gobernanza agéntica para IAs.",
        ),
        SenalReadiness(
            nombre="Makefile/Justfile",
            peso=4,
            presente=verificar_archivo(
                ruta_raiz, ["Makefile", "makefile", "Justfile", "justfile", "Taskfile.yml", "Rakefile"]
            ),
            detalle="Archivo de automatización de tareas comunes.",
        ),
    ]

    resultado.senales = senales

    peso_total = sum(s.peso for s in senales)
    peso_obtenido = sum(s.peso for s in senales if s.presente)

    resultado.score = int(round((peso_obtenido / peso_total) * 100)) if peso_total > 0 else 0

    if resultado.score >= 80:
        resultado.veredicto = "ready"
    elif resultado.score >= 50:
        resultado.veredicto = "partial"
    else:
        resultado.veredicto = "not-ready"

    resultado.gaps = [s.nombre for s in senales if not s.presente]

    resultado.sugerencias = []
    if not verificar_archivo(ruta_raiz, ["README.md", "README.rst", "README.txt", "README"]):
        resultado.sugerencias.append("Crear un README.md con la descripción y uso del proyecto.")
    if not (
        verificar_directorio(ruta_raiz, ["tests", "test", "__tests__", "spec", "specs"])
        or verificar_archivo(ruta_raiz, ["test.py", "tests.py"])
    ):
        resultado.sugerencias.append("Agregar una carpeta de pruebas (tests/) para validar el código.")
    if not (
        verificar_directorio(ruta_raiz, [".github", ".gitlab", ".circleci", ".travis"])
        or verificar_archivo(ruta_raiz, [".gitlab-ci.yml", "Jenkinsfile", ".travis.yml", "azure-pipelines.yml"])
    ):
        resultado.sugerencias.append("Configurar un pipeline de CI/CD (ej. .github/workflows/).")
    if not verificar_archivo(ruta_raiz, ["AGENTS.md", "CLAUDE.md"]):
        resultado.sugerencias.append("Generar AGENTS.md (`ctxmap adapt .`) para definir reglas del proyecto.")

    import context_map.domain.analysis.checker as chk

    resultado.frescura = chk._ultima_actividad(ruta_raiz)
    resultado.cobertura_memoria = chk._cobertura_memoria_viva(ruta_raiz)
    resultado.nombre_fragmentado = chk._inconsistencia_nombre(ruta_raiz, "Repo")

    if resultado.frescura.get("aviso"):
        resultado.sugerencias.append(str(resultado.frescura["aviso"]))

    return resultado


def salud_vault(ruta_raiz: str) -> dict[str, object]:
    """Inspecciona el vault de `.context-map/` para auditar su salud y notas manuales."""
    context_dir = os.path.join(ruta_raiz, ".context-map")
    if not os.path.isdir(context_dir):
        return {
            "vaults": 0,
            "notas_manuales": 0,
            "ultimo_build_clean": False,
            "manuales_preservadas": 0,
        }

    vault_dirs = [
        d for d in os.listdir(context_dir) if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
    ]

    n_manuales = 0
    for vname in vault_dirs:
        vpath = os.path.join(context_dir, vname)
        for raiz, _, archivos in os.walk(vpath):
            es_zona_manual = any(z in raiz.replace("\\", "/") for z in ZONAS_MANUALES)
            for fname in archivos:
                if not fname.endswith(".md"):
                    continue
                if es_zona_manual:
                    n_manuales += 1
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
                info_build = json.load(f)
        except Exception:
            info_build = {}

    return {
        "vaults": len(vault_dirs),
        "notas_manuales": n_manuales,
        "ultimo_build_clean": bool(info_build.get("clean", False)),
        "manuales_preservadas": int(info_build.get("manuales_preservadas", 0)),
    }


def ejecutar_git(ruta: str, args: list[str]) -> str:
    """Ejecuta un comando git en la ruta y devuelve la salida (o vacío)."""
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


def timestamp_build(ruta_raiz: str) -> float | None:
    """Lee el timestamp del último build desde state/last_build.json."""
    last_build = os.path.join(ruta_raiz, ".context-map", "state", "last_build.json")
    if not os.path.isfile(last_build):
        return None
    try:
        with open(last_build, encoding="utf-8") as f:
            info = json.load(f)
        ts = info.get("timestamp")
        if not ts:
            return None
        return datetime.fromisoformat(ts).timestamp()
    except Exception:
        return None


def ultima_actividad(ruta_raiz: str) -> dict[str, object]:
    """Detecta actividad posterior al último build (commits y sesiones)."""
    import context_map.domain.analysis.checker as chk
    ts_b = chk._timestamp_build(ruta_raiz)
    if ts_b is None:
        return {
            "commits_posteriores": 0,
            "aviso": "⚠️ Nunca se ha hecho build del contexto: ejecuta `ctxmap refresh .` para inicializarlo.",
        }

    salida = chk._ejecutar_git(ruta_raiz, ["log", "-1", "--format=%ct"])
    commits_posteriores = 0
    if salida.isdigit():
        commits_posteriores = 1 if int(salida) > ts_b else 0

    n_sesiones = chk._sesiones_posteriores(ruta_raiz)

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


def sesiones_posteriores(ruta_raiz: str) -> int:
    """Cuenta sesiones de Hermes iniciadas después del último build."""
    ts_b = timestamp_build(ruta_raiz)
    if ts_b is None:
        return 0
    try:
        import context_map.domain.analysis.checker as chk
        sesiones = chk.leer_sesiones(db_path=None, limite=50)
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
        if ts > ts_b:
            n += 1
    return n


def contar_eventos_events_jsonl(ruta_raiz: str) -> int:
    """Cuenta los eventos importados en .context-map/raw/events.jsonl."""
    ruta = os.path.join(ruta_raiz, ".context-map", "raw", "events.jsonl")
    if not os.path.isfile(ruta):
        return 0
    n = 0
    try:
        with open(ruta, encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    n += 1
    except Exception:
        return 0
    return n


def cobertura_memoria_viva(ruta_raiz: str) -> dict[str, int]:
    """Mide la cobertura de memoria viva: eventos vs sesiones sin importar."""
    import context_map.domain.analysis.checker as chk
    eventos = chk._contar_eventos_events_jsonl(ruta_raiz)
    sesiones = chk._sesiones_posteriores(ruta_raiz)
    porcentaje = 0
    if eventos or sesiones:
        total = eventos + sesiones
        porcentaje = int(round(eventos / total * 100)) if total else 0
    return {"eventos": eventos, "sesiones": sesiones, "porcentaje": porcentaje}


def inconsistencia_nombre(ruta_raiz: str, proyecto_actual: str) -> str:
    """Detecta si el nombre del proyecto está fragmentado."""
    context_dir = os.path.join(ruta_raiz, ".context-map")
    if not os.path.isdir(context_dir):
        return ""

    vaults = [
        d[len("vault-"):]
        for d in os.listdir(context_dir)
        if d.startswith("vault-") and os.path.isdir(os.path.join(context_dir, d))
    ]
    nombre_vault = vaults[0] if len(vaults) == 1 else ""

    nombre_project = ""
    context_md = os.path.join(context_dir, "CONTEXT.md")
    if os.path.isfile(context_md):
        try:
            with open(context_md, encoding="utf-8") as f:
                for linea in f:
                    linea = linea.strip()
                    if linea.startswith("project:"):
                        nombre_project = (
                            linea.split(":", 1)[1].strip().strip('"').strip("'")
                        )
                        break
        except Exception:
            pass

    nombre_repo = os.path.basename(os.path.abspath(ruta_raiz))

    def _norm(v: str) -> str:
        return v.strip().replace(" ", "-").lower()

    etiquetas = {"vault": nombre_vault, "project": nombre_project, "repo": nombre_repo}
    unicas = {_norm(v) for v in etiquetas.values() if v}

    if len(unicas) <= 1:
        return ""

    detalle = " · ".join(f"{k}='{v}'" for k, v in etiquetas.items() if v)
    return (
        f"⚠️ Nombre del proyecto fragmentado ({detalle}): el vault, el CONTEXT.md "
        "y la carpeta del repo no coinciden — la BD personal puede duplicar "
        "eventos. Unifica a un solo nombre (idealmente el del repo)."
    )

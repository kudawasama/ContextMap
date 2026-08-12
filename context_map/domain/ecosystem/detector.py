"""Detección del ecosistema de un proyecto: stack técnico e IDE/agentes.

ContextMap analiza el proyecto donde se instala para adaptar las reglas
de gobernanza al entorno real: lenguaje, framework, runner de tests,
entrypoints y las herramientas agénticas presentes (VS Code, Cursor,
Windsurf, JetBrains, Claude Code, Copilot, Hermes, Antigravity).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ============================================================
# Modelos de datos
# ============================================================


@dataclass
class StackInfo:
    """Información del stack técnico detectado en el proyecto.

    Attributes:
        lenguajes (list[str]): Lenguajes detectados ('Python', 'JavaScript', ...).
        frameworks (list[str]): Frameworks detectados ('FastAPI', 'React', ...).
        test_runner (str): Comando de tests detectado ('pytest', 'jest', ...).
        package_manager (str): Gestor de paquetes ('pip', 'uv', 'npm', ...).
        entrypoints (list[str]): Puntos de entrada detectados.
        estructura (list[str]): Directorios de estructura clave.
    """

    lenguajes: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    test_runner: str = ""
    package_manager: str = ""
    entrypoints: list[str] = field(default_factory=list)
    estructura: list[str] = field(default_factory=list)


@dataclass
class IDEInfo:
    """Herramientas agénticas detectadas en el proyecto.

    Attributes:
        ides (list[str]): IDEs detectados ('VS Code', 'Cursor', 'Windsurf', 'JetBrains').
        agentes (list[str]): Agentes de código detectados ('Claude Code', 'Copilot', ...).
        reglas_existentes (list[str]): Archivos de reglas ya presentes.
        ides_por_proceso (list[str]): IDEs detectados por proceso activo del sistema
            (no por marcadores del proyecto). Permite saber que el IDE está corriendo
            aunque el proyecto no tenga su carpeta de configuración.
    """

    ides: list[str] = field(default_factory=list)
    agentes: list[str] = field(default_factory=list)
    reglas_existentes: list[str] = field(default_factory=list)
    ides_por_proceso: list[str] = field(default_factory=list)


@dataclass
class EcosistemaInfo:
    """Resumen completo del ecosistema detectado.

    Attributes:
        stack (StackInfo): Información del stack técnico.
        ide (IDEInfo): Información de IDEs y agentes.
    """

    stack: StackInfo = field(default_factory=StackInfo)
    ide: IDEInfo = field(default_factory=IDEInfo)

    def resumen_texto(self) -> str:
        """Devuelve un resumen legible del ecosistema detectado."""
        ides_linea = f"- IDEs: {', '.join(self.ide.ides) or 'no detectado'}"
        if self.ide.ides_por_proceso:
            ides_linea += (
                f"\n- IDEs por proceso activo: {', '.join(self.ide.ides_por_proceso)}"
                " (corriendo ahora, aunque el proyecto no tenga su carpeta)"
            )
        lineas = [
            "## 🧰 Stack detectado",
            f"- Lenguajes: {', '.join(self.stack.lenguajes) or 'no detectado'}",
            f"- Frameworks: {', '.join(self.stack.frameworks) or 'no detectado'}",
            f"- Test runner: {self.stack.test_runner or 'no detectado'}",
            f"- Package manager: {self.stack.package_manager or 'no detectado'}",
            f"- Entrypoints: {', '.join(self.stack.entrypoints) or 'no detectado'}",
            "",
            "## 🛠️ IDE / Agentes detectados",
            ides_linea,
            f"- Agentes: {', '.join(self.ide.agentes) or 'no detectado'}",
            f"- Reglas existentes: {', '.join(self.ide.reglas_existentes) or 'ninguna'}",
        ]
        return "\n".join(lineas)


# ============================================================
# Detección de stack
# ============================================================


def _existe(target_dir: str, nombre: str) -> bool:
    return os.path.isfile(os.path.join(target_dir, nombre))


def detectar_stack(target_dir: str = ".") -> StackInfo:
    """Detecta el stack técnico del proyecto.

    Examina los archivos de manifest (pyproject.toml, package.json,
    Cargo.toml, go.mod) y los directorios clave para inferir lenguaje,
    framework, runner de tests y entrypoints.

    Args:
        target_dir (str): Directorio raíz del proyecto a analizar.

    Returns:
        StackInfo: Información del stack detectado.
    """
    info = StackInfo()

    # --- Python ---
    if _existe(target_dir, "pyproject.toml") or _existe(target_dir, "requirements.txt") or _existe(target_dir, "setup.py"):
        info.lenguajes.append("Python")
        if _existe(target_dir, "uv.lock"):
            info.package_manager = "uv"
        elif _existe(target_dir, "poetry.lock"):
            info.package_manager = "poetry"
        elif _existe(target_dir, "Pipfile"):
            info.package_manager = "pipenv"
        else:
            info.package_manager = "pip"

        # Leer pyproject.toml para detectar framework/test runner
        pyproject = os.path.join(target_dir, "pyproject.toml")
        if os.path.isfile(pyproject):
            try:
                with open(pyproject, encoding="utf-8") as f:
                    contenido = f.read().lower()
                for fw in ["fastapi", "django", "flask", "streamlit", "pydantic"]:
                    if fw in contenido:
                        info.frameworks.append(fw.capitalize())
                if "pytest" in contenido or _existe(target_dir, "pytest.ini") or _existe(target_dir, "tox.ini"):
                    info.test_runner = "pytest"
            except Exception as err:
                logger.debug("No se pudo leer pyproject.toml: %s", err)

        if not info.frameworks:
            # Detección por carpetas de framework
            for carpeta, fw in [("src/app", "FastAPI"), ("app", "FastAPI/Django"), ("django", "Django")]:
                if os.path.isdir(os.path.join(target_dir, carpeta)):
                    if fw not in info.frameworks:
                        info.frameworks.append(fw)
                    break

        if not info.test_runner and (
            _existe(target_dir, "conftest.py") or os.path.isdir(os.path.join(target_dir, "tests"))
        ):
            info.test_runner = "pytest"

    # --- JavaScript/TypeScript ---
    if _existe(target_dir, "package.json"):
        info.lenguajes.append("JavaScript/TypeScript")
        if not info.package_manager:
            info.package_manager = "npm"
        try:
            with open(os.path.join(target_dir, "package.json"), encoding="utf-8") as f:
                contenido = f.read().lower()
            for fw in ["react", "vue", "angular", "next", "svelte", "express"]:
                if fw in contenido and fw not in info.frameworks:
                    info.frameworks.append(fw.capitalize())
            for runner in ["jest", "vitest", "mocha", "cypress", "playwright"]:
                if runner in contenido:
                    info.test_runner = runner
                    break
        except Exception as err:
            logger.debug("No se pudo leer package.json: %s", err)

    # --- Rust ---
    if _existe(target_dir, "Cargo.toml"):
        info.lenguajes.append("Rust")
        if not info.package_manager:
            info.package_manager = "cargo"
        if not info.test_runner:
            info.test_runner = "cargo test"

    # --- Go ---
    if _existe(target_dir, "go.mod"):
        info.lenguajes.append("Go")
        if not info.package_manager:
            info.package_manager = "go mod"
        if not info.test_runner:
            info.test_runner = "go test"

    # --- Entrypoints ---
    for ep in ["main.py", "app.py", "manage.py", "cli.py", "index.js", "index.ts", "src/main.py", "src/main.rs", "main.go"]:
        if _existe(target_dir, ep):
            info.entrypoints.append(ep)

    # Entrypoints declarados en pyproject.toml ([project.scripts] / [project.gui-scripts])
    if os.path.isfile(os.path.join(target_dir, "pyproject.toml")):
        try:
            with open(os.path.join(target_dir, "pyproject.toml"), encoding="utf-8") as f:
                contenido_py = f.read()
            for bloque in ("[project.scripts]", "[project.gui-scripts]"):
                if bloque in contenido_py:
                    despues = contenido_py.split(bloque, 1)[1].split("\n\n", 1)[0]
                    for linea in despues.splitlines():
                        linea = linea.strip()
                        if linea and "=" in linea and not linea.startswith("#"):
                            comando = linea.split("=", 1)[0].strip()
                            if comando:
                                info.entrypoints.append(comando)
        except Exception as err:
            logger.debug("No se pudieron leer scripts de pyproject.toml: %s", err)

    # Deduplicar entrypoints
    info.entrypoints = list(dict.fromkeys(info.entrypoints))

    # --- Estructura ---
    for carpeta in ["src", "app", "tests", "docs", "scripts"]:
        if os.path.isdir(os.path.join(target_dir, carpeta)):
            info.estructura.append(carpeta)

    return info


# ============================================================
# Detección de IDE / agentes
# ============================================================

# Procesos de IDE conocidos -> nombre de IDE (detección por proceso activo).
# Clave en minúsculas: el nombre real del proceso varía por SO/versión.
PROCESOS_IDE: dict[str, str] = {
    "cursor.exe": "Cursor",
    "cursor": "Cursor",
    "code.exe": "VS Code",
    "code": "VS Code",
    "code - insiders.exe": "VS Code",
    "code-insiders": "VS Code",
    "codium.exe": "VS Code",
    "codium": "VS Code",
    "windsurf.exe": "Windsurf",
    "windsurf": "Windsurf",
    "windsurf-next.exe": "Windsurf",
    "idea64.exe": "JetBrains",
    "idea.exe": "JetBrains",
    "idea": "JetBrains",
    "pycharm64.exe": "JetBrains",
    "pycharm.exe": "JetBrains",
    "pycharm": "JetBrains",
    "webstorm64.exe": "JetBrains",
    "goland64.exe": "JetBrains",
    "rider64.exe": "JetBrains",
    "clion64.exe": "JetBrains",
    "datagrip64.exe": "JetBrains",
    "phpstorm64.exe": "JetBrains",
    "rubymine64.exe": "JetBrains",
    "androidstudio64.exe": "JetBrains",
    "antigravity.exe": "Antigravity",
    "antigravity": "Antigravity",
}


def _listar_procesos() -> list[str]:
    """Lista los nombres de procesos activos del sistema (en minúsculas).

    Windows usa ``tasklist``; Unix/macOS usa ``ps``. Ante cualquier error
    devuelve lista vacía (la detección por proceso es complementaria, nunca
    debe romper el flujo).

    Returns:
        list[str]: Nombres de procesos activos en minúsculas.
    """
    import subprocess

    try:
        if os.name == "nt":
            resultado = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, timeout=10,
            )
            nombres: list[str] = []
            for linea in resultado.stdout.splitlines():
                if linea.startswith('"'):
                    proc = linea.split('"')[1].strip().lower()
                    if proc:
                        nombres.append(proc)
            return nombres
        # Unix / macOS
        resultado = subprocess.run(
            ["ps", "-axo", "comm"],
            capture_output=True, text=True, timeout=10,
        )
        nombres = []
        for linea in resultado.stdout.splitlines():
            proc = os.path.basename(linea.strip()).lower()
            if proc:
                nombres.append(proc)
        return nombres
    except Exception as err:
        logger.debug("No se pudo listar procesos del sistema: %s", err)
        return []


def detectar_ide_proceso() -> list[str]:
    """Detecta IDEs por proceso activo del sistema.

    Complementa la detección por marcadores del proyecto: si el usuario tiene
    Cursor/VS Code/Windsurf/JetBrains/Antigravity corriendo AHORA, se reporta
    aunque el proyecto no tenga su carpeta de configuración (`.cursor/`, etc.).

    Returns:
        list[str]: IDEs detectados por proceso activo, sin duplicados.
    """
    detectados: list[str] = []
    for proc in _listar_procesos():
        ide = PROCESOS_IDE.get(proc)
        if ide and ide not in detectados:
            detectados.append(ide)
    return detectados


def detectar_ide(target_dir: str = ".") -> IDEInfo:
    """Detecta IDEs y herramientas agénticas presentes en el proyecto.

    Examina los directorios de configuración de los IDEs (`.vscode/`,
    `.idea/`, `.cursor/`, `.windsurf/`) y los archivos de reglas agénticas
    (`AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.windsurfrules`,
    `.github/copilot-instructions.md`, `.clinerules`, `.hermes/`).

    Args:
        target_dir (str): Directorio raíz del proyecto a analizar.

    Returns:
        IDEInfo: Información de IDEs y agentes detectados.
    """
    info = IDEInfo()

    # --- Directorios de IDE ---
    if os.path.isdir(os.path.join(target_dir, ".vscode")):
        info.ides.append("VS Code")
    if os.path.isdir(os.path.join(target_dir, ".cursor")):
        info.ides.append("Cursor")
    if os.path.isdir(os.path.join(target_dir, ".windsurf")):
        info.ides.append("Windsurf")
    if os.path.isdir(os.path.join(target_dir, ".idea")):
        info.ides.append("JetBrains")

    # --- Archivos de reglas agénticas ---
    reglas_candidatas = [
        "AGENTS.md", "CLAUDE.md", ".cursorrules", ".windsurfrules",
        ".clinerules", ".github/copilot-instructions.md", "GEMINI.md",
        ".aider.conf.yml", ".aider.conf.yaml", ".roo/rules",
        "opencode.json", ".opencode/",
    ]
    for ruta in reglas_candidatas:
        if os.path.isdir(os.path.join(target_dir, ruta)) or _existe(target_dir, ruta):
            info.reglas_existentes.append(ruta)

    # --- Directorios de agentes / harnesses CLI ---
    if os.path.isdir(os.path.join(target_dir, ".hermes")):
        info.agentes.append("Hermes")
        info.reglas_existentes.append(".hermes/")
    if os.path.isdir(os.path.join(target_dir, ".claude")):
        info.agentes.append("Claude")
    if os.path.isdir(os.path.join(target_dir, ".antigravity")):
        info.agentes.append("Antigravity")
    if os.path.isdir(os.path.join(target_dir, ".opencode")) or _existe(target_dir, "opencode.json"):
        info.agentes.append("OpenCode")
    if os.path.isdir(os.path.join(target_dir, ".codex")):
        info.agentes.append("OpenAI Codex")
    if os.path.isdir(os.path.join(target_dir, ".gemini")) or _existe(target_dir, "GEMINI.md"):
        info.agentes.append("Gemini CLI")
    if os.path.isdir(os.path.join(target_dir, ".aider")) or _existe(target_dir, ".aider.conf.yml") or _existe(target_dir, ".aider.conf.yaml"):
        info.agentes.append("Aider")
    if os.path.isdir(os.path.join(target_dir, ".roo")):
        info.agentes.append("Roo Code")
    # Copilot usa .github/copilot-instructions.md; el dir .github no implica Copilot
    if os.path.isdir(os.path.join(target_dir, ".github")) and _existe(
        target_dir, ".github/copilot-instructions.md"
    ):
        info.agentes.append("GitHub Copilot")

    # Inferir agentes por archivos de reglas
    if "CLAUDE.md" in info.reglas_existentes:
        info.agentes.append("Claude Code")
    if ".cursorrules" in info.reglas_existentes or ".cursor" in info.reglas_existentes:
        info.agentes.append("Cursor")
    if ".windsurfrules" in info.reglas_existentes:
        info.agentes.append("Windsurf")
    if ".clinerules" in info.reglas_existentes:
        info.agentes.append("Cline")
    if ".roo/rules" in info.reglas_existentes:
        info.agentes.append("Roo Code")
    if "GEMINI.md" in info.reglas_existentes:
        info.agentes.append("Gemini CLI")
    if ".aider.conf.yml" in info.reglas_existentes or ".aider.conf.yaml" in info.reglas_existentes:
        info.agentes.append("Aider")
    if "opencode.json" in info.reglas_existentes or ".opencode/" in info.reglas_existentes:
        info.agentes.append("OpenCode")
    if "AGENTS.md" in info.reglas_existentes:
        info.agentes.append("AGENTS.md (estándar universal)")

    # Deduplicar preservando orden
    info.ides = list(dict.fromkeys(info.ides))
    info.agentes = list(dict.fromkeys(info.agentes))
    info.reglas_existentes = list(dict.fromkeys(info.reglas_existentes))

    return info


def detectar_ecosistema(target_dir: str = ".") -> EcosistemaInfo:
    """Detecta el ecosistema completo (stack + IDE/agentes) del proyecto.

    Combina la detección por marcadores del proyecto (`.cursor/`, `.vscode/`,
    etc.) con la detección por proceso activo del sistema: si un IDE está
    corriendo ahora pero el proyecto no tiene su carpeta, igual se reporta
    (y se generan sus reglas).

    Args:
        target_dir (str): Directorio raíz del proyecto a analizar.

    Returns:
        EcosistemaInfo: Información completa del ecosistema.
    """
    ide = detectar_ide(target_dir)
    ides_proceso = detectar_ide_proceso()
    if ides_proceso:
        # Solo se marca como "por proceso" lo que no vino por marcadores
        ide.ides_por_proceso = [i for i in ides_proceso if i not in ide.ides]
        ide.ides = list(dict.fromkeys(ide.ides + ides_proceso))
    return EcosistemaInfo(
        stack=detectar_stack(target_dir),
        ide=ide,
    )

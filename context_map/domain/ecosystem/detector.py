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
    """

    ides: list[str] = field(default_factory=list)
    agentes: list[str] = field(default_factory=list)
    reglas_existentes: list[str] = field(default_factory=list)


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
        lineas = [
            "## 🧰 Stack detectado",
            f"- Lenguajes: {', '.join(self.stack.lenguajes) or 'no detectado'}",
            f"- Frameworks: {', '.join(self.stack.frameworks) or 'no detectado'}",
            f"- Test runner: {self.stack.test_runner or 'no detectado'}",
            f"- Package manager: {self.stack.package_manager or 'no detectado'}",
            f"- Entrypoints: {', '.join(self.stack.entrypoints) or 'no detectado'}",
            "",
            "## 🛠️ IDE / Agentes detectados",
            f"- IDEs: {', '.join(self.ide.ides) or 'no detectado'}",
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

        if not info.test_runner:
            if _existe(target_dir, "conftest.py") or os.path.isdir(os.path.join(target_dir, "tests")):
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
        ".clinerules", ".github/copilot-instructions.md",
    ]
    for ruta in reglas_candidatas:
        if _existe(target_dir, ruta):
            info.reglas_existentes.append(ruta)

    # --- Directorios de agentes ---
    if os.path.isdir(os.path.join(target_dir, ".hermes")):
        info.agentes.append("Hermes")
        info.reglas_existentes.append(".hermes/")
    if os.path.isdir(os.path.join(target_dir, ".claude")):
        info.agentes.append("Claude")
    if os.path.isdir(os.path.join(target_dir, ".antigravity")):
        info.agentes.append("Antigravity")
    if os.path.isdir(os.path.join(target_dir, ".github")):
        # Copilot usa .github/copilot-instructions.md; el dir .github no implica Copilot
        if _existe(target_dir, ".github/copilot-instructions.md"):
            info.agentes.append("GitHub Copilot")

    # Inferir agentes por archivos de reglas
    if "CLAUDE.md" in info.reglas_existentes:
        info.agentes.append("Claude Code")
    if ".cursorrules" in info.reglas_existentes:
        info.agentes.append("Cursor")
    if ".windsurfrules" in info.reglas_existentes:
        info.agentes.append("Windsurf")
    if ".clinerules" in info.reglas_existentes:
        info.agentes.append("Cline")
    if "AGENTS.md" in info.reglas_existentes:
        info.agentes.append("Antigravity/Cursor/Claude (AGENTS.md)")

    # Deduplicar preservando orden
    info.ides = list(dict.fromkeys(info.ides))
    info.agentes = list(dict.fromkeys(info.agentes))
    info.reglas_existentes = list(dict.fromkeys(info.reglas_existentes))

    return info


def detectar_ecosistema(target_dir: str = ".") -> EcosistemaInfo:
    """Detecta el ecosistema completo (stack + IDE/agentes) del proyecto.

    Args:
        target_dir (str): Directorio raíz del proyecto a analizar.

    Returns:
        EcosistemaInfo: Información completa del ecosistema.
    """
    return EcosistemaInfo(
        stack=detectar_stack(target_dir),
        ide=detectar_ide(target_dir),
    )

from __future__ import annotations

"""Cargador de configuración declarativa (.contextmap.toml / pyproject.toml)."""

import os
import tomllib
from typing import Optional

from context_map.core.models.config import ContextMapConfig


def load_project_config(target_dir: str = ".") -> ContextMapConfig:
    """Carga la configuración declarativa desde .contextmap.toml o pyproject.toml.

    Args:
        target_dir (str): Directorio raíz del proyecto.

    Returns:
        ContextMapConfig: Objeto de configuración inicializado.
    """
    config = ContextMapConfig()

    # 1. Intentar cargar .contextmap.toml
    custom_toml = os.path.join(target_dir, ".contextmap.toml")
    if os.path.exists(custom_toml):
        try:
            with open(custom_toml, "rb") as f:
                data = tomllib.load(f)
                config.project_name = data.get("project_name", "")
                config.ignore_dirs = data.get("ignore_dirs", [])
                config.custom_tags = data.get("custom_tags", [])
                config.mode = data.get("mode", "hierarchical")
                config.brief_enabled = data.get("brief_enabled", True)
                config.quiet = data.get("quiet", False)
                return config
        except Exception:
            pass

    # 2. Intentar cargar pyproject.toml [tool.contextmap]
    pyproject_path = os.path.join(target_dir, "pyproject.toml")
    if os.path.exists(pyproject_path):
        try:
            with open(pyproject_path, "rb") as f:
                data = tomllib.load(f)
                tool_cfg = data.get("tool", {}).get("contextmap", {})
                if tool_cfg:
                    config.project_name = tool_cfg.get("project_name", "")
                    config.ignore_dirs = tool_cfg.get("ignore_dirs", [])
                    config.custom_tags = tool_cfg.get("custom_tags", [])
                    config.mode = tool_cfg.get("mode", "hierarchical")
                    config.brief_enabled = tool_cfg.get("brief_enabled", True)
                    config.quiet = tool_cfg.get("quiet", False)
        except Exception:
            pass

    return config

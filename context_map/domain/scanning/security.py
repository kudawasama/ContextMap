"""Módulo de inspección preventiva de secretos y seguridad en el escaneo estático."""

import re
from pathlib import Path
from typing import Dict, List


class SecurityScanner:
    """Detector de patrones de credenciales, llaves API y secretos en código fuente."""

    # Patrones de expresiones regulares para identificar secretos conocidos
    PATRONES_SECRETOS: Dict[str, str] = {
        "AWS Access Key ID": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "AWS Secret Key": r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/\+=]{40}['\"]",
        "OpenAI API Key": r"sk-[a-zA-Z0-9]{32,64}",
        "Anthropic API Key": r"sk-ant-api[a-zA-Z0-9_\-]{30,80}",
        "GitHub Token": r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,255}",
        "Google API Key": r"AIzaSy[a-zA-Z0-9_\-]{35}",
        "JWT Token": r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
        "Private Key Header": r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
        "Database URI with Credentials": r"(?:postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_]+:[^@\s]+@[a-zA-Z0-9_\-\.]+",
    }

    @classmethod
    def escanear_contenido(cls, text: str, rel_path: str = "") -> List[Dict[str, str]]:
        """Inspecciona una cadena de texto en busca de patrones de secretos.

        Args:
            text: Contenido a analizar.
            rel_path: Ruta relativa del archivo para enriquecer el reporte.

        Returns:
            Lista de hallazgos con tipo de secreto, línea aproximada y recomendación.
        """
        if not text:
            return []

        hallazgos: List[Dict[str, str]] = []
        lineas = text.splitlines()

        for nombre_regla, patron in cls.PATRONES_SECRETOS.items():
            regex = re.compile(patron)
            for idx, linea in enumerate(lineas, start=1):
                # Omitir líneas de prueba o comentarios de ejemplo explícitos
                if "example" in linea.lower() or "dummy" in linea.lower() or "mock" in linea.lower():
                    continue

                coincidencias = regex.findall(linea)
                if coincidencias:
                    hallazgos.append(
                        {
                            "tipo": nombre_regla,
                            "linea": str(idx),
                            "archivo": rel_path,
                            "descripcion": f"Posible secreto expuesto ({nombre_regla}) en la línea {idx} de {rel_path}",
                            "mitigacion": "Mover el secreto a una variable de entorno (.env) o gestor de secretos.",
                        }
                    )

        return hallazgos


def escanear_secretos_archivo(file_path: Path, content: str, project_root: Path) -> List[Dict[str, str]]:
    """Función de utilidad para escanear un archivo individual.

    Args:
        file_path: Ruta absoluta o Path del archivo.
        content: Contenido leído del archivo.
        project_root: Raíz del proyecto para calcular ruta relativa.

    Returns:
        Lista de hallazgos de seguridad.
    """
    try:
        rel_path = str(file_path.relative_to(project_root))
    except Exception:
        rel_path = str(file_path)

    return SecurityScanner.escanear_contenido(content, rel_path=rel_path)

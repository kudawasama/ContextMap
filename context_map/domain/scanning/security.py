"""Módulo de inspección preventiva de secretos y seguridad en el escaneo estático."""

from __future__ import annotations

import math
import re
from collections import Counter
from pathlib import Path


def calcular_entropia_shannon(cadena: str) -> float:
    """Calcula la entropía de Shannon de una cadena de caracteres en bits por caracter.

    Args:
        cadena: Texto a evaluar.

    Returns:
        Valor de entropía (float, donde valores > 4.5 típicamente indican datos aleatorios/criptográficos).
    """
    if not cadena:
        return 0.0
    longitud = len(cadena)
    frecuencias = Counter(cadena)
    return -sum((conteo / longitud) * math.log2(conteo / longitud) for conteo in frecuencias.values())


class SecurityScanner:
    """Detector de patrones de credenciales, llaves API y secretos en código fuente."""

    # Patrones de expresiones regulares para identificar secretos conocidos
    PATRONES_SECRETOS: dict[str, str] = {
        "AWS Access Key ID": r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "AWS Secret Key": r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/\+=]{40}['\"]",
        "OpenAI API Key": r"sk-[a-zA-Z0-9]{32,64}",
        "Anthropic API Key": r"sk-ant-api[a-zA-Z0-9_\-]{30,80}",
        "GitHub Token": r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,255}",
        "Google API Key": r"AIzaSy[a-zA-Z0-9_\-]{35}",
        "Slack Token": r"xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*",
        "Stripe API Key": r"(?:sk|pk)_(?:test|live)_[0-9a-zA-Z]{24,99}",
        "Twilio API Key or SID": r"(?:SK|AC)[0-9a-fA-F]{32}",
        "SendGrid API Key": r"SG\.[a-zA-Z0-9_\-]{20,64}(?:\.[a-zA-Z0-9_\-]{20,64})?",
        "npm Access Token": r"npm_[A-Za-z0-9]{32,64}",
        "Discord Webhook": r"https:\/\/discord(?:app)?\.com\/api\/webhooks\/[0-9]{17,20}\/[A-Za-z0-9_-]{60,68}",
        "JWT Token": r"eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}",
        "Private Key Header": r"-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
        "Database URI with Credentials": r"(?:postgres|mysql|mongodb|redis):\/\/[a-zA-Z0-9_]+:[^@\s]+@[a-zA-Z0-9_\-\.]+",
    }

    PATRON_ASIGNACION_SECRETO = re.compile(
        r'(?i)\b(?:api_key|secret|password|auth_token|access_token|private_key|token|passwd)\b\s*[:=]\s*["\']([a-zA-Z0-9_\-\.\+/=]{16,})["\']'
    )

    @classmethod
    def escanear_contenido(cls, text: str, rel_path: str = "") -> list[dict[str, str]]:
        """Inspecciona una cadena de texto en busca de patrones de secretos y alta entropía.

        Args:
            text: Contenido a analizar.
            rel_path: Ruta relativa del archivo para enriquecer el reporte.

        Returns:
            Lista de hallazgos con tipo de secreto, línea aproximada y recomendación.
        """
        if not text:
            return []

        hallazgos: list[dict[str, str]] = []
        lineas = text.splitlines()

        # 1. Escaneo por firmas de patrones conocidos
        for nombre_regla, patron in cls.PATRONES_SECRETOS.items():
            regex = re.compile(patron)
            for idx, linea in enumerate(lineas, start=1):
                # Omitir líneas de prueba o comentarios de ejemplo explícitos
                if any(ign in linea.lower() for ign in ("example", "dummy", "placeholder", "fake_")):
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

        # 2. Escaneo heurístico por entropía de Shannon en asignaciones sospechosas
        for idx, linea in enumerate(lineas, start=1):
            if any(ign in linea.lower() for ign in ("example", "dummy", "placeholder", "mock")):
                continue

            match = cls.PATRON_ASIGNACION_SECRETO.search(linea)
            if match:
                valor = match.group(1)
                entropia = calcular_entropia_shannon(valor)
                if entropia >= 3.6 and len(valor) >= 16:
                    # Evitar duplicar si ya fue capturado por un patrón específico
                    linea_str = str(idx)
                    if not any(h["linea"] == linea_str and h["archivo"] == rel_path for h in hallazgos):
                        hallazgos.append(
                            {
                                "tipo": "High-Entropy Generic Secret",
                                "linea": linea_str,
                                "archivo": rel_path,
                                "descripcion": f"Posible secreto de alta entropía (Shannon: {entropia:.2f}) en la línea {idx} de {rel_path}",
                                "mitigacion": "Almacenar claves y credenciales exclusivamente en variables de entorno.",
                            }
                        )

        return hallazgos


def escanear_secretos_archivo(file_path: Path, content: str, project_root: Path) -> list[dict[str, str]]:
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

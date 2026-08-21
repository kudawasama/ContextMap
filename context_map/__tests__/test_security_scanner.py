"""Pruebas unitarias para el detector preventivo de secretos en el código fuente."""

from pathlib import Path

from context_map.domain.scanning.security import SecurityScanner, escanear_secretos_archivo


def test_detector_secretos_limpio() -> None:
    """Verifica que un archivo sin credenciales devuelva 0 hallazgos."""
    codigo_limpio = """
def sumar(a: int, b: int) -> int:
    return a + b
"""
    hallazgos = SecurityScanner.escanear_contenido(codigo_limpio, rel_path="utils.py")
    assert len(hallazgos) == 0


def test_detector_openai_key() -> None:
    """Verifica la detección de una OpenAI API key expuesta."""
    codigo_con_key = 'API_KEY = "sk-1234567890abcdef1234567890abcdef12345678"'
    hallazgos = SecurityScanner.escanear_contenido(codigo_con_key, rel_path="config.py")
    assert len(hallazgos) == 1
    assert hallazgos[0]["tipo"] == "OpenAI API Key"
    assert hallazgos[0]["linea"] == "1"


def test_detector_database_uri() -> None:
    """Verifica la detección de credenciales en conexión a base de datos."""
    codigo_db = 'DB_URL = "postgres://admin:PasswordSecret123@localhost:5432/mydb"'
    hallazgos = SecurityScanner.escanear_contenido(codigo_db, rel_path="db.py")
    assert len(hallazgos) == 1
    assert hallazgos[0]["tipo"] == "Database URI with Credentials"


def test_escanear_secretos_archivo_helper(tmp_path: Path) -> None:
    """Verifica el helper de escaneo de archivo con ruta relativa."""
    f = tmp_path / "app.py"
    contenido = 'TOKEN = "ghp_1234567890abcdef1234567890abcdef123456"'
    hallazgos = escanear_secretos_archivo(f, contenido, project_root=tmp_path)
    assert len(hallazgos) == 1
    assert hallazgos[0]["archivo"] == "app.py"

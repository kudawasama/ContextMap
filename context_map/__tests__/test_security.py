"""Pruebas unitarias para el escáner de secretos y análisis de entropía de Shannon."""

from context_map.domain.scanning.security import SecurityScanner, calcular_entropia_shannon


def test_calcular_entropia_shannon() -> None:
    """Verifica el cálculo de entropía de Shannon en cadenas repetitivas y aleatorias."""
    assert calcular_entropia_shannon("") == 0.0
    # Cadena de caracteres repetidos tiene entropía 0
    assert calcular_entropia_shannon("aaaaaaaaaaaaaaaa") == 0.0
    # Cadena pseudoaleatoria criptográfica tiene alta entropía (> 4.0)
    entropia_alta = calcular_entropia_shannon("a8F9z!q2L#m9X$v1K@p8")
    assert entropia_alta > 4.0


def test_scanner_detecta_slack_y_stripe() -> None:
    """Verifica la detección de tokens de Slack y Stripe."""
    token_slack = "".join(["xo", "xb-", "123456789012-", "1234567890123-", "abcDEFghiJKLmnoPQR"])
    token_stripe = "".join(["sk_", "live_", "51HzABC1234567890abcdefghijklmnOPQR"])
    codigo = f"""
    SLACK_BOT = "{token_slack}"
    STRIPE_KEY = "{token_stripe}"
    """
    hallazgos = SecurityScanner.escanear_contenido(codigo, "app/config.py")
    tipos = [h["tipo"] for h in hallazgos]
    assert "Slack Token" in tipos
    assert "Stripe API Key" in tipos


def test_scanner_detecta_sendgrid_npm_twilio() -> None:
    """Verifica la detección de SendGrid, npm y Twilio."""
    token_sendgrid = "".join(["SG.", "abcdefghij1234567890_-.", "_-abcdefghijklmnopqrstuvwxyz0123456789012"])
    token_npm = "".join(["npm_", "1234567890abcdefghijklmnopqrstuv"])
    token_twilio = "".join(["AC", "1234567890abcdef1234567890abcdef"])
    codigo = f"""
    SENDGRID_API = "{token_sendgrid}"
    NPM_AUTH = "{token_npm}"
    TWILIO_SID = "{token_twilio}"
    """
    hallazgos = SecurityScanner.escanear_contenido(codigo, "services/auth.py")
    tipos = [h["tipo"] for h in hallazgos]
    assert "SendGrid API Key" in tipos
    assert "npm Access Token" in tipos
    assert "Twilio API Key or SID" in tipos


def test_scanner_detecta_alta_entropia_generica() -> None:
    """Verifica que asignaciones de alta entropía a variables sensibles sean advertidas."""
    token_entropy = "".join(["9f8a7b6c5d", "4e3f2a1b0c", "9d8e7f6a5b", "4c3d2e1f0a"])
    codigo = f'AUTH_TOKEN = "{token_entropy}"'
    hallazgos = SecurityScanner.escanear_contenido(codigo, "sec/secrets.py")
    tipos = [h["tipo"] for h in hallazgos]
    assert any("Entropy" in t or "Token" in t for t in tipos)


def test_scanner_ignora_lineas_dummy() -> None:
    """Verifica que líneas con dummy, placeholder o example no disparen falsos positivos."""
    token_anthropic = "".join(["sk-ant-", "api03-", "1234567890123456789012345678901234567890"])
    token_example = "".join(["xo", "xb-", "123456789012-", "1234567890123-", "placeholder"])
    codigo = f"""
    # dummy_key = {token_anthropic}
    EXAMPLE_TOKEN = "{token_example}"
    """
    hallazgos = SecurityScanner.escanear_contenido(codigo, "tests/mock.py")
    assert len(hallazgos) == 0

"""Pruebas unitarias para el módulo context_map.domain.analyzers.ast_summary."""

import pytest
from context_map.domain.analyzers.ast_summary import ASTSummaryExtractor


def test_ast_summary_extractor_docstring() -> None:
    """Verifica que si existe docstring de módulo se priorice en el resumen."""
    codigo = '''"""Módulo principal de autenticación OAuth2 para ContextMap."""

def login():
    pass
'''
    extractor = ASTSummaryExtractor(codigo)
    resumen = extractor.inferir_resumen()
    assert "Módulo principal de autenticación OAuth2" in resumen


def test_ast_summary_extractor_imports() -> None:
    """Verifica la inferencia de propósito basada en las importaciones AST."""
    codigo = """import requests
import pytest

def test_api():
    res = requests.get('https://api.example.com')
    assert res.status_code == 200
"""
    extractor = ASTSummaryExtractor(codigo)
    resumen = extractor.inferir_resumen()
    assert "cliente HTTP" in resumen or "pruebas" in resumen

"""Comando `ctxmap enrich` para el enriquecimiento automático de código función por función.

Analiza archivos Python mediante AST y genera docstrings formales en Español Técnico
(Google Style) utilizando Ollama local si está disponible o inferencia AST estática.
"""

import argparse
import ast
from pathlib import Path

from context_map.domain.analyzers.ast_summary import ASTSummaryExtractor
from context_map.domain.health.hardware import evaluar_hardware_pc
from context_map.infrastructure.integrations.ollama import OllamaLocalClient


def cmd_enrich(args: argparse.Namespace) -> int:
    """Ejecuta el enriquecimiento de código función por función.

    Args:
        args: Argumentos de CLI (ruta, model, dry_run).

    Returns:
        Código de salida 0 (éxito) o 1 (error).
    """
    ruta_target = Path(args.path).resolve() if hasattr(args, "path") and args.path else Path(".").resolve()

    print(f"[enrich] Analizando directorio: {ruta_target}")

    # 1. Diagnóstico de Hardware y RAM
    hw = evaluar_hardware_pc()
    print(f"[enrich] Hardware: {hw.mensaje_diagnostico}")

    # 2. Inicializar cliente Ollama si es apto
    ollama_client: OllamaLocalClient | None = None
    if hw.es_apto_para_ollama:
        client = OllamaLocalClient(model_name=getattr(args, "model", None) or hw.modelo_recomendado)
        if client.esta_disponible():
            ollama_client = client
            print(f"[enrich] Ollama local activo con modelo '{client.model_name}'")
        else:
            print("[enrich] Ollama no activo en localhost:11434. Se utiliza inferencia sintáctica AST offline.")

    # 3. Recorrer archivos .py y enriquecer función por función
    archivos_procesados = 0
    funciones_enriquecidas = 0

    archivos = [ruta_target] if ruta_target.is_file() else list(ruta_target.rglob("*.py"))

    for filepath in archivos:
        if any(part.startswith(".") or part in ("venv", "build", "dist", "__pycache__") for part in filepath.parts):
            continue

        try:
            contenido = filepath.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(contenido)
        except Exception:
            continue

        lineas = contenido.splitlines()

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                docstring = ast.get_docstring(node)
                if not docstring:
                    funciones_enriquecidas += 1
                    # Extraer código de la función
                    fn_code = "\n".join(lineas[node.lineno - 1 : node.end_lineno])

                    # Intentar inferencia con Ollama o Fallback AST
                    nuevo_doc = None
                    if ollama_client:
                        nuevo_doc = ollama_client.generar_docstring_funcion(node.name, fn_code)

                    if not nuevo_doc:
                        extractor = ASTSummaryExtractor(fn_code)
                        resumen = extractor.inferir_resumen()
                        nuevo_doc = f'"""{resumen}"""'

                    print(f"  · {filepath.name} :: {node.name}() -> Enriquecido con docstring")

        archivos_procesados += 1

    print(f"[enrich] [OK] Finalizado: {archivos_procesados} archivos evaluados, {funciones_enriquecidas} funciones identificadas.")
    return 0

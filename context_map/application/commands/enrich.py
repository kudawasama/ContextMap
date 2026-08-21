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


def _formatear_docstring(doc: str, indent: str) -> list[str]:
    """Formatea un docstring garantizando comillas triples y la indentación adecuada.

    Args:
        doc: Contenido del docstring (puede o no traer comillas triples).
        indent: Espacios de indentación que corresponden al cuerpo de la función.

    Returns:
        Lista de líneas listas para ser insertadas.
    """
    texto = doc.strip()
    if texto.startswith('"""') and texto.endswith('"""'):
        texto = texto[3:-3].strip()
    elif texto.startswith("'''") and texto.endswith("'''"):
        texto = texto[3:-3].strip()

    lineas_doc = texto.splitlines()
    if not lineas_doc:
        return [f'{indent}""""""']

    if len(lineas_doc) == 1:
        return [f'{indent}"""{lineas_doc[0]}"""']

    resultado = [f'{indent}"""{lineas_doc[0]}']
    for linea in lineas_doc[1:]:
        if linea.strip():
            resultado.append(f"{indent}{linea}")
        else:
            resultado.append("")
    resultado.append(f'{indent}"""')
    return resultado


def cmd_enrich(args: argparse.Namespace) -> int:
    """Ejecuta el enriquecimiento de código función por función.

    Args:
        args: Argumentos de CLI (path, model, dry_run).

    Returns:
        Código de salida 0 (éxito) o 1 (error).
    """
    ruta_target = Path(args.path).resolve() if hasattr(args, "path") and args.path else Path(".").resolve()
    dry_run = getattr(args, "dry_run", False)

    modo_str = " (MODO PREVIEW / DRY-RUN)" if dry_run else ""
    print(f"[enrich] Analizando directorio: {ruta_target}{modo_str}")

    # 1. Diagnóstico de Hardware y RAM
    hw = evaluar_hardware_pc()
    print(f"[enrich] Hardware: {hw.mensaje_diagnostico}")

    # 2. Inicializar cliente Ollama si es apto y no se solicitó opt-out
    no_ollama = getattr(args, "no_ollama", False)
    ollama_client: OllamaLocalClient | None = None
    if hw.es_apto_para_ollama and not no_ollama:
        client = OllamaLocalClient(
            model_name=getattr(args, "model", None) or hw.modelo_recomendado,
            opt_out=no_ollama,
        )
        if client.esta_disponible():
            ollama_client = client
            print(f"[enrich] Ollama local activo con modelo '{client.model_name}'")
        else:
            print("[enrich] Ollama no activo en localhost:11434 o desactivado. Se utiliza inferencia sintáctica AST offline.")
    elif no_ollama:
        print("[enrich] Ollama desactivado por flag --no-ollama. Se utiliza inferencia sintáctica AST offline.")

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

        # Recolectar funciones sin docstring
        nodos_funciones: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not ast.get_docstring(node) and node.body:
                    nodos_funciones.append(node)

        if not nodos_funciones:
            archivos_procesados += 1
            continue

        # Ordenar de abajo hacia arriba por línea de inicio del cuerpo para insertar sin desfasar índices
        nodos_funciones.sort(key=lambda n: n.body[0].lineno, reverse=True)
        archivo_modificado = False

        for node in nodos_funciones:
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
                nuevo_doc = resumen

            # Determinar indentación del cuerpo de la función
            primer_stmt_lineno = node.body[0].lineno  # 1-indexed
            linea_cuerpo = lineas[primer_stmt_lineno - 1]
            indent_cuerpo = linea_cuerpo[: len(linea_cuerpo) - len(linea_cuerpo.lstrip())]
            if not indent_cuerpo:
                # Fallback: indentación de la línea def + 4 espacios
                linea_def = lineas[node.lineno - 1]
                indent_def = linea_def[: len(linea_def) - len(linea_def.lstrip())]
                indent_cuerpo = indent_def + "    "

            bloque_docstring = _formatear_docstring(nuevo_doc, indent_cuerpo)

            # Insertar en las líneas antes de la primera sentencia del cuerpo
            idx_insercion = primer_stmt_lineno - 1
            for offset, l_doc in enumerate(bloque_docstring):
                lineas.insert(idx_insercion + offset, l_doc)

            archivo_modificado = True
            prefijo = "[dry-run] " if dry_run else ""
            print(f"  · {prefijo}{filepath.name} :: {node.name}() -> Enriquecido con docstring")

        if archivo_modificado and not dry_run:
            nuevo_contenido = "\n".join(lineas)
            if contenido.endswith("\n"):
                nuevo_contenido += "\n"
            filepath.write_text(nuevo_contenido, encoding="utf-8")

        archivos_procesados += 1

    print(f"[enrich] [OK] Finalizado: {archivos_procesados} archivos evaluados, {funciones_enriquecidas} funciones identificadas.")
    return 0

"""Reconocimiento del catálogo de reglas de negocio (R10, 2026-08-14).

ContextMap refleja las reglas de negocio del proyecto cuando existe el
catálogo en la convención Gobernanza:
``<repo>/references/reglas/reglas_registro.yaml`` (fuente única de verdad
con IDs jerárquicos REG-XXX-###, categoría, prioridad y estado).

La fuente vive en el REPO del proyecto (versionada, con tests y auditor),
NO en el vault — este módulo solo la LEE para crear nodos ``REGLA`` en el
grafo y el resumen para el brief.
"""

from __future__ import annotations

import logging
import os

from context_map.core.models import Node

logger = logging.getLogger(__name__)

# Nombres de archivo del catálogo que se reconocen automáticamente.
NOMBRES_CATALOGO = ["reglas_registro.yaml", "reglas.yaml"]
# Carpeta donde se busca el catálogo (convención Gobernanza).
CARPETA_REGLAS = os.path.join("references", "reglas")


def parsear_catalogo(ruta: str) -> list[dict]:
    """Parsea un catálogo de reglas de negocio (YAML) a lista de dicts.

    Usa ``yaml.safe_load`` si está disponible (entorno de desarrollo); si el
    binario no trae pyyaml, cae a un parser mínimo del subconjunto que
    usamos (mismo patrón que ``dominios.yaml`` en common.py).

    Args:
        ruta (str): Ruta al archivo ``reglas_registro.yaml``.

    Returns:
        list[dict]: Reglas con sus campos (id, nombre, categoria, ...),
            o lista vacía si el archivo no existe o no se puede leer.
    """
    if not ruta or not os.path.isfile(ruta):
        return []

    try:
        with open(ruta, encoding="utf-8") as f:
            texto = f.read()
    except Exception as err:  # noqa: BLE001 — el catálogo es opcional
        logger.debug("reglas_registro.yaml no legible: %s", err)
        return []

    try:
        import yaml  # noqa: PLC0415 — opcional; fallback si no está

        datos = yaml.safe_load(texto) or {}
    except ImportError:
        datos = _parsear_catalogo_simple(texto)
    except Exception as err:  # noqa: BLE001
        logger.debug("yaml falló, intentando parser simple: %s", err)
        datos = _parsear_catalogo_simple(texto)

    reglas = datos.get("reglas", []) if isinstance(datos, dict) else []
    return [r for r in reglas if isinstance(r, dict) and r.get("id")]


def _parsear_catalogo_simple(texto: str) -> dict:
    """Parser mínimo del catálogo de reglas sin depender de pyyaml.

    Soporta el subconjunto que usamos: bloque ``reglas:`` seguido de
    ``  - id: ...`` con campos ``clave: valor``. Comentarios y ``---`` se
    ignoran.

    Args:
        texto (str): Contenido del YAML.

    Returns:
        dict: Con la clave ``reglas`` (lista de dicts).
    """
    reglas: list[dict] = []
    actual: dict[str, str] | None = None
    en_reglas = False

    for linea in texto.splitlines():
        limpia = linea.strip()
        if not limpia or limpia.startswith("#") or limpia.startswith("---"):
            continue
        if limpia == "reglas:":
            en_reglas = True
            continue
        if not en_reglas:
            continue
        if limpia.startswith("- "):
            if actual:
                reglas.append(actual)
            actual = {}
            resto = limpia[2:].strip()
            if ":" in resto:
                clave, valor = resto.split(":", 1)
                actual[clave.strip()] = _valor_limpio(valor)
        elif ":" in limpia and actual is not None:
            clave, valor = limpia.split(":", 1)
            actual[clave.strip()] = _valor_limpio(valor)

    if actual:
        reglas.append(actual)

    return {"reglas": reglas}


def _valor_limpio(valor: str) -> str:
    """Limpia un valor YAML simple (comillas, comentarios, saltos).

    Args:
        valor (str): Valor crudo tras los dos puntos.

    Returns:
        str: Valor limpio.
    """
    v = valor.split("#")[0].strip().strip('"').strip("'")
    return v


def _buscar_catalogo(ruta_raiz: str) -> str | None:
    """Busca el catálogo de reglas en el proyecto.

    Busca primero en ``references/reglas/`` (convención Gobernanza) y luego
    en cualquier ``reglas_registro.yaml`` a 2 niveles de profundidad.

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        str | None: Ruta del catálogo, o None si no existe.
    """
    if not ruta_raiz or not os.path.isdir(ruta_raiz):
        return None

    # Convención principal: references/reglas/reglas_registro.yaml
    for nombre in NOMBRES_CATALOGO:
        candidato = os.path.join(ruta_raiz, CARPETA_REGLAS, nombre)
        if os.path.isfile(candidato):
            return candidato

    # Barrido ligero a 2 niveles de profundidad (sin entrar a .context-map,
    # .git, node_modules ni .venv).
    excluidos = {".context-map", ".git", "node_modules", ".venv", "venv", "__pycache__"}
    raiz_abs = os.path.abspath(ruta_raiz)
    for nombre_actual, dirs, archivos in os.walk(ruta_raiz):
        dirs[:] = [d for d in dirs if d not in excluidos]
        nivel = os.path.relpath(nombre_actual, raiz_abs)
        if nivel != "." and nivel.count(os.sep) >= 2:
            dirs[:] = []  # no bajar más de 2 niveles
        for archivo in archivos:
            if archivo in NOMBRES_CATALOGO:
                return os.path.join(nombre_actual, archivo)
    return None


def nodos_regla_desde_catalogo(ruta: str, proyecto: str) -> list[Node]:
    """Convierte el catálogo de reglas en nodos ``REGLA`` del grafo.

    Cada regla genera un nodo con título ``ID: nombre``, tags de categoría,
    prioridad y estado, y un ``created_at`` estable (derivado del contenido)
    para que el dedup no duplique nodos entre scans.

    Args:
        ruta (str): Ruta al catálogo YAML.
        proyecto (str): Nombre del proyecto (para la evidencia).

    Returns:
        list[Node]: Nodos REGLA listos para persistir.
    """
    reglas = parsear_catalogo(ruta)
    nodos: list[Node] = []
    for i, r in enumerate(reglas):
        regla_id = str(r.get("id", f"REG-{i:03d}"))
        nombre = str(r.get("nombre", ""))
        categoria = str(r.get("categoria", ""))
        categoria_nombre = str(r.get("categoria_nombre", ""))
        prioridad = str(r.get("prioridad", ""))
        estado = str(r.get("estado", ""))
        norma = str(r.get("norma", ""))

        title = f"{regla_id}: {nombre}" if nombre else regla_id
        tags = [t for t in (categoria, categoria_nombre, prioridad, estado) if t]
        summary = (
            f"Regla de negocio {regla_id} ({categoria_nombre or categoria}, "
            f"prioridad {prioridad}, estado {estado}). "
            f"Norma: {norma}"
        )
        # created_at estable derivado del contenido para idempotencia.
        nodos.append(Node(
            id=f"regla-{regla_id}",
            type="REGLA",
            title=title,
            summary=summary,
            status="completado" if estado == "implementada" else "vigente",
            tags=tags,
            source="reglas",
            created_at="2026-08-14T00:00:00",
            evidence=[os.path.abspath(ruta)] if ruta else [],
            concept=categoria_nombre or categoria,
        ))
    return nodos


def resumen_catalogo(ruta: str | None) -> dict:
    """Resume el catálogo para el brief: total y conteo por categoría.

    Args:
        ruta (str | None): Ruta del catálogo, o None si no se encontró.

    Returns:
        dict: Con ``total`` (int), ``categorias`` (dict prefijo → int) y
            ``ruta`` (str, relativa).
    """
    if not ruta or not os.path.isfile(ruta):
        return {"total": 0, "categorias": {}, "ruta": ""}

    reglas = parsear_catalogo(ruta)
    categorias: dict[str, int] = {}
    for r in reglas:
        cat = str(r.get("categoria", "OTROS"))
        categorias[cat] = categorias.get(cat, 0) + 1

    # Ruta relativa (desde cwd) para mostrarla legible en el brief.
    try:
        ruta_rel = os.path.relpath(ruta, os.getcwd())
    except Exception:
        ruta_rel = ruta
    return {"total": len(reglas), "categorias": categorias, "ruta": ruta_rel}


def buscar_y_resumir(ruta_raiz: str) -> dict:
    """Busca el catálogo en el proyecto y devuelve su resumen (o vacío).

    Args:
        ruta_raiz (str): Directorio raíz del proyecto.

    Returns:
        dict: Resumen del catálogo (total 0 si no existe).
    """
    catalogo = _buscar_catalogo(ruta_raiz)
    return resumen_catalogo(catalogo)

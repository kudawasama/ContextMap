"""Generadores de contenido sintético y narrativa rica para el mapa conceptual.


Responsabilidades:
- Generar resúmenes educativos, profesionales e intuitivos para los nodos.
- Construir bloques de narrativa especializada según el tipo de nodo (IDEA, RIESGO, CAMBIO, BASE, PRUEBA, FUTURO).
- Clasificar eventos por contexto de origen (Git, scanner, chats sueltos).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_map.core.models import Node


def generar_summary(tipo: str, texto: str, source: str, tags: list[str]) -> str:
    """Genera un resumen explicativo adaptado al tipo y contexto del evento.

    Args:
        tipo (str): Tipo de nodo/evento ('BASE', 'IDEA', 'RIESGO', 'CAMBIO', etc.).
        texto (str): Texto crudo original.
        source (str): Origen del evento ('scanner', 'git', 'chat', etc.).
        tags (List[str]): Lista de etiquetas asociadas.

    Returns:
        str: Resumen explicativo del nodo.
    """
    texto_limpio = texto.strip()
    texto_lower = texto_limpio.lower()

    es_scanner = source == "scanner"
    es_git = source == "git"

    if tipo == "BASE":
        return _summary_base(texto_limpio, texto_lower, es_scanner, es_git)
    if tipo == "IDEA":
        return _summary_idea(texto_limpio, texto_lower, es_scanner, es_git)
    if tipo == "RIESGO":
        return _summary_riesgo(texto_limpio, texto_lower)
    if tipo == "CAMBIO":
        return _summary_cambio(texto_limpio, texto_lower, es_git)
    if tipo == "PRUEBA":
        return _summary_prueba(texto_limpio, texto_lower)
    if tipo == "FUTURO":
        return _summary_futuro(texto_limpio, texto_lower)
    if tipo == "HITO":
        return _summary_hito(texto_limpio, texto_lower, es_git)
    if tipo == "CORRECCION":
        return _summary_correccion(texto_limpio, es_git)

    return (
        f"{tipo}: {texto_limpio}. "
        "Este evento forma parte del mapa contextual del proyecto para auditar su historia."
    )


def generar_contexto_narrativo(node: Node) -> str:
    """Construye un bloque de contexto narrativo especializado según el tipo de nodo.

    Args:
        node (Node): Nodo a analizar.

    Returns:
        str: Bloque Markdown formateado con la narrativa específica del dominio.
    """
    node_type = node.type.upper()

    if node_type == "IDEA":
        return _contexto_idea(node)
    elif node_type == "RIESGO":
        return _contexto_riesgo(node)
    elif node_type in ("CAMBIO", "CORRECCION"):
        return _contexto_cambio_correccion(node)
    elif node_type == "BASE":
        return _contexto_base(node)
    elif node_type == "PRUEBA":
        return _contexto_prueba(node)
    elif node_type == "DOCUMENTO":
        return _contexto_documento(node)
    elif node_type == "FUTURO":
        return _contexto_futuro(node)
    elif node_type == "HITO":
        return _contexto_hito(node)

    return _contexto_idea(node)


def _titulo_limpio(texto: str) -> str:
    """Limpia el ruido del scanner en títulos y summaries.

    Quita los prefijos mecánicos que el scanner mete en los eventos:
    ``TODO (ruta.py:L12): texto`` y ``Pendiente: texto``, además de comillas
    triples sobrantes del código fuente.

    Args:
        texto (str): Título o summary crudo.

    Returns:
        str: Texto limpio y legible (humanizado).
    """
    t = re.sub(r"^TODO\s*\([^)]*\):\s*", "", texto or "").strip()
    t = re.sub(r"^Pendiente:\s*", "", t).strip()
    t = re.sub(r'^"""|"""$', "", t).strip()
    return t or (texto or "").strip()


def _contexto_idea(node: Node) -> str:
    """Narrativa especializada para IDEAS (Por qué, De dónde, Para qué, Cómo, Pros/Contras)."""
    title = _titulo_limpio(node.title.strip())
    summary = _titulo_limpio(node.summary.strip()) or f"Idea o concepto referente a {title}."
    source = node.source or "análisis de sistema"
    lower_title = title.lower()

    if "doc" in lower_title or "contributing" in lower_title or "readme" in lower_title:
        porque = f"El proyecto requiere estandarización documental sobre '{title}' para evitar desorden entre desarrolladores y agentes de IA."
    elif "entrypoint" in lower_title or "cli" in lower_title:
        porque = f"Es crítico definir y aislar el punto de entrada '{title}' para garantizar una interfaz de ejecución limpia."
    else:
        porque = f"Existe la necesidad técnica de abordar '{title}' para evolucionar la arquitectura del proyecto."

    de_donde = f"Surgió del análisis de '{source}' durante el escaneo y seguimiento de contexto."
    para_que = f"Para resolver '{summary}', permitiendo a los agentes de IA actuar con mayor precisión y contexto."
    como = (
        f"1. Analizar las dependencias e impacto de '{title}'.\n"
        f"2. Diseñar la solución aplicando Clean Code y principios SOLID.\n"
        f"3. Validar con pruebas automatizadas."
    )

    tabla_pros_contras = (
        "| 🟢 PROS (Ventajas) | 🔴 CONTRAS (Riesgos / Costos) |\n"
        "| :--- | :--- |\n"
        f"| Otorga claridad técnica sobre '{title[:45]}'. | Requiere mantenimiento para evitar obsolescencia del contexto. |\n"
        "| Permite autonomía a los agentes de IA. | Añade tiempo de procesamiento inicial. |"
    )

    return f"""### ❓ 1. ¿POR QUÉ es esta idea?
{porque}

### 📍 2. ¿DE DÓNDE SURGIÓ?
{de_donde}

### 🎯 3. ¿PARA QUÉ es esta idea?
{para_que}

### 🛠️ 4. ¿CÓMO se implementará?
{como}

### ⚖️ 5. PROS Y CONTRAS

{tabla_pros_contras}"""


def _contexto_riesgo(node: Node) -> str:
    """Narrativa especializada para RIESGOS (Ubicación, Gravedad, Impacto, Mitigación)."""
    title = _titulo_limpio(node.title.strip())
    summary = _titulo_limpio(node.summary.strip()) or f"Riesgo técnico identificado en {title}."
    source = node.source or "scanner"

    que_riesgo = f"Riesgo técnico o zona de alta complejidad referente a '{title}'."
    ubicacion = f"Detectado en el módulo/componente vía `{source}`."
    impacto = f"Incrementa la probabilidad de desacoplamientos o fallos al refactorizar. {summary}"
    mitigacion = (
        "1. Modularizar el componente reduciendo el número de líneas/responsabilidades.\n"
        "2. Incrementar la cobertura de pruebas unitarias antes de modificarlo.\n"
        "3. Aislar las funciones públicas mediante interfaces bien definidas."
    )

    tabla_gravedad = (
        "| ⚠️ Nivel de Gravedad | 🛡️ Estrategia de Mitigación |\n"
        "| :--- | :--- |\n"
        "| **ALTO / CRÍTICO** | Aplicar Refactoring paso a paso y agregar tests unitarios preventivos. |\n"
        "| **MEDIO** | Documentar docstrings y aislar la lógica compleja en submódulos. |"
    )

    return f"""### ⚠️ 1. ¿Qué RIESGO técnico es?
{que_riesgo}

### 📍 2. ¿Dónde se ubica el problema?
{ubicacion}

### 💥 3. ¿Qué IMPACTO tiene si se ignora?
{impacto}

### 🛡️ 4. ¿Cómo MITIGAR este riesgo?
{mitigacion}

### 📊 5. MATRIZ DE GRAVEDAD Y MITIGACIÓN

{tabla_gravedad}"""


def _contexto_documento(node: Node) -> str:
    """Narrativa especializada para DOCUMENTOS ingeridos (Síntesis + Citas).

    Los documentos externos (PDFs, MD, TXT) se convierten en nodos de
    conocimiento con una síntesis del contenido y citas textuales
    referenciadas, de modo que los agentes puedan citar la fuente exacta.

    Args:
        node (Node): Nodo de tipo DOCUMENTO.

    Returns:
        str: Bloque Markdown con síntesis y citas del documento.
    """
    title = node.title.strip()
    summary = node.summary.strip() or f"Documento de conocimiento: {title}."
    source = node.source or "ingesta de documentos"
    concepto = getattr(node, "concept", "") or "GENERAL"

    sintesis = summary
    citas = list(node.evidence or [])

    tabla_citas = "\n".join(
        f"- 📌 {cita}" for cita in citas[:10]
    ) or "- _(Sin citas extraídas)_"

    return f"""### 📄 1. ¿Qué DOCUMENTO es?
{title} — concepto `{concepto}` · ingerido vía `{source}`.

### 🧠 2. SÍNTESIS del contenido
{sintesis}

### 🔖 3. CITAS referenciadas
{tabla_citas}

### 💡 4. Para qué se ingirió
Proveer contexto fiable y trazable a los agentes de IA: el conocimiento del
documento queda a disposición del grafo sin re-leer el original cada vez."""


def _contexto_cambio_correccion(node: Node) -> str:
    """Narrativa especializada para CAMBIOS y CORRECCIONES."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Modificación registrada en {title}."
    source = node.source or "git"

    que_cambio = f"Cambio/Corrección aplicada en '{title}'."
    por_que_cambio = f"Para solucionar o refactorizar comportamientos no deseados. {summary}"
    verificacion = (
        "1. Ejecutar `python -m pytest` para confirmar no-regresión.\n"
        "2. Verificar que los módulos dependientes importan los símbolos reestructurados."
    )

    tabla_impacto = (
        "| 🔧 Tipo de Modificación | 🧪 Verificación Realizada |\n"
        "| :--- | :--- |\n"
        f"| {node.type} ({source}) | Pruebas de integración y compilación sintáctica aprobadas. |"
    )

    return f"""### 🔧 1. ¿Qué se modificó o corrigió?
{que_cambio}

### 🕵️ 2. ¿Por qué se realizó este cambio?
{por_que_cambio}

### 🧪 3. ¿Cómo se VERIFICA la no-regresión?
{verificacion}

### 📊 4. RESUMEN DE VERIFICACIÓN

{tabla_impacto}"""


def _contexto_base(node: Node) -> str:
    """Narrativa especializada para componentes BASE y estructura."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Componente estructural {title}."

    return f"""### 📦 1. ¿Qué componente BASE es?
Elemento fundamental de la arquitectura: '{title}'.

### 🏗️ 2. Rol en la Arquitectura
{summary}

### 📌 3. Puntos Clave
- Define interfaces y/o configuraciones raíz del proyecto.
- Garantiza la cohesión entre los diferentes submódulos."""


def _contexto_prueba(node: Node) -> str:
    """Narrativa especializada para PRUEBAS (QA, pytest)."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Validación de software para {title}."

    return f"""### 🧪 1. ¿Qué funcionalidad VALIDA?
Prueba de software referente a '{title}'.

### 🎯 2. Criterios de Aceptación
{summary}

### 💻 3. Comando de Ejecución
```bash
python -m pytest
```"""


def _contexto_futuro(node: Node) -> str:
    """Narrativa especializada para tareas FUTURAS / TODOs."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Tarea pendiente: {title}."

    ubicacion = ""
    match = re.search(r"TODO\s*\(([^)]+)\)", title, re.IGNORECASE)
    if match:
        ubicacion = match.group(1).strip()
    elif "Ubicación: `" in summary:
        m_sum = re.search(r"Ubicación:\s*`([^`]+)`", summary)
        if m_sum:
            ubicacion = m_sum.group(1).strip()

    ubicacion_texto = f"`{ubicacion}`" if ubicacion else summary

    return f"""### 📝 1. Tarea Pendiente (TODO)
'{title}'

### 📍 2. Detalles y Ubicación
{ubicacion_texto}

### 🎯 3. Prioridad Sugerida
Evaluada como tarea de mejora o mantenimiento pendiente para próximos desarrollos."""


def _contexto_hito(node: Node) -> str:
    """Narrativa especializada para HITOS de versión."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Hito alcanzado: {title}."

    return f"""### 🎯 1. Hito Alcantado
'{title}'

### 📌 2. Significado en la Historia del Proyecto
{summary}"""


def _summary_base(texto: str, lower: str, es_scanner: bool, es_git: bool) -> str:
    """Resumen para eventos de tipo BASE."""
    if es_scanner:
        if "archivos" in lower and "líneas" in lower:
            return f"{texto}."
        if "entry point" in lower or "entrypoint" in lower:
            modulo = texto.split(":")[-1].strip() if ":" in texto else texto
            return f"Entrypoint del proyecto: `{modulo}`."
        if "config" in lower or "pyproject" in lower:
            return f"Configuración: {texto}."
        if "doc" in lower or "readme" in lower or "contributing" in lower:
            return f"Documentación: {texto}."
    if es_git:
        return f"Repositorio: {texto}."
    return f"{texto}."


def _summary_idea(texto: str, lower: str, es_scanner: bool, es_git: bool) -> str:
    """Resumen para eventos de tipo IDEA."""
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            return f"Feature implementada: {partes[1]}"
    if es_scanner:
        if "clase" in lower or "función" in lower:
            return f"Componente de código detectado: {texto}."
        if "docstring" in lower or "descripción" in lower:
            return f"Documentación interna del código: {texto}."
        if "estructura" in lower:
            return f"Aspecto estructural: {texto}."
    return f"Idea o implementación relevante. {texto}."


def _summary_riesgo(texto: str, lower: str) -> str:
    """Resumen para eventos de tipo RIESGO."""
    if "complejidad" in lower or "complejo" in lower:
        return f"Zona de alta complejidad: {texto}."
    if "dependencia" in lower or "depend" in lower:
        return f"Dependencia: {texto}."
    return f"Riesgo: {texto}."


def _summary_cambio(texto: str, lower: str, es_git: bool) -> str:
    """Resumen para eventos de tipo CAMBIO."""
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            return f"Cambio: {partes[1]}"
    if "conversación" in lower or "chat" in lower:
        return f"Decisión discutida en conversación: {texto}."
    return f"Cambio en el proyecto: {texto}."


def _summary_prueba(texto: str, lower: str) -> str:
    """Resumen para eventos de tipo PRUEBA."""
    if "test" in lower or "pytest" in lower:
        return f"Prueba detectada: {texto}."
    return f"Validación del proyecto: {texto}."


def _summary_futuro(texto: str, lower: str) -> str:
    """Resumen para eventos de tipo FUTURO."""
    if "todo" in lower or "pendiente" in lower:
        match = re.search(r"TODO\s*\(([^)]+)\):\s*(.*)", texto, re.IGNORECASE)
        if match:
            ubicacion = match.group(1).strip()
            detalle = match.group(2).strip()
            return f"Pendiente: {detalle}.\n\nUbicación: `{ubicacion}`"

        if ":" in texto:
            partes = texto.split(":", 1)
            if len(partes) >= 2:
                ubicacion = partes[0].strip()
                detalle = partes[1].strip()
                return f"Pendiente: {detalle}.\n\nUbicación: `{ubicacion}`"
        return f"Pendiente: {texto}."
    if "futuro" in lower or "próximo" in lower or "roadmap" in texto:
        return f"Plan: {texto}."
    return f"Tarea: {texto}."


def _summary_hito(texto: str, lower: str, es_git: bool) -> str:
    """Resumen para eventos de tipo HITO."""
    if "tag" in lower or "v0" in lower or "release" in lower:
        return f"🎯 Versión publicada: {texto}."
    if es_git:
        return f"Hito alcanzado: {texto}."
    return f"🎯 Hito del proyecto: {texto}."


def _summary_correccion(texto: str, es_git: bool) -> str:
    """Resumen para eventos de tipo CORRECCION."""
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            return f"Corrección: {partes[1]}"
    return f"Corrección: {texto}."

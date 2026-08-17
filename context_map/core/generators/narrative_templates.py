"""Submódulo de plantillas narrativas polimórficas por tipo de nodo."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from context_map.core.models import Node


def titulo_limpio(texto: str) -> str:
    """Limpia el ruido del scanner en títulos y summaries."""
    t = re.sub(r"^TODO\s*\([^)]*\):\s*", "", texto or "").strip()
    t = re.sub(r"^Pendiente:\s*", "", t).strip()
    t = re.sub(r'^"""|"""$', "", t).strip()
    return t or (texto or "").strip()


def contexto_idea(node: Node) -> str:
    """Narrativa especializada para IDEAS."""
    title = titulo_limpio(node.title.strip())
    summary = titulo_limpio(node.summary.strip()) or f"Idea o concepto referente a {title}."
    source = node.source or "análisis de sistema"
    lower_title = title.lower()

    if "doc" in lower_title or "contributing" in lower_title or "readme" in lower_title:
        porque = f"El proyecto requiere estandarización documental sobre '{title}' para evitar desorden entre desarrolladores y agentes de IA."
    elif "entrypoint" in lower_title or "cli" in lower_title:
        porque = f"Es crítico definir y aislar el punto de entrada '{title}' para garantizar una interfaz de ejecución limpia."
    else:
        porque = (
            f"Falta contexto registrado del porqué de '{title}'. "
            "Completar con la historia real: conversación, decisión o dolor que la originó."
        )

    de_donde = f"Surgió de '{source}' (escaneo de código o importación de historia)."
    para_que = f"Resuelve: {summary}. Completar el impacto esperado con el dueño."
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

    para_quien = "Pendiente de contexto — preguntar al dueño del proyecto para quién es."
    valor = "Pendiente de contexto — qué valor aporta y qué se gana al implementarla."
    riesgo_no_hacer = "Pendiente de contexto — qué se arriesga si no se hace (deuda o impacto)."
    listo = "Pendiente de contexto — definir criterios de aceptación con el dueño."
    dependencias = "Sin dependencias registradas (ver 🔗 Conexiones del mapa)."

    return f"""### ❓ 1. ¿POR QUÉ es esta idea?
{porque}

### 📍 2. ¿DE DÓNDE SURGIÓ?
{de_donde}

### 🎯 3. ¿PARA QUÉ es esta idea?
{para_que}

### 🛠️ 4. ¿CÓMO se implementará?
{como}

### ⚖️ 5. PROS Y CONTRAS

{tabla_pros_contras}

### 👥 6. ¿PARA QUIÉN es? (stakeholders)
{para_quien}

### 💰 7. ¿QUÉ VALOR APORTA? (qué se gana)
{valor}

### ⚠️ 8. ¿QUÉ SE ARRIESGA SI NO SE HACE? (costo de no hacer)
{riesgo_no_hacer}

### ✅ 9. ¿CÓMO SE SABE QUE ESTÁ LISTO? (criterios de aceptación)
{listo}

### 🔗 10. ¿DE QUÉ DEPENDE? (dependencias y orden)
{dependencias}"""


def contexto_riesgo(node: Node) -> str:
    """Narrativa especializada para RIESGOS."""
    title = titulo_limpio(node.title.strip())
    summary = titulo_limpio(node.summary.strip()) or f"Riesgo técnico identificado en {title}."
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


def contexto_documento(node: Node) -> str:
    """Narrativa especializada para DOCUMENTOS."""
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


def contexto_cambio_correccion(node: Node) -> str:
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


def contexto_base(node: Node) -> str:
    """Narrativa especializada para componentes BASE."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Componente estructural {title}."

    return f"""### 📦 1. ¿Qué componente BASE es?
Elemento fundamental de la arquitectura: '{title}'.

### 🏗️ 2. Rol en la Arquitectura
{summary}

### 📌 3. Puntos Clave
- Define interfaces y/o configuraciones raíz del proyecto.
- Garantiza la cohesión entre los diferentes submódulos."""


def contexto_prueba(node: Node) -> str:
    """Narrativa especializada para PRUEBAS."""
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


def contexto_futuro(node: Node) -> str:
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
Evaluada como tarea de mejora o mantenimiento pendiente para próximos desarrollos.

### ✅ 4. ¿Cómo se sabe que está LISTA? (criterios)
Pendiente de contexto — definir con el dueño qué valida que la tarea quedó hecha.

### 👤 5. Responsable sugerido
Pendiente de contexto — quién la trabajará."""


def contexto_hito(node: Node) -> str:
    """Narrativa especializada para HITOS."""
    title = node.title.strip()
    summary = node.summary.strip() or f"Hito alcanzado: {title}."

    return f"""### 🎯 1. Hito Alcanzado
'{title}'

### 📌 2. Significado en la Historia del Proyecto
{summary}"""

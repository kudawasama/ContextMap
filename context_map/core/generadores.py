"""Generadores de contenido para nodos del mapa.

Responsabilidades:
- Generar summaries educativos, profesionales e intuitivos.
- Clasificar eventos por contexto y tipo.
- Crear descripciones útiles para estudiar el proyecto.
"""

from __future__ import annotations
from typing import List


def generar_summary(tipo: str, texto: str, source: str, tags: List[str]) -> str:
    """Genera un summary educativo, profesional e intuitivo.

    Objetivo: que cualquier agente o persona pueda entender el contexto
    sin necesidad de leer el código fuente. Las descripciones deben ser
    útiles para estudiar y revisar el proyecto.
    """
    texto_limpio = texto.strip()
    texto_lower = texto_limpio.lower()

    # Detectar contexto del evento
    es_scanner = source == "scanner"
    es_git = source == "git"
    es_chat = source.startswith("chat")

    # === BASE: Fundamentos del proyecto ===
    if tipo == "BASE":
        return _summary_base(texto_limpio, texto_lower, es_scanner, es_git)

    # === IDEA: Ideas, conceptos, implementaciones ===
    if tipo == "IDEA":
        return _summary_idea(texto_limpio, texto_lower, es_scanner, es_git)

    # === RIESGO: Problemas potenciales ===
    if tipo == "RIESGO":
        return _summary_riesgo(texto_limpio, texto_lower)

    # === CAMBIO: Modificaciones en curso ===
    if tipo == "CAMBIO":
        return _summary_cambio(texto_limpio, texto_lower, es_git)

    # === PRUEBA: Testing y validación ===
    if tipo == "PRUEBA":
        return _summary_prueba(texto_limpio, texto_lower)

    # === FUTURO: Lo que viene ===
    if tipo == "FUTURO":
        return _summary_futuro(texto_limpio, texto_lower)

    # === HITO: Logros y versiones ===
    if tipo == "HITO":
        return _summary_hito(texto_limpio, texto_lower, es_git)

    # === CORRECCION: Bugs y fixes ===
    if tipo == "CORRECCION":
        return _summary_correccion(texto_limpio, es_git)

    # Default genérico
    return (
        f"{tipo}: {texto_limpio}. "
        f"Este evento es parte del contexto del proyecto y ayuda a entender "
        f"su historia y evolución."
    )


def _summary_base(texto: str, lower: str, es_scanner: bool, es_git: bool) -> str:
    """Summary para eventos BASE."""
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
    """Summary para eventos IDEA."""
    if es_git:
        if "] " in texto:
            partes = texto.split("] ", 1)
            if len(partes) == 2:
                commit_msg = partes[1]
                return f"Feature implementada: {commit_msg}"
    if es_scanner:
        if "clase" in lower or "función" in lower:
            return (
                f"Componente de código detectado: {texto}. "
                f"Las clases y funciones son los bloques de construcción del proyecto. "
                f"Cada una tiene una responsabilidad específica."
            )
        if "docstring" in lower or "descripción" in lower:
            return (
                f"Documentación interna del código: {texto}. "
                f"Los docstrings explican qué hace cada módulo, clase o función. "
                f"Son esenciales para entender el código sin leerlo línea por línea."
            )
        if "estructura" in lower:
            return (
                f"Aspecto estructural: {texto}. "
                f"La estructura del proyecto determina cómo se organiza el código "
                f"y cómo los diferentes módulos se relacionan entre sí."
            )
    return (
        f"Idea o implementación relevante. {texto}. "
        f"Este concepto es parte fundamental de cómo funciona o evoluciona el proyecto."
    )


def _summary_riesgo(texto: str, lower: str) -> str:
    """Summary para eventos RIESGO."""
    if "complejidad" in lower or "complejo" in lower:
        return f"Zona de alta complejidad: {texto}."
    if "dependencia" in lower or "depend" in lower:
        return f"Dependencia: {texto}."
    return f"Riesgo: {texto}."


def _summary_cambio(texto: str, lower: str, es_git: bool) -> str:
    """Summary para eventos CAMBIO."""
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            commit_msg = partes[1]
            return f"Cambio: {commit_msg}"
    if "conversación" in lower or "chat" in lower:
        return f"Decisión discutida en conversación: {texto}."
    return f"Cambio en el proyecto: {texto}."


def _summary_prueba(texto: str, lower: str) -> str:
    """Summary para eventos PRUEBA."""
    if "test" in lower or "pytest" in lower:
        return (
            f"Prueba detectada: {texto}. "
            f"Los tests verifican que el código funciona correctamente. "
            f"Ejecuta `pytest` antes de cada commit para asegurar que nada se rompió."
        )
    return (
        f"Validación del proyecto: {texto}. "
        f"Las pruebas son la primera línea de defensa contra bugs. "
        f"Siempre prueba antes de desplegar."
    )


def _summary_futuro(texto: str, lower: str) -> str:
    """Summary para eventos FUTURO."""
    if "todo" in lower or "pendiente" in lower:
        ubicacion = ""
        if "en " in lower or ":" in texto:
            partes = texto.split(":")
            if len(partes) >= 2:
                ubicacion = partes[0].strip()
        result = f"Pendiente: {texto}."
        if ubicacion:
            result += f"\n\nUbicación: `{ubicacion}`"
        return result
    if "futuro" in lower or "próximo" in lower or "roadmap" in texto:
        return f"Plan: {texto}."
    return f"Tarea: {texto}."


def _summary_hito(texto: str, lower: str, es_git: bool) -> str:
    """Summary para eventos HITO."""
    if "tag" in lower or "v0" in lower or "release" in lower:
        return (
            f"🎯 Versión publicada: {texto}. "
            f"Los hitos marcan puntos estables del proyecto donde se puede "
            f"usar en producción con confianza."
        )
    if es_git:
        return (
            f"Hito alcanzado: {texto}. "
            f"Este commit marca un punto importante en la evolución del proyecto."
        )
    return (
        f"🎯 Hito del proyecto: {texto}. "
        f"Los hitos ayudan a trackear el progreso y celebrar logros."
    )


def _summary_correccion(texto: str, es_git: bool) -> str:
    """Summary para eventos CORRECCION."""
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            commit_msg = partes[1]
            return f"Corrección: {commit_msg}"
    return f"Corrección: {texto}."

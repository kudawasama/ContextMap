"""Generadores de contenido sintético y narrativa rica para el mapa conceptual.

Fachada modularizada que desacopla la generación de summaries y las plantillas
narrativas polimórficas por tipo de nodo.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from context_map.core.generators.narrative_templates import (
    contexto_base as _contexto_base,
    contexto_cambio_correccion as _contexto_cambio_correccion,
    contexto_documento as _contexto_documento,
    contexto_futuro as _contexto_futuro,
    contexto_hito as _contexto_hito,
    contexto_idea as _contexto_idea,
    contexto_prueba as _contexto_prueba,
    contexto_riesgo as _contexto_riesgo,
    titulo_limpio as _titulo_limpio,
)

if TYPE_CHECKING:
    from context_map.core.models import Node


def generar_summary(tipo: str, texto: str, source: str, tags: list[str]) -> str:
    """Genera un resumen explicativo adaptado al tipo y contexto del evento."""
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
    """Construye un bloque de contexto narrativo especializado según el tipo de nodo."""
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


def _summary_base(texto: str, lower: str, es_scanner: bool, es_git: bool) -> str:
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
    if "complejidad" in lower or "complejo" in lower:
        return f"Zona de alta complejidad: {texto}."
    if "dependencia" in lower or "depend" in lower:
        return f"Dependencia: {texto}."
    return f"Riesgo: {texto}."


def _summary_cambio(texto: str, lower: str, es_git: bool) -> str:
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            return f"Cambio: {partes[1]}"
    if "conversación" in lower or "chat" in lower:
        return f"Decisión discutida en conversación: {texto}."
    return f"Cambio en el proyecto: {texto}."


def _summary_prueba(texto: str, lower: str) -> str:
    if "test" in lower or "pytest" in lower:
        return f"Prueba detectada: {texto}."
    return f"Validación del proyecto: {texto}."


def _summary_futuro(texto: str, lower: str) -> str:
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
    if "tag" in lower or "v0" in lower or "release" in lower:
        return f"🎯 Versión publicada: {texto}."
    if es_git:
        return f"Hito alcanzado: {texto}."
    return f"🎯 Hito del proyecto: {texto}."


def _summary_correccion(texto: str, es_git: bool) -> str:
    if es_git and "] " in texto:
        partes = texto.split("] ", 1)
        if len(partes) == 2:
            return f"Corrección: {partes[1]}"
    return f"Corrección: {texto}."


__all__ = [
    "generar_summary",
    "generar_contexto_narrativo",
    "_titulo_limpio",
    "_contexto_idea",
    "_contexto_riesgo",
    "_contexto_documento",
    "_contexto_cambio_correccion",
    "_contexto_base",
    "_contexto_prueba",
    "_contexto_futuro",
    "_contexto_hito",
]

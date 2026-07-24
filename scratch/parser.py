from __future__ import annotations

"""Parser de eventos normalizados desde JSONL agnóstico o chats sueltos.

Responsabilidades:
- Normalizar entradas heterogéneas.
- Clasificar heurísticamente eventos no tipados.
- Desduplicar eventos repetidos.
- Convertir eventos en grafo: `Node` y `Edge`.
"""

import json
import re
from typing import Any, Dict, List, Tuple, Union

from context_map.models import Event, Node, Edge


JSONL_TYPES = {"IDEA", "BASE", "PRUEBA", "FUTURO", "CORRECCION", "RIESGO", "CAMBIO", "HITO"}


# Patrones determinísticos para tipo de evento cuando el origen no trae `type`.
_LINE_PATTERNS: List[Tuple[Union[str, re.Pattern[str]], str]] = [
    (re.compile(r"\b(adding|added|feat|feature)\b", re.I), "IDEA"),
    (re.compile(r"\b(fix|fixing|correc|patch)\b", re.I), "CORRECCION"),
    (re.compile(r"\b(test|tested|pytest|spec|qa)\b", re.I), "PRUEBA"),
    (re.compile(r"\b(next|future|todo|planned|roadmap)\b", re.I), "FUTURO"),
    (re.compile(r"\b(risk|bug|issue|danger|blocked)\b", re.I), "RIESGO"),
    (re.compile(r"\b(change|changed|update|updated)\b", re.I), "CAMBIO"),
    (re.compile(r"\b(base|init|seed|bootstrap|setup)\b", re.I), "BASE"),
    (re.compile(r"\b(release|milestone|hit)\b", re.I), "HITO"),
]


def _safe_jsonl(path: str) -> List[Dict[str, Any]]:
    """Lee objetos JSON desde un JSONL tolerando errores de parseo."""
    out: List[Dict[str, Any]] = []
    if not path or not isinstance(path, str):
        return out
    if not __import__("os").path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def load_events_from_jsonl(path: str) -> List[Event]:
    """Convierte líneas JSON tipadas en `Event`.

    Solo conserva tipos válidos y textos presentes.
    """
    events: List[Event] = []
    for obj in _safe_jsonl(path):
        t = obj.get("type", "")
        if not isinstance(t, str):
            continue
        t = t.upper().strip()
        text = str(obj.get("text", "")).strip()
        if t in JSONL_TYPES and text:
            events.append(
                Event(
                    type=t,
                    text=text,
                    timestamp=str(obj.get("timestamp", "")),
                    source=str(obj.get("source", "")),
                    tags=list(obj.get("tags") or []),
                    meta=obj.get("meta") or {},
                )
            )
    return events


def _heuristic_event(raw: str, source_hint: str) -> Event:
    """Clasifica texto libre usando reglas léxicas."""
    text = raw.strip()
    kind = "IDEA"
    for pat, k in _LINE_PATTERNS:
        if isinstance(pat, re.Pattern) and pat.search(text):
            kind = k
            break
    return Event(type=kind, text=text, timestamp="", source=source_hint)


def load_events_from_chat_folder(folder: str) -> List[Event]:
    """Lee archivos de chat y produce eventos clasificados."""
    events: List[Event] = []
    if not folder or not __import__("os").path.isdir(folder):
        return events
    for name in sorted(__import__("os").listdir(folder)):
        path = __import__("os").path.join(folder, name)
        if not __import__("os").path.isfile(path):
            continue
        source = f"chat:{name}"
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or len(line) < 8:
                        continue
                    events.append(_heuristic_event(line, source))
        except Exception:
            continue
    return events


def _dedup_events(events: List[Event]) -> List[Event]:
    """Elimina duplicados preservando orden cronológico."""
    seen: set = set()
    out: List[Event] = []
    for e in sorted(
        events,
        key=lambda x: (x.timestamp or "", x.source, x.text[:40]),
    ):
        k = (e.type, e.text, e.source)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    return out


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def _generar_summary(tipo: str, texto: str, source: str, tags: List[str]) -> str:
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
    es_manual = source in ("manual", "")

    # === BASE: Fundamentos del proyecto ===
    if tipo == "BASE":
        if es_scanner:
            if "archivos" in texto_lower and "líneas" in texto_lower:
                return (
                    f"Este es el estado actual del código fuente. "
                    f"{texto_limpio}. "
                    f"Esta métrica te da una idea del tamaño y complejidad del proyecto: "
                    f"más archivos y líneas implican mayor superficie de mantenimiento."
                )
            if "entry point" in texto_lower or "entrypoint" in texto_lower:
                modulo = texto_limpio.split(":")[-1].strip() if ":" in texto_limpio else texto_limpio
                return (
                    f"El punto de entrada del proyecto es `{modulo}`. "
                    f"Este es el archivo que se ejecuta primero cuando corres el programa. "
                    f"Si necesitas entender cómo funciona el proyecto, empieza por aquí."
                )
            if "config" in texto_lower or "pyproject" in texto_lower:
                return (
                    f"Configuración del proyecto detectada: {texto_limpio}. "
                    f"Este archivo define metadatos, dependencias y puntos de entrada. "
                    f"Los agentes de IA lo usan para entender qué librerías están disponibles."
                )
            if "doc" in texto_lower or "readme" in texto_lower or "contributing" in texto_lower:
                return (
                    f"Documentación encontrada: {texto_limpio}. "
                    f"Estos archivos explican cómo usar, contribuir y entender el proyecto. "
                    f"Lee el README primero para una visión general."
                )
            if "lenguaje" in texto_lower or "python" in texto_lower:
                return (
                    f"Tecnología principal: {texto_limpio}. "
                    f"Esto define qué herramientas y librerías puedes usar al trabajar en el proyecto."
                )
        if es_git:
            return (
                f"Estado del repositorio: {texto_limpio}. "
                f"El historial de git muestra la evolución del proyecto y las decisiones tomadas."
            )
        # Default BASE
        return (
            f"Elemento fundamento del proyecto. {texto_limpio}. "
            f"Entender esto es esencial antes de hacer cambios."
        )

    # === IDEA: Ideas, conceptos, implementaciones ===
    if tipo == "IDEA":
        if es_git:
            # Parsear commit: [hash] tipo: descripción
            commit_match = texto_limpio
            if "] " in commit_match:
                partes = commit_match.split("] ", 1)
                if len(partes) == 2:
                    commit_hash = partes[0].replace("[", "")
                    commit_msg = partes[1]
                    return (
                        f"Este commit (`{commit_hash}`) implementa: {commit_msg}. "
                        f"Los commits son unidades atómicas de cambio que mantienen el historial limpio. "
                        f"Cada commit debe resolver un solo problema o agregar una funcionalidad."
                    )
        if es_scanner:
            if "clase" in texto_lower or "función" in texto_lower:
                return (
                    f"Componente de código detectado: {texto_limpio}. "
                    f"Las clases y funciones son los bloques de construcción del proyecto. "
                    f"Cada una tiene una responsabilidad específica."
                )
            if "docstring" in texto_lower or "descripción" in texto_lower:
                return (
                    f"Documentación interna del código: {texto_limpio}. "
                    f"Los docstrings explican qué hace cada módulo, clase o función. "
                    f"Son esenciales para entender el código sin leerlo línea por línea."
                )
            if "estructura" in texto_lower:
                return (
                    f"Aspecto estructural: {texto_limpio}. "
                    f"La estructura del proyecto determina cómo se organiza el código "
                    f"y cómo los diferentes módulos se relacionan entre sí."
                )
        # Default IDEA
        return (
            f"Idea o implementación relevante. {texto_limpio}. "
            f"Este concepto es parte fundamental de cómo funciona o evoluciona el proyecto."
        )

    # === RIESGO: Problemas potenciales ===
    if tipo == "RIESGO":
        if "test" in texto_lower:
            return (
                f"⚠️ Riesgo importante: {texto_limpio}. "
                f"Sin tests automatizados, cualquier cambio puede romper funcionalidad "
                f"existente sin que te des cuenta. Los tests protegen contra regresiones "
                f"y dan confianza para hacer cambios."
            )
        if "complejidad" in texto_lower or "complejo" in texto_lower:
            return (
                f"⚠️ Zona de alta complejidad: {texto_limpio}. "
                f"Estas áreas son propensas a bugs y difíciles de mantener. "
                f"Considera refactorizar o agregar documentación extra."
            )
        if "dependencia" in texto_lower or "depend" in texto_lower:
            return (
                f"⚠️ Dependencia potencial: {texto_limpio}. "
                f"Las dependencias externas pueden cambiar o dejarse de mantener. "
                f"Verifica que estén activas y sean compatibles."
            )
        # Default RIESGO
        return (
            f"⚠️ Riesgo identificado: {texto_limpio}. "
            f"Este problema puede afectar la calidad, mantenibilidad o estabilidad del proyecto. "
            f"Requiere atención antes de hacer cambios significativos."
        )

    # === CAMBIO: Modificaciones en curso ===
    if tipo == "CAMBIO":
        if es_git:
            if "] " in texto_limpio:
                partes = texto_limpio.split("] ", 1)
                if len(partes) == 2:
                    commit_hash = partes[0].replace("[", "")
                    commit_msg = partes[1]
                    return (
                        f"Cambio registrado en commit `{commit_hash}`: {commit_msg}. "
                        f"Cada cambio en git es rastreable y reversible. "
                        f"Esto te permite entender qué se modificó y por qué."
                    )
        if "conversación" in texto_lower or "chat" in texto_lower:
            return (
                f"Decisión discutida en conversación: {texto_limpio}. "
                f"Las decisiones tomadas en chat definen la dirección del proyecto "
                f"y son tan importantes como el código mismo."
            )
        # Default CAMBIO
        return (
            f"Cambio en el proyecto: {texto_limpio}. "
            f"Los cambios deben ser bien documentados para que otros entiendan "
            f"qué se modificó y cuál fue la razón."
        )

    # === PRUEBA: Testing y validación ===
    if tipo == "PRUEBA":
        if "test" in texto_lower or "pytest" in texto_lower:
            return (
                f"Prueba detectada: {texto_limpio}. "
                f"Los tests verifican que el código funciona correctamente. "
                f"Ejecuta `pytest` antes de cada commit para asegurar que nada se rompió."
            )
        return (
            f"Validación del proyecto: {texto_limpio}. "
            f"Las pruebas son la红线 de defensa contra bugs. "
            f"Siempre prueba antes de desplegar."
        )

    # === FUTURO: Lo que viene ===
    if tipo == "FUTURO":
        if "todo" in texto_lower or "pendiente" in texto_lower:
            # Extraer ubicación si existe
            ubicacion = ""
            if "en " in texto_lower or ":" in texto_limpio:
                partes = texto_limpio.split(":")
                if len(partes) >= 2:
                    ubicacion = partes[0].strip()
            return (
                f"📝 Tarea pendiente: {texto_limpio}. "
                f"Los TODOs son recordatorios de funcionalidad que falta por implementar. "
                f"Revisa estos items cuando busques cómo contribuir al proyecto."
                + (f"\n\nUbicación: `{ubicacion}`" if ubicacion else "")
            )
        if "futuro" in texto_lower or "próximo" in texto_lower or "roadmap" in texto_limpio:
            return (
                f"🔮 Planificación futura: {texto_limpio}. "
                f"Estos elementos están en la hoja de ruta del proyecto "
                f"y se implementarán cuando las prioridades lo permitan."
            )
        # Default FUTURO
        return (
            f"Elemento futuro o pendiente: {texto_limpio}. "
            f"Esto está planificado pero aún no se ha implementado. "
            f"Puede ser una buena oportunidad para contribuir."
        )

    # === HITO: Logros y versiones ===
    if tipo == "HITO":
        if "tag" in texto_lower or "v0" in texto_lower or "release" in texto_lower:
            return (
                f"🎯 Versión publicada: {texto_limpio}. "
                f"Los hitos marcan puntos estables del proyecto donde se puede "
                f"usar en producción con confianza."
            )
        if es_git:
            return (
                f"Hito alcanzado: {texto_limpio}. "
                f"Este commit marca un punto importante en la evolución del proyecto."
            )
        return (
            f"🎯 Hito del proyecto: {texto_limpio}. "
            f"Los hitos ayudan a trackear el progreso y celebrar logros."
        )

    # === CORRECCION: Bugs y fixes ===
    if tipo == "CORRECCION":
        if es_git:
            if "] " in texto_limpio:
                partes = texto_limpio.split("] ", 1)
                if len(partes) == 2:
                    commit_hash = partes[0].replace("[", "")
                    commit_msg = partes[1]
                    return (
                        f"🔧 Corrección aplicada en `{commit_hash}`: {commit_msg}. "
                        f"Los fixes deben ser atómicos y describir claramente "
                        f"qué problema resuelven."
                    )
        return (
            f"🔧 Corrección: {texto_limpio}. "
            f"Los bugs deben documentarse para evitar que reaparezcan "
            f"y para entender qué problemas ha tenido el proyecto."
        )

    # === Default genérico ===
    return (
        f"{tipo}: {texto_limpio}. "
        f"Este evento es parte del contexto del proyecto y ayuda a entender "
        f"su historia y evolución."
    )


def events_to_model(
    events: List[Event], start_id: int = 1
) -> Tuple[List[Node], List[Edge]]:
    """Transforma eventos en nodos y aristas.

    Consecuencias de diseño:
    - IDs estables por tipo.
    - Conexiones livianas cuando el texto menciona dependencias.
    """
    nodes: List[Node] = []
    edges: List[Edge] = []
    counters: Dict[str, int] = {}
    id_by_key: Dict[Tuple[str, str, str], str] = {}

    def _prefix(t: str) -> str:
        return t if t in JSONL_TYPES else "IDEA"

    for e in events:
        prefix = _prefix(e.type)
        counters[prefix] = counters.get(prefix, 0) + 1
        pid = f"{prefix}.{counters[prefix]:003d}"
        title = e.text.split("\n")[0][:90]

        # Generar summary más descriptivo
        summary = _generar_summary(e.type, e.text, e.source, e.tags)

        node = Node(
            id=pid,
            type=prefix,
            title=title,
            summary=summary,
            tags=list(e.tags),
            source=e.source,
            created_at=e.timestamp or _now(),
            updated_at=e.timestamp or _now(),
        )
        nodes.append(node)
        id_by_key[(e.type, e.source, e.text)] = pid

        lowered = e.text.lower()
        if "termina en" in lowered or "=>" in e.text:
            parts = re.split(r"=>|termina en|\n", e.text)
            if len(parts) >= 2:
                target_text = parts[-1].strip()[:120]
                for k, tid in id_by_key.items():
                    if target_text and target_text.lower() in k[2].lower() and tid != pid:
                        edges.append(Edge(source=pid, target=tid, kind="depends_on"))
                        node.depends_on.append(tid)
                        break

    return nodes, edges

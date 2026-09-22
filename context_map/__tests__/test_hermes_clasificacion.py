"""Patrones de cierre → tipos específicos (R6, auditoría 2026-08-14).

Verifica que ``extraer_contexto_sesion`` clasifica mensajes del asistente con
patrones de cierre como DECISION/CORRECCION/LECCION en vez de IDEA genérica.
"""

from __future__ import annotations

from context_map.infrastructure.integrations.hermes import (
    Mensaje,
    Sesion,
    extraer_contexto_sesion,
)


def _sesion_con(rol: str, contenido: str) -> Sesion:
    """Crea una sesión de un solo mensaje.

    Args:
        rol (str): Rol del mensaje (user/assistant/tool).
        contenido (str): Texto del mensaje.

    Returns:
        Sesion: Sesión mínima para el clasificador.
    """
    return Sesion(
        id="s1",
        titulo="Test",
        fecha_inicio="2026-08-14",
        mensajes=[Mensaje(id=1, rol=rol, contenido=contenido, herramienta="")],
    )


def _tipos(ev: list[dict]) -> list[str]:
    """Extrae los tipos de los eventos generados.

    Args:
        ev (list[dict]): Eventos generados por el clasificador.

    Returns:
        list[str]: Tipos presentes.
    """
    return [e["type"] for e in ev]


def test_quedo_implementado_es_correccion():
    """Un cierre tipo 'quedó implementado en commit X' es CORRECCION."""
    ev = extraer_contexto_sesion(_sesion_con("assistant", "quedó implementado en commit abc"))
    assert "CORRECCION" in _tipos(ev)


def test_regla_definitiva_es_decision():
    """Un cierre tipo 'la regla definitiva es...' es DECISION."""
    ev = extraer_contexto_sesion(_sesion_con("assistant", "la regla definitiva es el cruce fiel"))
    assert "DECISION" in _tipos(ev)


def test_leccion_es_leccion():
    """Un cierre tipo 'Lección: ...' es LECCION."""
    ev = extraer_contexto_sesion(_sesion_con("assistant", "Lección: no inventar estados sin confirmar"))
    assert "LECCION" in _tipos(ev)


def test_usuario_rechazo_es_decision():
    """El asistente registra el rechazo del usuario como DECISION."""
    ev = extraer_contexto_sesion(_sesion_con("assistant", "el usuario rechazó el estado 'Asignado'"))
    assert "DECISION" in _tipos(ev)


def test_mensaje_normal_sigue_siendo_idea():
    """Un mensaje de implementación sin cierre sigue siendo IDEA."""
    ev = extraer_contexto_sesion(_sesion_con("assistant", "vamos a implementar el nuevo endpoint"))
    assert "IDEA" in _tipos(ev)


def test_sesion_es_del_proyecto_con_alias(tmp_path):
    """Verifica que los alias permitan asociar sesiones huérfanas por renombre."""
    from context_map.infrastructure.integrations.hermes import sesion_es_del_proyecto
    import json

    s_huerfana = Sesion(
        id="s_old",
        titulo="Revisión de arquitectura y pruebas",
        fecha_inicio="2026-08-01",
        cwd="C:/Users/jose.cespedes/Desktop/PruebaContext",
    )

    # 1. Sin alias no coincide si el proyecto es ContextMap
    assert not sesion_es_del_proyecto(s_huerfana, proyecto="ContextMap", ruta_raiz=str(tmp_path / "ContextMap"))

    # 2. Con alias explícito coincide
    assert sesion_es_del_proyecto(s_huerfana, proyecto="ContextMap", alias=["PruebaContext"])

    # 3. Con alias en .context-map/config.json coincide automáticamente
    proy_dir = tmp_path / "ContextMap"
    cfg_dir = proy_dir / ".context-map"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "config.json").write_text(json.dumps({"alias": ["PruebaContext"]}), encoding="utf-8")

    assert sesion_es_del_proyecto(s_huerfana, proyecto="ContextMap", ruta_raiz=str(proy_dir))

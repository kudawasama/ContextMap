"""Pruebas del motor de decisiones tipadas y del panel de clasificación.

Fijan el contrato que reemplaza al «gana el primer patrón»: probabilidades
normalizadas, confianza calibrada, desempate histórico, anti-señales,
detección de ambigüedad y determinismo.
"""

from __future__ import annotations

import pytest

from context_map.core.decisiones import (
    Decision,
    MotorLexicoCalibrado,
    Pregunta,
    Senal,
    confianza_calibrada,
    entropia_normalizada,
    softmax,
)
from context_map.core.models import Node
from context_map.core.normalization.paneles import (
    TAG_REVISION,
    decidir_tipo,
    evaluar,
)
from context_map.core.normalization.standardize import estandarizar_nodo

MOTOR = MotorLexicoCalibrado()


def _pregunta_ab(nombre: str = "ab") -> Pregunta:
    """Pregunta mínima de dos etiquetas para aislar el comportamiento del motor."""
    return Pregunta(
        nombre=nombre,
        tipo="choice",
        instrucciones="¿A o B?",
        etiquetas=("A", "B"),
        senales=(
            Senal.literal("bueno", "A", peso=1.0),
            Senal.literal("malo", "B", peso=-1.0),
        ),
    )


# --------------------------------------------------------------------------- #
# Aritmética del motor
# --------------------------------------------------------------------------- #


def test_softmax_suma_uno_y_es_uniforme_sin_evidencia() -> None:
    """Sin evidencia (puntuaciones iguales) el motor no inventa seguridad."""
    probabilidades = softmax([0.0, 0.0, 0.0])
    assert abs(sum(probabilidades) - 1.0) < 1e-9
    assert len(set(probabilidades)) == 1


def test_confianza_cero_con_distribucion_uniforme() -> None:
    """Una distribución uniforme significa confianza nula."""
    assert confianza_calibrada([0.5, 0.5]) == pytest.approx(0.0)
    assert confianza_calibrada([0.25, 0.25, 0.25, 0.25]) == pytest.approx(0.0)


def test_confianza_uno_con_distribucion_degenerada() -> None:
    """Concentrar toda la probabilidad en una etiqueta da confianza máxima."""
    assert confianza_calibrada([1.0, 0.0]) == pytest.approx(1.0)


def test_entropia_normalizada_va_de_certeza_a_desorden() -> None:
    """La entropía es complementaria a la confianza."""
    assert entropia_normalizada([1.0, 0.0]) == pytest.approx(0.0)
    assert entropia_normalizada([0.5, 0.5]) == pytest.approx(1.0)


def test_senal_negativa_reduce_probabilidad_de_su_etiqueta() -> None:
    """Una anti-señal resta evidencia en lugar de sumarla."""
    decision = MOTOR.decidir("esto es malo", _pregunta_ab())
    assert decision.distribucion.probabilidad("B") < decision.distribucion.probabilidad("A")
    assert decision.eleccion == "A"


def test_regla_dura_no_requiere_revision() -> None:
    """Una regla determinista no entra en la cola de revisión."""
    decision = Decision.por_regla_dura("tipo_nodo", "CORRECCION", ("IDEA", "CORRECCION"), "git fix")
    assert decision.confianza == pytest.approx(1.0)
    assert decision.requiere_revision() is False
    assert decision.en_conflicto() is False


def test_pregunta_rechaza_senal_de_etiqueta_desconocida() -> None:
    """Una señal mal cableada falla al construir la pregunta, no en silencio."""
    with pytest.raises(ValueError):
        Pregunta(
            nombre="rota",
            tipo="choice",
            instrucciones="¿?",
            etiquetas=("A", "B"),
            senales=(Senal.literal("x", "C"),),
        )


def test_pregunta_noul_exige_dos_etiquetas() -> None:
    """La primitiva noul es booleana por definición."""
    with pytest.raises(ValueError):
        Pregunta(nombre="n", tipo="noul", instrucciones="¿?", etiquetas=("a", "b", "c"))


def test_score_devuelve_puntuacion_ponderada() -> None:
    """La primitiva score resume la escala en un número."""
    pregunta = Pregunta(
        nombre="complejidad",
        tipo="score",
        instrucciones="¿Cuánta complejidad tiene?",
        etiquetas=("baja", "media", "alta"),
        senales=(Senal.literal("alta", "alta", peso=1.0),),
    )
    decision = MOTOR.decidir("complejidad alta", pregunta)
    assert decision.puntuacion is not None
    assert decision.puntuacion > 1.0
    assert decision.eleccion == "alta"


def test_decidir_panel_responde_varias_preguntas() -> None:
    """El panel responde preguntas independientes sobre el mismo estado."""
    decisiones = MOTOR.decidir_panel("bueno", (_pregunta_ab("p1"), _pregunta_ab("p2")))
    assert set(decisiones) == {"p1", "p2"}
    assert all(d.eleccion == "A" for d in decisiones.values())


# --------------------------------------------------------------------------- #
# Panel real de ContextMap
# --------------------------------------------------------------------------- #


def test_decidir_tipo_elige_por_evidencia_no_por_orden() -> None:
    """CORRECCION gana aunque IDEA se evalúe primero, si no hay evidencia de IDEA."""
    assert decidir_tipo("fix del parser de fechas").eleccion == "CORRECCION"


def test_desempate_respeta_orden_historico() -> None:
    """Con evidencia idéntica gana la etiqueta que ganaba antes (IDEA primero)."""
    decision = decidir_tipo("feature nueva con fix aplicado")
    assert decision.eleccion == "IDEA"
    assert decision.margen == pytest.approx(0.0, abs=1e-6)


def test_ambiguedad_real_se_marca_como_conflicto() -> None:
    """Dos etiquetas con evidencia comparable se marcan para revisión humana."""
    decision = decidir_tipo("feature nueva con fix aplicado")
    assert decision.en_conflicto() is True
    assert decision.requiere_revision() is True
    etiquetas_con_evidencia = {ev.etiqueta for ev in decision.evidencias}
    assert {"IDEA", "CORRECCION"} <= etiquetas_con_evidencia


def test_anti_senal_todo_en_minusculas_no_es_futuro() -> None:
    """La prosa en español con «todo» no debe clasificar como pendiente."""
    assert decidir_tipo("revisa todo el rango de fechas").eleccion != "FUTURO"
    assert decidir_tipo("TODO: unificar el descubrimiento").eleccion == "FUTURO"


def test_decision_es_determinista() -> None:
    """El mismo texto produce siempre la misma decisión (build reproducible)."""
    primera = decidir_tipo("release milestone v2")
    segunda = decidir_tipo("release milestone v2")
    assert primera == segunda
    assert primera.eleccion == "HITO"


def test_explicar_es_legible() -> None:
    """La decisión puede auditarse en una línea."""
    assert "CORRECCION" in decidir_tipo("fix del parser").explicar()


def test_evaluar_responde_las_tres_preguntas() -> None:
    """El panel expone tipo, clasificación y concepto de una sola pasada."""
    decisiones = evaluar("migración de base de datos sql")
    assert set(decisiones) == {"tipo", "clasificacion", "concepto"}
    assert decisiones["concepto"].eleccion == "BASEDEDATOS"


# --------------------------------------------------------------------------- #
# Integración en el pipeline
# --------------------------------------------------------------------------- #


def test_estandarizar_nodo_marca_conflicto_para_revision() -> None:
    """La ambigüedad de tipo queda visible como etiqueta del vault."""
    nodo = estandarizar_nodo(
        Node(id="IDEA-99", type="IDEA", title="feature nueva con fix aplicado")
    )
    assert TAG_REVISION in nodo.tags


def test_estandarizar_nodo_sin_conflicto_no_marca_revision() -> None:
    """Un caso claro no ensucia la cola de revisión."""
    nodo = estandarizar_nodo(
        Node(id="CORRECCION-99", type="CORRECCION", title="Corregir bug en la serialización JSON")
    )
    assert TAG_REVISION not in nodo.tags

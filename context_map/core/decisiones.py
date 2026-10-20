"""Motor de decisiones tipadas inspirado en los *System One Models* (Jev).

Contexto del diseño
-------------------
La clasificación histórica de ContextMap resolvía cada caso con *listas de
patrones y «gana el primero que coincide»*. Ese esquema es rápido pero frágil:

1. **Evidencia ignorada**: un patrón débil anula a uno fuerte («feature: fix del
   parser» → IDEA, porque ``feature`` se evalúa antes que ``fix``).
2. **Sin confianza**: un acierto al 51 % y uno al 99 % son indistinguibles, así
   que el error no se puede priorizar ni auditar.
3. **Sin traza**: no hay forma de explicar por qué un nodo cambió de tipo.

Este módulo introduce una capa de decisión **determinista, calibrada y
auditable**, tomando como referencia los *System One Models* (Jev, TypeSafe AI):
en lugar de generar texto, se recibe un **estado** y se responden **preguntas
tipadas** (``noul``, ``choice``, ``score``) devolviendo una **distribución de
probabilidad**, una **confianza calibrada** y las **evidencias** que la
sustentan. Todas las preguntas de un panel se responden en una sola pasada
sobre el mismo estado, reutilizando las coincidencias léxicas.

Diferencias deliberadas frente a Jev
------------------------------------
* Aquí el motor es **local y determinista** (sin red ni coste): ContextMap debe
  funcionar offline y reproducir builds byte a byte.
* No se "aprende": los pesos son explícitos y versionables en el repositorio, de
  modo que un cambio de clasificación es un cambio revisable en un diff.
* La confianza usa la misma definición que el modelo de referencia, para que un
  futuro adaptador remoto (Jev real) sea intercambiable sin tocar a los
  consumidores::

    confianza = (p_max - 1/n) / (1 - 1/n)

Uso típico::

    from context_map.core.decisiones import MotorLexicoCalibrado, Pregunta, Senal

    pregunta = Pregunta(
        nombre="tipo",
        tipo="choice",
        instrucciones="¿Qué tipo de evento es?",
        etiquetas=("IDEA", "CORRECCION"),
        senales=(
            Senal.literal("fix", "CORRECCION", peso=1.0),
            Senal.literal("feature", "IDEA", peso=1.0),
        ),
    )
    decision = MotorLexicoCalibrado().decidir("fix del parser", pregunta)
    decision.eleccion  # 'CORRECCION'
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

#: Primitivas de pregunta soportadas por el motor (equivalentes a las de Jev).
TipoPregunta = Literal["noul", "choice", "score"]

#: Etiquetas canónicas de una pregunta booleana (``noul``).
ETIQUETAS_NOUL: tuple[str, str] = ("true", "false")


def softmax(puntuaciones: Sequence[float], temperatura: float = 1.0) -> tuple[float, ...]:
    """Convierte puntuaciones de evidencia en una distribución de probabilidad.

    Una puntuación constante para todas las etiquetas (es decir, ausencia de
    evidencia) produce una distribución **uniforme**: el motor nunca inventa
    seguridad cuando no la tiene.

    Args:
        puntuaciones (Sequence[float]): Puntuación acumulada por etiqueta.
        temperatura (float): A mayor temperatura, distribución más plana.

    Returns:
        tuple[float, ...]: Probabilidades que suman 1.

    Raises:
        ValueError: Si ``puntuaciones`` está vacío o la temperatura no es > 0.
    """
    if not puntuaciones:
        raise ValueError("softmax requiere al menos una puntuación")
    if temperatura <= 0:
        raise ValueError("la temperatura debe ser mayor que cero")

    maximo = max(puntuaciones)
    exponenciales = [math.exp((p - maximo) / temperatura) for p in puntuaciones]
    total = sum(exponenciales)
    return tuple(e / total for e in exponenciales)


def confianza_calibrada(probabilidades: Sequence[float]) -> float:
    """Calcula la confianza como concentración de la distribución.

    Reproduce la definición del modelo de referencia: vale 0 cuando la
    distribución es uniforme (no hay información) y 1 cuando una etiqueta
    concentra toda la probabilidad.

    Args:
        probabilidades (Sequence[float]): Distribución de probabilidad.

    Returns:
        float: Confianza en el rango ``[0, 1]``.
    """
    n = len(probabilidades)
    if n <= 1:
        return 1.0
    p_max = max(probabilidades)
    return max(0.0, (p_max - 1 / n) / (1 - 1 / n))


def entropia_normalizada(probabilidades: Sequence[float]) -> float:
    """Calcula la entropía de Shannon normalizada al rango ``[0, 1]``.

    Sirve como segunda lectura de la incertidumbre: 0 = certeza total,
    1 = máximo desorden entre las etiquetas ofrecidas.

    Args:
        probabilidades (Sequence[float]): Distribución de probabilidad.

    Returns:
        float: Entropía normalizada.
    """
    n = len(probabilidades)
    if n <= 1:
        return 0.0
    entropia = -sum(p * math.log(p) for p in probabilidades if p > 0)
    return entropia / math.log(n)


@dataclass(frozen=True)
class Senal:
    """Patrón léxico ponderado que aporta evidencia a favor (o en contra) de una etiqueta.

    Un peso negativo es una **anti-señal**: documenta un falso amigo conocido
    (por ejemplo ``todo`` en minúsculas dentro de prosa en español) y resta
    evidencia en lugar de sumarla.

    Attributes:
        etiqueta (str): Etiqueta que recibe la evidencia.
        patron (re.Pattern[str]): Expresión compilada que se busca en el estado.
        peso (float): Aporte por coincidencia; negativo para anti-señales.
        descripcion (str): Texto legible para explicar la decisión.
    """

    etiqueta: str
    patron: re.Pattern[str]
    peso: float = 1.0
    descripcion: str = ""

    @classmethod
    def literal(
        cls,
        texto: str,
        etiqueta: str,
        peso: float = 1.0,
        descripcion: str = "",
        ignorar_caso: bool = True,
        palabra_completa: bool = False,
    ) -> Senal:
        """Construye una señal a partir de un texto literal.

        Args:
            texto (str): Palabra o frase a buscar.
            etiqueta (str): Etiqueta favorecida.
            peso (float): Aporte por coincidencia.
            descripcion (str): Descripción legible (por defecto «texto»).
            ignorar_caso (bool): Si es ``False`` la búsqueda distingue mayúsculas.
            palabra_completa (bool): Si es ``True`` exige límites de palabra.

        Returns:
            Senal: Señal compilada.
        """
        cuerpo = re.escape(texto)
        if palabra_completa:
            cuerpo = rf"(?<!\w){cuerpo}(?!\w)"
        flags = re.IGNORECASE if ignorar_caso else 0
        return cls(etiqueta, re.compile(cuerpo, flags), peso, descripcion or f"«{texto}»")

    @classmethod
    def expresion(
        cls,
        patron: str,
        etiqueta: str,
        peso: float = 1.0,
        descripcion: str = "",
        ignorar_caso: bool = True,
    ) -> Senal:
        """Construye una señal a partir de una expresión regular.

        Args:
            patron (str): Expresión regular.
            etiqueta (str): Etiqueta favorecida.
            peso (float): Aporte por coincidencia.
            descripcion (str): Descripción legible (por defecto el patrón).
            ignorar_caso (bool): Si es ``False`` la búsqueda distingue mayúsculas.

        Returns:
            Senal: Señal compilada.
        """
        flags = re.IGNORECASE if ignorar_caso else 0
        return cls(etiqueta, re.compile(patron, flags), peso, descripcion or patron)

    def contar(self, texto: str) -> int:
        """Cuenta las coincidencias de la señal en el texto.

        Args:
            texto (str): Estado a evaluar (ya en forma de cadena).

        Returns:
            int: Número de coincidencias.
        """
        return len(self.patron.findall(texto))


@dataclass(frozen=True)
class Evidencia:
    """Traza de una señal que efectivamente coincidió en el estado evaluado.

    Attributes:
        etiqueta (str): Etiqueta que recibió la evidencia.
        descripcion (str): Explicación legible de la señal.
        peso (float): Peso unitario de la señal.
        coincidencias (int): Número de coincidencias encontradas.
    """

    etiqueta: str
    descripcion: str
    peso: float
    coincidencias: int

    @property
    def aporte(self) -> float:
        """Aporte total de la señal (peso × coincidencias)."""
        return self.peso * self.coincidencias

    def __str__(self) -> str:
        signo = "-" if self.aporte < 0 else "+"
        return f"{signo}{abs(self.aporte):.2f} {self.etiqueta}: {self.descripcion}"


@dataclass(frozen=True)
class Pregunta:
    """Pregunta tipada con sus etiquetas candidatas y señales de evidencia.

    Attributes:
        nombre (str): Identificador de la pregunta (clave en el panel).
        tipo (TipoPregunta): ``noul`` (sí/no), ``choice`` (categorías) o
            ``score`` (escala ordenada).
        instrucciones (str): Enunciado de la pregunta.
        etiquetas (tuple[str, ...]): Candidatas en orden de desempate; el
            primero gana si hay empate exacto (preserva la precedencia histórica).
        senales (tuple[Senal, ...]): Evidencia léxica ponderada.
        temperatura (float): Suavizado del ``softmax``.
    """

    nombre: str
    tipo: TipoPregunta
    instrucciones: str
    etiquetas: tuple[str, ...]
    senales: tuple[Senal, ...] = ()
    temperatura: float = 1.0

    def __post_init__(self) -> None:
        etiquetas = tuple(self.etiquetas)
        if not etiquetas:
            raise ValueError(f"la pregunta '{self.nombre}' necesita al menos una etiqueta")
        if len(set(etiquetas)) != len(etiquetas):
            raise ValueError(f"la pregunta '{self.nombre}' tiene etiquetas duplicadas")
        if self.tipo == "noul" and len(etiquetas) != 2:
            raise ValueError("una pregunta 'noul' debe ofrecer exactamente dos etiquetas")
        if self.tipo == "score" and len(etiquetas) < 2:
            raise ValueError("una pregunta 'score' necesita al menos dos niveles")
        for senal in self.senales:
            if senal.etiqueta not in etiquetas:
                raise ValueError(
                    f"la señal '{senal.descripcion}' apunta a '{senal.etiqueta}', "
                    f"que no es una etiqueta de '{self.nombre}'"
                )
        if self.temperatura <= 0:
            raise ValueError(f"la temperatura de '{self.nombre}' debe ser mayor que cero")
        object.__setattr__(self, "etiquetas", etiquetas)
        object.__setattr__(self, "senales", tuple(self.senales))


@dataclass(frozen=True)
class Distribucion:
    """Distribución de probabilidad sobre las etiquetas de una pregunta.

    Attributes:
        etiquetas (tuple[str, ...]): Etiquetas evaluadas, en orden.
        probabilidades (tuple[float, ...]): Probabilidad de cada etiqueta.
    """

    etiquetas: tuple[str, ...]
    probabilidades: tuple[float, ...]

    @classmethod
    def uniforme(cls, etiquetas: Sequence[str]) -> Distribucion:
        """Distribución uniforme: el resultado de «no tengo evidencia».

        Args:
            etiquetas (Sequence[str]): Etiquetas candidatas.

        Returns:
            Distribucion: Distribución con la misma probabilidad para todas.
        """
        n = len(etiquetas)
        return cls(tuple(etiquetas), tuple(1 / n for _ in range(n)))

    @property
    def modo(self) -> str:
        """Etiqueta más probable (gana la primera en caso de empate)."""
        return self.etiquetas[max(range(len(self.probabilidades)), key=self.probabilidades.__getitem__)]

    @property
    def confianza(self) -> float:
        """Confianza calibrada de la distribución."""
        return confianza_calibrada(self.probabilidades)

    @property
    def margen(self) -> float:
        """Diferencia entre la probabilidad ganadora y la siguiente."""
        ordenadas = sorted(self.probabilidades, reverse=True)
        if len(ordenadas) < 2:
            return 1.0
        return ordenadas[0] - ordenadas[1]

    @property
    def entropia(self) -> float:
        """Entropía normalizada de la distribución."""
        return entropia_normalizada(self.probabilidades)

    def probabilidad(self, etiqueta: str) -> float:
        """Devuelve la probabilidad de una etiqueta concreta.

        Args:
            etiqueta (str): Etiqueta consultada.

        Returns:
            float: Probabilidad asociada, ``0.0`` si no existe.
        """
        if etiqueta not in self.etiquetas:
            return 0.0
        return self.probabilidades[self.etiquetas.index(etiqueta)]

    def as_dict(self) -> dict[str, float]:
        """Serializa la distribución como diccionario etiqueta → probabilidad."""
        return {
            etiqueta: round(p, 6)
            for etiqueta, p in zip(self.etiquetas, self.probabilidades, strict=True)
        }


@dataclass(frozen=True)
class Decision:
    """Respuesta tipada a una pregunta, con su traza de evidencias.

    Attributes:
        pregunta (str): Nombre de la pregunta respondida.
        tipo (TipoPregunta): Primitiva utilizada.
        instrucciones (str): Enunciado original.
        distribucion (Distribucion): Distribución completa de probabilidad.
        evidencias (tuple[Evidencia, ...]): Señales que coincidieron.
        puntuacion (float | None): Media ponderada del índice de nivel para
            preguntas ``score``; ``None`` en los demás casos.
        por_regla (bool): ``True`` si la etiqueta vino de una regla dura
            (Conventional Commits, prefijos) y no del motor de evidencia.
        motivo (str): Explicación legible del origen de la decisión.
    """

    pregunta: str
    tipo: TipoPregunta
    instrucciones: str
    distribucion: Distribucion
    evidencias: tuple[Evidencia, ...] = ()
    puntuacion: float | None = None
    por_regla: bool = False
    motivo: str = ""

    @classmethod
    def por_regla_dura(cls, pregunta: str, etiqueta: str, etiquetas: Sequence[str], motivo: str) -> Decision:
        """Construye una decisión de confianza total tomada por una regla dura.

        Se usa cuando una regla determinista (por ejemplo un prefijo
        *Conventional Commits*) decide sin ambigüedad y el motor léxico no debe
        poder revocarla.

        Args:
            pregunta (str): Nombre de la pregunta.
            etiqueta (str): Etiqueta decidida.
            etiquetas (Sequence[str]): Universo de etiquetas de la pregunta.
            motivo (str): Explicación legible.

        Returns:
            Decision: Decisión con confianza 1.0.
        """
        universo = tuple(etiquetas)
        if etiqueta not in universo:
            universo = (etiqueta, *universo)
        probabilidades = tuple(1.0 if e == etiqueta else 0.0 for e in universo)
        return cls(
            pregunta=pregunta,
            tipo="choice",
            instrucciones="Decisión por regla determinista",
            distribucion=Distribucion(universo, probabilidades),
            evidencias=(Evidencia(etiqueta, motivo, 1.0, 1),),
            por_regla=True,
            motivo=motivo,
        )

    @property
    def etiqueta(self) -> str:
        """Etiqueta decidida (alias explícito de ``eleccion``)."""
        return self.distribucion.modo

    @property
    def eleccion(self) -> str:
        """Etiqueta decidida: la más probable de la distribución."""
        return self.distribucion.modo

    @property
    def confianza(self) -> float:
        """Confianza calibrada de la decisión."""
        return self.distribucion.confianza

    @property
    def margen(self) -> float:
        """Margen entre la primera y la segunda etiqueta."""
        return self.distribucion.margen

    @property
    def entropia(self) -> float:
        """Entropía normalizada de la decisión."""
        return self.distribucion.entropia

    def requiere_revision(self, umbral: float = 0.6) -> bool:
        """Indica si la decisión es demasiado insegura para darla por buena.

        Args:
            umbral (float): Confianza mínima aceptable.

        Returns:
            bool: ``True`` si la confianza está por debajo del umbral.
        """
        if self.por_regla:
            return False
        return self.confianza < umbral

    def en_conflicto(self, margen: float = 0.15) -> bool:
        """Indica si hay evidencia real a favor de dos etiquetas distintas.

        Es el criterio usado para enviar un nodo a la **cola de revisión**: no
        basta con que el resultado sea poco probable, debe existir un empate
        técnico que un humano pueda resolver.

        Args:
            margen (float): Margen máximo entre las dos primeras etiquetas.

        Returns:
            bool: ``True`` si dos etiquetas reciben evidencia y el margen es bajo.
        """
        if self.por_regla:
            return False
        etiquetas_con_evidencia = {ev.etiqueta for ev in self.evidencias if ev.aporte > 0}
        return self.margen < margen and len(etiquetas_con_evidencia) > 1

    def explicar(self) -> str:
        """Redacta una explicación legible de la decisión.

        Returns:
            str: Texto de una línea con etiqueta, confianza y evidencias.
        """
        if self.motivo:
            return f"{self.pregunta}={self.eleccion} (confianza 1.00, {self.motivo})"
        detalles = ", ".join(str(ev) for ev in self.evidencias) or "sin evidencia léxica"
        return (
            f"{self.pregunta}={self.eleccion} "
            f"(confianza {self.confianza:.2f}, margen {self.margen:.2f}): {detalles}"
        )

    def as_dict(self) -> dict[str, object]:
        """Serializa la decisión a un diccionario apto para JSON/reportes."""
        return {
            "pregunta": self.pregunta,
            "tipo": self.tipo,
            "eleccion": self.eleccion,
            "confianza": round(self.confianza, 6),
            "margen": round(self.margen, 6),
            "entropia": round(self.entropia, 6),
            "puntuacion": None if self.puntuacion is None else round(self.puntuacion, 6),
            "por_regla": self.por_regla,
            "distribucion": self.distribucion.as_dict(),
            "evidencias": [
                {
                    "etiqueta": ev.etiqueta,
                    "descripcion": ev.descripcion,
                    "aporte": round(ev.aporte, 6),
                }
                for ev in self.evidencias
            ],
        }


class MotorLexicoCalibrado:
    """Motor de decisiones local, determinista y explicable.

    Reemplaza el «gana el primer patrón» por evidencia ponderada + ``softmax`` +
    confianza calibrada. No usa red ni modelos: el mismo estado produce siempre
    la misma distribución, lo que mantiene los builds reproducibles.

    Attributes:
        umbral_revision (float): Confianza mínima para no marcar revisión.
        margen_conflicto (float): Margen por debajo del cual hay empate técnico.
    """

    nombre = "lexico-calibrado"

    def __init__(self, umbral_revision: float = 0.6, margen_conflicto: float = 0.15) -> None:
        self.umbral_revision = umbral_revision
        self.margen_conflicto = margen_conflicto

    def decidir(self, estado: str, pregunta: Pregunta) -> Decision:
        """Responde una pregunta tipada sobre un estado textual.

        Args:
            estado (str): Texto o serialización del estado a evaluar.
            pregunta (Pregunta): Pregunta tipada con sus señales.

        Returns:
            Decision: Distribución, etiqueta ganadora, confianza y evidencias.
        """
        texto = estado or ""
        puntuaciones = [0.0] * len(pregunta.etiquetas)
        evidencias: list[Evidencia] = []

        for senal in pregunta.senales:
            coincidencias = senal.contar(texto)
            if not coincidencias:
                continue
            indice = pregunta.etiquetas.index(senal.etiqueta)
            puntuaciones[indice] += senal.peso * coincidencias
            evidencias.append(
                Evidencia(senal.etiqueta, senal.descripcion, senal.peso, coincidencias)
            )

        probabilidades = softmax(puntuaciones, pregunta.temperatura)
        distribucion = Distribucion(pregunta.etiquetas, probabilidades)
        puntuacion = None
        if pregunta.tipo == "score":
            puntuacion = sum(i * p for i, p in enumerate(probabilidades))

        return Decision(
            pregunta=pregunta.nombre,
            tipo=pregunta.tipo,
            instrucciones=pregunta.instrucciones,
            distribucion=distribucion,
            evidencias=tuple(sorted(evidencias, key=lambda e: -abs(e.aporte))),
            puntuacion=puntuacion,
        )

    def decidir_panel(self, estado: str, preguntas: Sequence[Pregunta]) -> dict[str, Decision]:
        """Responde todas las preguntas de un panel en una sola pasada.

        Igual que los *System One Models*, las preguntas de un panel son
        independientes y se resuelven juntas: el coste marginal de añadir una
        pregunta es solo el de sus propios patrones.

        Args:
            estado (str): Estado compartido.
            preguntas (Sequence[Pregunta]): Panel de preguntas independientes.

        Returns:
            dict[str, Decision]: Decisión indexada por nombre de pregunta.
        """
        return {pregunta.nombre: self.decidir(estado, pregunta) for pregunta in preguntas}

    def decidir_varias(self, estados: Iterable[str], pregunta: Pregunta) -> list[Decision]:
        """Aplica *map-reduce* sobre muchos estados con la misma pregunta.

        Args:
            estados (Iterable[str]): Estados a evaluar.
            pregunta (Pregunta): Pregunta común.

        Returns:
            list[Decision]: Una decisión por estado, en el mismo orden.
        """
        return [self.decidir(estado, pregunta) for estado in estados]


#: Motor por defecto del proyecto (stateless, seguro de compartir).
MOTOR_POR_DEFECTO = MotorLexicoCalibrado()

__all__ = [
    "TipoPregunta",
    "ETIQUETAS_NOUL",
    "MotorLexicoCalibrado",
    "MOTOR_POR_DEFECTO",
    "Senal",
    "Evidencia",
    "Pregunta",
    "Distribucion",
    "Decision",
    "softmax",
    "confianza_calibrada",
    "entropia_normalizada",
]

# Jev (TypeSafe AI) — qué es, pros, contras y por qué ContextMap no depende de él

> Investigación realizada el **2026-10-13**. Fuentes al final.
> Plan asociado: `docs/plans/PLAN-CLASIFICACION-CALIBRADA-2026-10-13.md`.

## 1. Qué es

**Jev** es un modelo de IA **discriminativo** (clasificación/regresión), no
generativo: **no escribe texto**. Lo desarrolla **TypeSafe AI** (San Francisco,
fundada en 2024 por Diogo Almeida —ex-OpenAI, RLHF/InstructGPT/ChatGPT/GPT-4—,
Erik Gafni y Sasha Sheng) y se publicó en *early access* el **15 de septiembre de
2026**, junto a una ronda semilla de **US$40 M** liderada por DCVC. Desarrollo en
*stealth* durante ~2 años.

TypeSafe lo presenta como el primer **System One Model**: modelos hechos para
tomar **decisiones rápidas y estructuradas que el software consume directamente**
(nombre tomado de la dicotomía de Kahneman entre pensar rápido y pensar despacio).
El nombre «Jev» viene de **William Stanley Jevons** (paradoja de Jevons: más
eficiencia → más consumo; la apuesta de que la inteligencia barata se despliega
mucho más).

## 2. Cómo funciona

| Aspecto | Detalle |
|---|---|
| Entrada | `state` (string, objeto JSON o array de strings; atributos referenciables) + `questions` |
| Límite de entrada | 64k tokens (32k de estado + la pregunta más larga) |
| Primitivas | **`noul`** (sí/no → P(verdadero)), **`choice`** (lista desordenada), **`score`** (escala ordenada) |
| Salida | **Una distribución de probabilidad por pregunta**, todas resueltas **en paralelo** en una sola pasada |
| Confianza | `confidence = (p_max − 1/n) / (1 − 1/n)`; 0 si es uniforme, 1 si es certeza |
| Cardinalidad | hasta 255 opciones por pregunta |
| Dependencias | ninguna entre preguntas (paralelas): si una depende de otra, hacen falta 2 requests |
| Entrenamiento | **RLCD** (*Reinforcement Learning for Calibrated Decisions*), **datos 100 % sintéticos** |
| Arquitectura | no publicada (descrita como transformer; observadores sugieren base BERT/open-weight). Sin paper |
| Rendimiento | 70–500 ms; 40–200× más rápido y 40–400× más barato que LLMs frontier en tareas «System One» |
| Precio | **$0.042 / millón** de tokens de entrada; **salida gratis** |
| Garantía | **0 errores de tipo**: el esquema se define antes → no puede alucinar estructura |

Idea central de la compañía: los LLM llevan años siendo superiores en *chat*
pero no en **automatizar**; optimizar para lenguaje humano no sirve para
software. Jev se posiciona como «una llamada a función de inteligencia frontier:
estado no estructurado entra, decisiones probabilísticas tipadas salen».

## 3. Pros

1. **No puede alucinar la forma**: la salida está tipada de antemano, así que se
   puede encadenar en código con garantías de latencia.
2. **Confianza calibrada real**: es lo más diferencial — permite decidir *cuándo
   automatizar* y *cuándo escalar a un humano*, con un número comparable.
3. **Coste y latencia de producción**: 70–500 ms y un precio dos órdenes de
   magnitud menor; usar IA en el camino crítico de la UX deja de ser inviable.
4. **N preguntas en 1 llamada**: responder 10 preguntas cuesta casi lo mismo que
   una, porque el muestreo es paralelo.
5. **Complementa al LLM** en vez de competir: *routing* de modelos, *guardrails*,
   verificación de trazas de agente y detección de *jailbreaks* a bajo coste.
6. **Evidencia de campo**: Vercel pasó de Luna 5.6 a Jev para clasificar comandos
   peligrosos → **5–18× más rápido y más preciso**; Bryo AI comparó con Gemini en
   clasificar correos: algo menos preciso pero **10–20× más barato**, y valoró
   explícitamente «devuelve una probabilidad real».
7. **Componible**: «if-statements borrosos» donde la lógica escrita a mano es
   demasiado frágil.

## 4. Contras

1. **No genera texto ni razona abierto**: no sustituye a un LLM, solo cubre
   decisiones acotadas.
2. **Opacidad**: arquitectura, pesos, datos y algoritmo sin publicar; sin paper
   ni benchmark público independiente.
3. **Evals propias y sesgadas**: los *workflows* de la evaluación los hicieron
   miembros de su equipo de capacidades y la referencia es la media de GPT-6
   Astra y Fable 5.1 (lo reconocen como sesgo hacia OpenAI/Anthropic).
4. **Datos sintéticos**: cobertura de dominios raros/industriales incierta.
5. **Delega el problema al usuario**: «si vuelve con 50 %, quizá es una moneda al
   aire, lo ignoro; si es 95 %, actúo» (Armin Ronacher, Earendil). Sin umbrales
   bien diseñados, la calibración no aporta nada.
6. **Preguntas independientes**: cualquier flujo con lógica encadenada exige
   varias llamadas (más latencia y más código).
7. **Sostenibilidad del precio sin probar**: ellos mismos admiten que no pueden
   demostrar que el precio no esté subvencionado.
8. **Coste humano oculto**: hay que descomponer el problema en muchas preguntas
   independientes y finas; eso es ingeniería de dominio real.

## 5. Por qué ContextMap NO depende de Jev

Es la restricción que gobierna el plan de implementación:

1. **No es usable hoy**: *early access* con lista de espera, propietario y
   requiere `TYPESAFE_API_KEY`.
2. **ContextMap debe funcionar offline y reproducir builds byte a byte**: un
   modelo remoto rompería el determinismo del vault.
3. **Coste y autorización**: la política del proyecto prohíbe generar coste sin
   autorización explícita.

Por eso ContextMap **replica el patrón, no el proveedor**:

| Patrón de Jev | Réplica local en ContextMap |
|---|---|
| Preguntas tipadas `noul` / `choice` / `score` | `core/decisiones.py` con la misma taxonomía |
| Distribuciones de probabilidad en paralelo | `MotorLexicoCalibrado.decidir_panel()` (una pasada, `lru_cache`) |
| Confianza calibrada `(p_max − 1/n)/(1 − 1/n)` | `confianza_calibrada()`, idéntica fórmula |
| 0 errores de tipo | `Decision` es un dataclass frozen: la salida siempre es válida |
| Evidencias / explicabilidad | `Decision.explicar()` y `as_dict()` |
| Umbral → decidir o escalar | `requiere_revision()` y `en_conflicto()` → cola `revision:clasificacion` |

El contrato público `decidir(estado, pregunta) -> Decision` es el mismo, así que
si algún día hay acceso, un `MotorJevRemoto` es un cambio **aditivo** con
*fallback* al motor local (Fase 5 del plan, hoy bloqueada).

## Fuentes

- Wikipedia: *Jev (AI model)* — https://en.wikipedia.org/wiki/Jev_(AI_model)
- TypeSafe AI: *Introducing System One Models & Jev* — https://typesafe.ai/blog/introducing-system-one-models-and-jev
- TechCrunch (18-sep-2026): *A new kind of AI model from a ChatGPT inventor is thrilling developers*
- Forbes (15-sep-2026): *This $200 Million Startup Wants To Fix AI's Overconfidence Problem*
- LangChain (17-sep-2026): *Building a Harness with Jev*
- The Register (16-sep-2026): *TypeSafe AI debuts model for machines that plays Doom*

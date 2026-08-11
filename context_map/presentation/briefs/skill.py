"""Generador de la skill de ContextMap dentro de .context-map/.

Contiene el CÓMO: comandos exactos, metodología narrativa para escribir las
notas dándole vida, zona protegida y topología. El AGENTS.md solo dice QUÉ
hacer y referencia esta skill — así los detalles viven junto al contexto, no
en la raíz del proyecto.
"""

from __future__ import annotations

import os
from datetime import datetime


def generar_skill_contextmap(
    project_name: str,
    target_dir: str = ".",
) -> str:
    """Genera `.context-map/contextmap-skill.md` con el cómo trabajar el contexto.

    Args:
        project_name (str): Nombre del proyecto.
        target_dir (str): Directorio raíz del proyecto.

    Returns:
        str: Ruta del archivo generado.
    """
    safe = project_name.strip().replace(" ", "-").replace("/", "-")
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    vault = f".context-map/vault-{safe}"

    content = f"""# Skill de ContextMap — Cómo darle vida al contexto

> El `AGENTS.md` de la raíz dice QUÉ hacer; esta skill es el CÓMO:
> comandos exactos, metodología para escribir notas con alma y reglas del vault.
> Última actualización: {fecha}

---

## 🚀 Poner el contexto al día (1 paso)

```bash
ctxmap refresh .     # = scan + build (preservando manuales) + check
```

## 🧭 PONERSE EN CONTEXTO CORRECTAMENTE (protocolo de lectura obligatorio)

Antes de responder sobre el estado del proyecto (o "¿qué quedó pendiente?"),
lee EN ESTE ORDEN — el orden importa:

1. **Este brief** (`.context-map/CONTEXT.md`) — qué es, por qué existe, qué cumple.
2. **Sección "Estado del Contexto" del brief**: si avisa que el diario manual es
   más nuevo que el build → el contexto está desactualizado → ejecuta
   `ctxmap refresh .` ANTES de responder.
3. **Pendientes REALES**:
   - `.context-map/vault-{safe}/7.0-MANUAL/BACKLOG.md` (si existe) — pendientes
     conversados con el usuario, con criterios de listo.
   - `.context-map/vault-{safe}/7.0-MANUAL/Diario/` — el diario más reciente
     (lo hecho, decidido y lo que falta).
   - `5.0-BACKLOG/5.1-Tareas.md` — TODOs del código (deuda técnica).
4. **Riesgos y propósito**: `4.0-RIESGOS/` y `1.0-PROPOSITO/` antes de proponer cambios.
5. **Código real** antes de diagnosticar — nunca suponer rutas ni lógica.

> ⚠️ **Regla anti-error**: NUNCA respondas "¿qué quedó pendiente?" basándote solo
> en un documento suelto (auditoría, CHANGELOG, docs/). La fuente de verdad son
> brief + backlog manual + diario. Y verifica que estás en el proyecto correcto:
> el vault de ESTE proyecto es `{vault}/` — si el usuario pregunta por otro,
> dilo ANTES de responder.

## 🔄 Actualizar NO es solo correr el script (flujo del agente)

Cuando el usuario pida "actualiza el contexto" (o al terminar de trabajar),
NO des el output del script por bueno. Ejecuta el ciclo completo:

1. **EJECUTA**: `ctxmap refresh .` (scan + build + check).
2. **VERIFICA** el resultado (criterios de calidad):
   - `ctxmap check .` sin alertas.
   - Títulos legibles: sin `TODO (ruta.py:Ln):` crudo, sin paths aplanados
     (`context_mapcore...` — deben leerse `context_map/core/...`).
   - `1.3-Proposito` y `CONTEXT.md` SIN métricas del scanner
     ("Proyecto 'X' — N archivos, N líneas").
   - Notas SIN plantillas vacías (frases que sirven para cualquier nodo:
     "Existe la necesidad técnica de abordar 'X'..."), sin `..` dobles,
     sin ubicación duplicada.
3. **CORRIGE** los garabatos:
   - Tarea técnica (TODO del código) → tarjeta técnica honesta: qué es,
     dónde está, qué hace ese módulo, estado. NO narrativa de diseño.
   - Idea/mejora conversada → nota con alma en la zona protegida
     `{vault}/7.0-MANUAL/` (¿Qué es? ¿Por qué existe? ¿Para qué? ¿Qué
     cumple? + conexiones) con frontmatter `preserve: true`.
   - Título feo → corrígelo en el estado/nota para que se lea como humano.
4. **REGENERA Y RE-VERIFICA** si corregiste (refresh de nuevo + check).

## ✍️ HUMANIZAR TODOS LOS ARCHIVOS (regla obligatoria)

El propósito del vault es que TODOS los archivos se lean como la historia
del proyecto — no solo la zona manual. Al actualizar, revisa CADA archivo
del vault (0.0 a 7.0) y redacta lo que el scanner dejó tosco, PRESERVANDO
siempre el contexto (nunca borres información real ni notas con historia):

- **Índices (X.0)**: que digan qué hay y por qué, no solo conteos.
- **1.x**: propósito/biblia con el alma real; datos clave reales; sin métricas.
- **2.x**: ideas con narrativa honesta (10 preguntas); TODOs del scanner
  NO son ideas (filtrados) — si aparece uno, muévelo a tarjeta técnica.
- **3.x**: fundamentos reales (no "Proyecto 'X' — N archivos" repetidos).
- **4.x**: riesgos reales, deduplicados, con paths legibles y por qué importan.
- **5.x**: tareas reales con criterios de listo; sin código crudo.
- **6.x**: historia legible (mensajes de commits, no plantillas de 5 preguntas).
- **7.0-MANUAL/**: zona protegida — escribe aquí la historia conversada
  (decisiones, porqués, ideas) con `preserve: true`.

> Regla de oro: el script propone, el AGENTE dispone — y el agente humaniza
> TODO el vault, no solo 7.0-MANUAL. Guardar siempre el contexto: nada se
> borra si tiene historia; lo tosco se REDACTa, no se elimina.

## 🧠 MEMORIA VIVA DEL PROYECTO (regla fundamental)

ContextMap ES la memoria del proyecto — y la mantiene el AGENTE,
constantemente:

- **Documenta AUTOMÁTICAMENTE**: si durante el trabajo surge una idea, una
  decisión, un porqué o una lección, escríbela en el momento — no esperes a
  que te lo pidan. Memoria viva = lo conversado queda.
- **Nota del día** (`{vault}/7.0-MANUAL/Diario/<fecha>.md`): resumen de lo
  conversado y decidido hoy (qué se hizo, qué se decidió, qué falta).
- **8.0-KNOWLEDGE** (`{vault}/8.0-KNOWLEDGE/`): el APRENDIZAJE accionable.
  Cada conocimiento reutilizable se documenta con el formato fijo:
  🎯 Lección · 🛠️ Cómo se resolvió · 💬 Prompt específico · 📋 Instrucción
  específica · 🔗 Conexiones. Si una lección puede servir después, es
  KNOWLEDGE; si es solo registro del día, queda en el Diario.
- **Criterio**: si lo que conversaste podría reutilizarse (un prompt que
  funcionó, un error que costó, un procedimiento) → 8.0-KNOWLEDGE. Todo lo
  demás → nota del día. Ambas zonas con `preserve: true`.

> Regla: el script propone, el AGENTE dispone. El contexto se da por bueno
> solo cuando el agente lo revisó y lo corrigió.

## 🧰 Comandos paso a paso

```bash
# Escanear cambios del código → nodos CAMBIO/CORRECCION/IDEA
ctxmap scan .

# Regenerar vault + brief (SIN --clean: no toca el trabajo manual)
ctxmap build --brief

# Auditar readiness y salud del vault
ctxmap check .
```

## 📚 Importar la historia del proyecto (chats y conversaciones)

Las conversaciones con el usuario también son contexto: ahí viven las ideas,
decisiones y porqués. Importarlas antes de responder si el usuario comparte un
chat, y al terminar cada sesión de trabajo:

```bash
ctxmap import-git .           # historial de commits y decisiones
ctxmap import-sessions        # sesiones de Hermes Agent
ctxmap import-antigravity     # conversaciones de Antigravity IDE
ctxmap import-chat <archivo>  # chats exportados (Telegram/Discord/Slack)
ctxmap refresh .              # regenerar vault + brief con la historia
```

## 🎨 Cómo escribir las notas dándole vida (metodología narrativa)

Cada nota del vault se escribe con formato narrativo polimórfico según su tipo.
El plano PROFESIONAL completo tiene dos capas: **identidad/decisión** y
**gobierno** (para quién, valor, límites, criterios de listo, dependencias):

- 💡 **IDEA**: ¿Por qué? (dolor real) · ¿De dónde surgió? (historia) · ¿Para qué?
  · ¿Cómo? · Pros/Contras · **¿Para quién? (stakeholders)** · **¿Qué valor aporta?
  (qué se gana)** · **¿Qué se arriesga si no se hace? (costo de no hacer)** ·
  **¿Cómo se sabe que está LISTO? (criterios de aceptación)** · **¿De qué depende?**
- ⚠️ **RIESGO**: ¿Qué riesgo es? · ¿Dónde se ubica? · Impacto · Mitigación +
  **Matriz de Gravedad**.
- 🔧 **CAMBIO / CORRECCION**: ¿Qué se modificó? · Razón del cambio · Archivos +
  **Verificación de No-Regresión**.
- 📦 **BASE**: Componente estructural, **Rol en la Arquitectura** e integraciones clave.
- 🧪 **PRUEBA**: Funcionalidad validada, **Criterios de Aceptación** y comando `pytest`.
- 📝 **FUTURO / TODO**: Tarea pendiente, Ubicación en código, **Prioridad**,
  **¿Cómo se sabe que está LISTA?** y **Responsable**.

**Regla de oro:** el contexto debe responder ¿por qué existe?, ¿para qué sirve?,
¿qué cumple?, ¿para quién es?, ¿cómo se sabe que está listo? — si una nota no
responde el porqué y el para quién, no tiene alma.

**Casillas honestas:** si el agente NO tiene el dato de una casilla de gobierno,
escribe "Pendiente de contexto" y la completa en la próxima actualización con la
historia real — NUNCA inventar una plantilla genérica que suene a respuesta.

## 🛡️ Zona protegida `7.0-MANUAL/` (visible en Obsidian)

Las notas manuales (sesiones, decisiones, mejoras — lo que el agente escribe
de lo conversado) viven en:

```
{vault}/7.0-MANUAL/
```

Es una carpeta VISIBLE (Obsidian oculta las carpetas que empiezan con ".").
El build JAMÁS las borra (también respeta frontmatter `preserve: true` donde
sea que estén). El `00-INDICE.md` las enlaza automáticamente y `ctxmap check`
cuenta cuántas hay.

## 🌳 Topología del vault (regla inamovible)

- Cada nota cuelga de EXACTAMENTE UN padre (árbol puro).
- Los índices de concepto usan nombre único por estado
  (`DEVOPS-Pendientes.md` ≠ `DEVOPS-Completas.md`).
- Secciones 2.1-Pendientes / 2.2-Futuras / 2.3-Completas son independientes y
  nunca se cruzan. Notas hoja enlazan solo a su padre vía `⬅ Volver a ...`.

---

> Generado automáticamente por ContextMap. Regenera con `ctxmap build --brief`.
"""

    output_path = os.path.join(target_dir, ".context-map", "contextmap-skill.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path

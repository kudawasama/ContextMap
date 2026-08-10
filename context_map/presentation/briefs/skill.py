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

Cada nota del vault se escribe con formato narrativo polimórfico según su tipo:

- 💡 **IDEA**: ¿Por qué?, ¿De dónde surgió?, ¿Para qué?, ¿Cómo? + tabla de **Pros y Contras**.
- ⚠️ **RIESGO**: ¿Qué riesgo es?, ¿Dónde se ubica?, Impacto, Mitigación + **Matriz de Gravedad**.
- 🔧 **CAMBIO / CORRECCION**: ¿Qué se modificó?, Razón del cambio, Archivos + **Verificación de No-Regresión**.
- 📦 **BASE**: Componente estructural, **Rol en la Arquitectura** e integraciones clave.
- 🧪 **PRUEBA**: Funcionalidad validada, **Criterios de Aceptación** y comando `pytest`.
- 📝 **FUTURO**: Tarea pendiente (TODO), Ubicación en código y **Prioridad**.

**Regla de oro:** el contexto debe responder ¿por qué existe?, ¿para qué sirve?,
¿qué cumple? — si una nota no responde el porqué, no tiene alma.

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

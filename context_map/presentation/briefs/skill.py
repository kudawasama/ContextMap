"""Generador de la skill de ContextMap dentro de .context-map/.

Contiene el **CÓMO operativo** (comandos exactos, criterios de calidad y
metodología narrativa). Las **normas** viven en `AGENTS.md` y su detalle en
`docs/GOBERNANZA-AGENTES.md`; esta skill no las repite — así no hay duplicación
de tokens entre los artefactos que lee el agente.
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

> `AGENTS.md` dice **QUÉ** hacer (normas) y `docs/GOBERNANZA-AGENTES.md` el
> detalle; esta skill es el **CÓMO operativo**: comandos exactos, criterios de
> calidad y metodología para escribir notas con alma.
> Última actualización: {fecha}

---

## 🚀 Poner el contexto al día (1 paso)

```bash
ctxmap refresh .     # = scan + build (preservando manuales) + check
```

## 🧰 Comandos

```bash
ctxmap scan .                  # escanear cambios del código -> nodos
ctxmap build --brief           # regenerar vault + brief (SIN --clean)
ctxmap check .                 # readiness + salud del vault
ctxmap search "<tema>"         # pasajes con citas (sin leer ficheros enteros)
ctxmap import-git .            # historial de commits y decisiones
ctxmap import-sessions         # sesiones de Hermes Agent
ctxmap import-antigravity      # conversaciones de Antigravity IDE
ctxmap import-chat <archivo>   # chats exportados (Telegram/Discord/Slack)
```

## 🔄 Actualizar NO es solo correr el script

1. **EJECUTA**: `ctxmap refresh .`.
2. **VERIFICA** (`ctxmap check .` sin alertas):
   - Títulos legibles: sin `TODO (ruta.py:Ln):` crudo ni paths aplanados
     (`context_mapcore...` debe leerse `context_map/core/...`).
   - `1.3-Proposito` y `CONTEXT.md` SIN métricas del scanner
     ("Proyecto 'X' — N archivos, N líneas").
   - Notas sin plantillas vacías ni `..` dobles.
3. **CORRIGE** los garabatos:
   - TODO del código → tarjeta técnica honesta (qué es, dónde está, qué hace el
     módulo, estado). NO narrativa de diseño.
   - Idea/mejora conversada → nota con alma en `{vault}/7.0-MANUAL/`
     (`preserve: true`).
   - Título feo → corrígelo para que se lea como humano.
4. **REGENERA Y RE-VERIFICA** si corregiste.

## ✍️ Cómo escribir las notas dándole vida (metodología narrativa)

- 💡 **IDEA**: ¿Por qué? · ¿De dónde surgió? · ¿Para qué? · ¿Cómo? · Pros/Contras ·
  ¿Para quién? · ¿Qué valor aporta? · ¿Costo de no hacerlo? · ¿Criterios de listo? · ¿De qué depende?
- ⚠️ **RIESGO**: ¿Qué es? · Ubicación · Impacto · Mitigación + Matriz de Gravedad.
- 🔧 **CAMBIO / CORRECCION**: qué se modificó · razón · archivos + Verificación de No-Regresión.
- 📦 **BASE**: componente estructural · Rol en la Arquitectura · integraciones.
- 🧪 **PRUEBA**: qué valida · Criterios de Aceptación · comando `pytest`.
- 📝 **FUTURO / TODO**: tarea · ubicación en código · prioridad · criterio de listo.

**Casillas honestas**: si no tienes el dato, escribe "Pendiente de contexto" y
complétalo con la historia real; NUNCA inventes una plantilla genérica.

## 🧠 Memoria viva y humanización

- **Documenta al momento**: ideas, decisiones y lecciones → `{vault}/7.0-MANUAL/Diario/`
  (lo conversado queda, sin esperar a que lo pidan).
- **Conocimiento reutilizable** → `{vault}/8.0-KNOWLEDGE/`
  (Lección · Cómo se resolvió · Prompt · Instrucción · Conexiones).
- **Humaniza TODO el vault** (índices con propósito, sin plantillas vacías);
  nunca borres historia ni notas manuales: lo tosco se **redacta**, no se elimina.
- Topología del árbol, vault único y verificación: `AGENTS.md` §4.

## 🛡️ Zona protegida `7.0-MANUAL/`

Carpeta VISIBLE en Obsidian para las notas manuales (sesiones, decisiones,
mejoras). El build JAMÁS las borra (también respeta `preserve: true` donde sea).
`00-INDICE.md` las enlaza y `ctxmap check` las cuenta.

---

> Generado automáticamente por ContextMap. Regenera con `ctxmap build --brief`.
"""

    output_path = os.path.join(target_dir, ".context-map", "contextmap-skill.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path

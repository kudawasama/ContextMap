"""Generador de instrucciones estandarizadas para agentes de IA (AGENTS.md).


Permite que cualquier proyecto inicializado o procesado por ContextMap disponga
de un archivo `AGENTS.md` estandarizado que fuerza a cualquier Agente de IA
(Antigravity, Cursor, Claude, Hermes, Copilot, etc.) a priorizar el contexto y
las reglas del repositorio automáticamente.
"""

from __future__ import annotations

import os
from datetime import datetime


def generar_instrucciones_agentes(
    project_name: str,
    target_dir: str = ".",
    output_filename: str = "AGENTS.md",
    overwrite_if_exists: bool = False,
) -> str:
    """Genera el archivo `AGENTS.md` en la raíz del proyecto de destino.

    Args:
        project_name (str): Nombre del proyecto.
        target_dir (str): Directorio raíz del proyecto.
        output_filename (str): Nombre del archivo de salida (por defecto `AGENTS.md`).
        overwrite_if_exists (bool): Si es False y el archivo existe, respeta el archivo existente.

    Returns:
        str: Ruta del archivo generado o existente.
    """
    output_path = os.path.join(target_dir, output_filename)

    if os.path.exists(output_path) and not overwrite_if_exists:
        return output_path

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")

    content = f"""# Instrucciones para Agentes de IA — {project_name}

> ⚠️ **REGLA PRIORITARIA PARA AGENTES DE IA**:
> **LEE el contexto del proyecto ANTES de investigar o modificar cualquier cosa.**
> Este proyecto se gobierna por su contexto: si no lo lees, trabajas a ciegas.
> Última actualización: {fecha}

Este proyecto utiliza **ContextMap** para gobernanza de contexto. Este `AGENTS.md`
define **QUÉ** hacer; el **CÓMO** (comandos exactos y metodología para escribir las
notas con alma) está en **[.context-map/contextmap-skill.md](file:///.context-map/contextmap-skill.md)**.

---

## 1. Protocolo de Inicio (QUÉ hacer antes de trabajar)

1. **Leer el Brief Ejecutivo**: `.context-map/CONTEXT.md` — responde qué es el
   proyecto, por qué existe, qué cumple, sus riesgos y tareas pendientes.
2. **Explorar el Vault**: `.context-map/vault/` o `.context-map/vault-{project_name}/`:
   propósito (1.0), ideas (2.0), riesgos (4.0) y backlog (5.0).
3. **Importar la historia del proyecto**: las conversaciones con el usuario también
   son contexto (comandos en la skill). Si el usuario comparte un chat, impórtalo
   ANTES de responder.
4. **Responder las 3 preguntas del alma** antes de proponer cambios:
   ¿Por qué existe este proyecto? ¿Para qué sirve? ¿Qué cumple?
5. **No Suponer Lógica**: inspecciona el código fuente antes de diagnosticar o cambiar.

---

## 2. Estándares de Desarrollo (QUÉ respetar)

* **Idioma**: explicaciones, comentarios y docstrings en **Español Técnico Profesional**.
* **Clean Architecture**: Principio de Responsabilidad Única (SRP) y convención modular `modulo/submodulo/archivo.py`.
* **Tipado Fuerte**: Type Hinting explícito en Python (`List`, `Dict`, `Tuple`, `Optional`).
* **Docstrings**: documentación formal en funciones, clases y módulos.
* **Raíz Limpia**: no crear archivos sueltos en la raíz (`PLAN.md`, `NOTES.txt`).

---

## 3. Verificación Obligatoria (QUÉ verificar)

Después de modificar código:

```bash
python -m pytest          # suite de pruebas (debe pasar 100%)
ctxmap refresh .          # contexto al día: scan + build (preservando manuales) + check
```

> Detalle de cada comando y el formato de las notas: `.context-map/contextmap-skill.md`.

---

## 4. Mantén Vivo el Contexto (QUÉ hacer al terminar)

El contexto es la **memoria viva del proyecto**:

1. Después de implementar, actualiza el mapa (`ctxmap refresh .`) para que refleje tu
   trabajo (nodos CAMBIO / CORRECCION / IDEA).
2. Al terminar una sesión de trabajo, importa la conversación (`import-sessions`,
   `import-antigravity`, `import-chat`) para que las decisiones y porqués queden
   registrados.
3. **Actualizar NO es solo correr el script**: verifica el resultado y corrígelo.
   El script propone, TÚ dispones — si `refresh` dejó títulos crudos
   (`TODO (ruta.py:Ln):`), métricas en `1.3-Proposito`, plantillas vacías o
   notas sin alma, corrígelas (títulos legibles, tarjeta técnica para TODOs,
   notas con alma en `7.0-MANUAL/`). No des el contexto por bueno sin revisarlo.
4. Un contexto que no se actualiza muere: el siguiente agente queda ciego y el
   proyecto pierde su historia.

> Comandos exactos y criterios de verificación: `.context-map/contextmap-skill.md`.

---

## 5. Convención de Commits

* Usar **Conventional Commits** en español (ej. `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`).
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path

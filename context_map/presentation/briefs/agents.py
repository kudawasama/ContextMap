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

Este proyecto utiliza **ContextMap** para gobernanza de contexto, mapas conceptuales y trazabilidad técnica. Cualquier agente de Inteligencia Artificial (Antigravity, Cursor, Claude, Hermes, Copilot, Windsurf, etc.) debe seguir estas instrucciones obligatoriamente.

---

## 1. Protocolo de Inicio (Ponerse en Contexto)

Antes de responder preguntas sobre el proyecto o escribir código, el Agente DEBE:

1. **Leer el Brief Ejecutivo**:
   Consultar [.context-map/CONTEXT.md](file:///.context-map/CONTEXT.md) — responde
   **qué es el proyecto, por qué existe, qué cumple**, sus riesgos críticos y tareas pendientes.
2. **Explorar el Vault Jerárquico**:
   Inspeccionar `.context-map/vault/` o `.context-map/vault-{project_name}/`:
   - `1.0-PROPOSITO/` (Identidad: qué es, por qué existe, qué cumple)
   - `2.0-IDEAS/` (`2.1-Ideas-Pendientes`, `2.2-Ideas-Futuras`, `2.3-Ideas-Completas`)
   - `4.0-RIESGOS/` (Deuda técnica y zonas de complejidad)
   - `5.0-BACKLOG/` (`5.1-Tareas.md`)
3. **Leer la Historia del Proyecto (chats y conversaciones)**:
   Importar las conversaciones e historial con el usuario para que las decisiones y
   los porqués queden en el mapa:

   ```bash
   python -m context_map.cli import-git .          # historial de commits y decisiones
   python -m context_map.cli import-sessions       # sesiones de Hermes Agent
   python -m context_map.cli import-antigravity    # conversaciones de Antigravity IDE
   python -m context_map.cli import-chat <archivo> # chats exportados (Telegram/Discord/Slack)
   ```

   Si el usuario comparte una conversación o menciona un chat relevante, importarla
   ANTES de responder: ahí viven las ideas, decisiones y contexto emocional del proyecto.
4. **Responder las 3 preguntas del alma** antes de proponer cambios:
   ¿Por qué existe este proyecto? ¿Para qué sirve? ¿Qué cumple?
5. **No Suponer Lógica**:
   Inspeccionar los archivos de código fuente antes de formular diagnósticos o proponer cambios.

---

## 2. Estándares de Desarrollo y Arquitectura

* **Idioma**: Todas las explicaciones, comentarios y docstrings deben estar en **Español Técnico Profesional**.
* **Clean Architecture**: Adherirse al Principio de Responsabilidad Única (SRP) y a la convención modular `modulo/submodulo/archivo.py`.
* **Tipado Fuerte**: Uso explícito de Type Hinting en Python (`List`, `Dict`, `Tuple`, `Optional`).
* **Docstrings**: Documentación formal en funciones, clases y módulos.
* **Raíz Limpia**: No crear archivos estáticos de notas en la raíz (`PLAN.md`, `NOTES.txt`). Mantener únicamente los archivos estándar del repositorio.

---

## 3. Protocolo de Verificación Obligatorio

Después de realizar modificaciones o implementar nuevas funciones, el Agente DEBE ejecutar los siguientes comandos de verificación:

```bash
# 1. Ejecutar suite de pruebas unitarias (debe pasar 100%)
python -m pytest

# 2. Escanear cambios en el mapa de contexto
python -m context_map.cli scan .

# 3. Reconstruir el Vault de Obsidian y el Brief ejecutivo
python -m context_map.cli build --clean --brief

# 4. Auditar el score de readiness
python -m context_map.cli check .
```

---

## 4. Mantén Vivo el Contexto (Regla de Vida del Proyecto)

El contexto no se genera una vez y se olvida: **es la memoria viva del proyecto**.
Después de implementar cualquier cambio, el Agente DEBE actualizar el mapa para que
refleje su trabajo (nodos CAMBIO / CORRECCION / IDEA). La forma más simple es el
comando único (scan + build preservando manuales + check):

```bash
python -m context_map.cli refresh .     # 1 paso: deja el contexto al día
```

O equivalentemente, paso a paso:

```bash
python -m context_map.cli scan .        # registrar lo que cambió
python -m context_map.cli build --brief # regenerar vault + brief (sin --clean)
```

**La conversación también es historia del proyecto.** Al terminar una sesión de
trabajo con el usuario, el Agente DEBE importarla para que las decisiones, ideas y
porqués queden registrados:

```bash
python -m context_map.cli import-sessions    # esta sesión de Hermes Agent
python -m context_map.cli import-antigravity # conversación de Antigravity IDE
python -m context_map.cli import-chat <archivo>  # chat exportado por el usuario
python -m context_map.cli refresh .          # regenerar vault + brief con la historia
```

Un contexto que no se actualiza muere: el siguiente agente queda ciego y el proyecto
pierde su historia. **Trabajar aquí incluye dejar el contexto al día.**

---

## 5. Convención de Commits

* Usar **Conventional Commits** en español (ej. `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`).
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path

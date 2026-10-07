# 🤖 Síntesis con LLM (opcional)

Por defecto `ctxmap wiki ask` responde **extractiva y localmente**: encadena las
frases más afines de la wiki y las cita `[1]`, `[2]`… Es determinista, no usa red
y no cuesta nada. Este documento explica el **paso opcional** que añade un LLM
para redactar mejor esa respuesta (G6 · plan v2.7).

## Principios

- **Nunca por defecto**: sin `CTXMAP_LLM_API_KEY` el hook está apagado.
- **Cero dependencias**: el cliente usa la librería estándar (`urllib`) contra
  cualquier endpoint compatible con la API de OpenAI.
- **Nunca rompe**: si la red, la clave o el modelo fallan, se devuelve la
  respuesta extractiva local.
- **Trazable**: la respuesta generada conserva las mismas `fuentes` y guarda la
  versión local en `respuesta_extractiva`.

## Activarlo

```bash
export CTXMAP_LLM_API_KEY="sk-..."                    # obligatoria para activarlo
export CTXMAP_LLM_MODEL="gpt-4o-mini"                 # opcional (default)
export CTXMAP_LLM_BASE_URL="https://api.openai.com/v1" # opcional (compatible OpenAI)
```

> En Windows (PowerShell): `$env:CTXMAP_LLM_API_KEY = "sk-..."`

Comprueba la configuración **sin gastar tokens**:

```bash
ctxmap wiki llm            # estado: disponible, modelo, endpoint, clave sí/no
ctxmap wiki llm --json     # salida estructurada (nunca muestra la clave)
ctxmap wiki llm --probar   # llamada mínima real (usa red y tokens)
```

## Usarlo

```bash
ctxmap wiki ask "¿cómo funciona RAG?"          # extractivo local (gratis)
ctxmap wiki ask "¿cómo funciona RAG?" --llm    # intenta el LLM; si falla, local
ctxmap wiki ask "¿cómo funciona RAG?" --no-llm # fuerza local aunque haya clave
```

Desde un agente (MCP), `knowledge_wiki_ask` acepta `llm: true`; en `false`
(por defecto) **nunca** sale a la red.

## Qué se envía (privacidad)

Al activarlo se envían al endpoint configurado **solo** los fragmentos de las
páginas de tu wiki que mejor encajan con la pregunta (más la pregunta). Nada más:
ni el vault, ni tu código, ni el resto de la wiki.

## Cuándo tiene sentido

| Situación | Recomendación |
| :--- | :--- |
| Recordar una decisión concreta ya escrita | Extractivo (`ask` a secas): más rápido y gratis |
| Pregunta que cruza varias páginas y pide redacción | `--llm` |
| Proyecto sensible / sin conexión | `--no-llm` (o no definir la clave) |
| Dentro de `build` / `refresh` | Jamás: el build no usa red |

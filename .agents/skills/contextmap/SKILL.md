---
name: contextmap
description: Memoria viva de ContextMap para ContextMap (brief, vault de Obsidian, Second Brain y memoria multi-proyecto). Úsala al empezar a trabajar, al preguntar «qué quedó pendiente», al cerrar sesión o al buscar en la memoria de otros proyectos.
---

# ContextMap — memoria viva de ContextMap

El script propone, **el agente dispone**: el contexto solo vale cuando el agente
lo revisó y lo corrigió.

## Protocolo de inicio (en este orden)
1. **Proyecto correcto**: el vault es `.context-map/vault-ContextMap/`. Si preguntan por otro proyecto, dilo ANTES de responder.
2. **Brief**: `mcp__contextmap__context` (capa mínima por defecto) o `.context-map/CONTEXT.md`. Si su sección «Estado del Contexto» avisa de diario más nuevo que el build → `ctxmap refresh .` primero.
3. **Pendientes REALES** (nunca una sola fuente): `7.0-MANUAL/BACKLOG.md` + `7.0-MANUAL/Diario/` + `5.0-BACKLOG/5.1-Tareas.md` + `3.2-DOCUMENTOS/`.
4. **Riesgos y propósito** (`4.0-RIESGOS/`, `1.0-PROPOSITO/`) y **código real** antes de proponer cambios.
5. **Al volver a una sesión**: `mcp__contextmap__context_diff(since=<digest>)` → solo lo que cambió desde la última lectura.

## Herramientas MCP
- Lectura (siempre visibles): `context` (`minimo=True` por defecto; `seccion="riesgos"` para una sola parte), `context_diff`, `context_search` (pasajes con citas), `personal_panorama`, `personal_query`, `knowledge_wiki_ask`.
- Operación (en codemode): `refresh`, `scan`, `build`, `check`, `doctor`, `knowledge_*`, `review`, `export`.

## Comandos
```bash
ctxmap refresh .                      # scan + build (preserva manuales) + check
ctxmap check .                        # readiness + salud del vault
ctxmap search "tema"                  # pasajes con citas
ctxmap ingest .context-map/raw/docs/  # MD/TXT/PDF -> DOCUMENTO
ctxmap personal query "tema"          # memoria multi-proyecto
```

## Detalle
- **CÓMO operativo** (ciclo de actualización, metodología narrativa, comandos exactos): `.context-map/contextmap-skill.md`.
- **Normas y topología del vault**: `AGENTS.md` (detalle en `docs/GOBERNANZA-AGENTES.md`).
- **Memoria viva**: ideas/decisiones/lecciones → `7.0-MANUAL/Diario/`; reutilizables → `8.0-KNOWLEDGE/`. `7.0-MANUAL/` es zona protegida (el build nunca la borra).

## Verificar antes de commit
- Tests: `python -m pytest` · `ctxmap refresh .` · sin archivos sueltos en la raíz.

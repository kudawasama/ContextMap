# CLAUDE.md — ContextMap

> Generado automáticamente por **ContextMap** — adaptado al stack real (2026-08-24 12:41).

## Contexto del proyecto

Este proyecto usa **ContextMap** para gobernanza de contexto. Antes de modificar código:

1. Lee `.context-map/CONTEXT.md` (brief ejecutivo: métricas, riesgos, tareas).
2. Explora el vault en `.context-map/vault-ContextMap/` para entender el grafo del proyecto.
3. No supongas lógica: inspecciona el código fuente antes de proponer cambios.
4. Para contexto histórico global (otros proyectos): `ctxmap personal query "términos" --limite 5` (BD personal FTS5, pocos tokens).

## Comandos de verificación

```bash
python -m pytest
python -m context_map.cli build --clean --brief
python -m context_map.cli check .
```

## Convenciones

- Commits: Conventional Commits en español (`feat:`, `fix:`, `refactor:`, `docs:`).
- Respuestas y docstrings en Español Técnico Profesional.
- Respetar la arquitectura modular existente; no crear archivos sueltos en la raíz.

---
name: contextmap
description: Protocolo, flujos y comandos esenciales para gobernar el contexto, consultar la memoria permanente y mantener vivo el grafo del proyecto con ContextMap IA.
---

# Skill de ContextMap IA — ContextMap

Esta skill proporciona las directivas operativas para interactuar con la memoria permanente, los documentos de referencia y el grafo conceptual de **ContextMap**.

## Comandos Esenciales

```bash
# 1. Poner todo el contexto al día en un solo paso (scan + build con preservación + auto-ingesta + check)
ctxmap refresh .

# 2. Ingerir documentos brutos manualmente (MD, TXT, PDF)
ctxmap ingest .context-map/raw/docs/

# 3. Verificar la salud, integridad y enlaces rotos del vault
ctxmap check .

# 4. Sincronizar memoria personal / multi-proyecto
ctxmap personal sync

# 5. Consultar decisiones o conocimiento histórico
ctxmap personal query "tema de consulta"
```

## Protocolo de Inicio y Memoria Viva para Agentes

1. **Inspeccionar Brief**: Leer `.context-map/CONTEXT.md` (identidad, propósito, métricas y estado).
2. **Consultar Documentos y Backlog**: Revisar `.context-map/vault-ContextMap/3.2-DOCUMENTOS/`, `7.0-MANUAL/BACKLOG.md` y notas de diario recientes.
3. **Memoria Viva Multicanal**: Para incorporar contexto externo (conversaciones, transcripciones o especificaciones), colócalos en `.context-map/chats/` o `.context-map/raw/docs/`. `ctxmap refresh .` los asimilará automáticamente.
4. **Verificar Antes de Commit**:
   - Tests: `python -m pytest`
   - Refrescar grafo y vault: `ctxmap refresh .`
   - Sin archivos sueltos en raíz.

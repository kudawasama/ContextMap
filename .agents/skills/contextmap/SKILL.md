---
name: contextmap
description: Protocolo, flujos y comandos esenciales para gobernar el contexto, consultar la memoria permanente y mantener vivo el grafo del proyecto con ContextMap IA.
---

# Skill de ContextMap IA — ContextMap

Esta skill proporciona las directivas operativas para interactuar con la memoria permanente y el grafo conceptual de **ContextMap**.

## Comandos Esenciales

```bash
# 1. Poner todo el contexto al día en un solo paso (scan + build con preservación + check)
ctxmap refresh .

# 2. Verificar la salud, integridad y enlaces rotos del vault
ctxmap check .

# 3. Sincronizar memoria personal / multi-proyecto
ctxmap personal sync

# 4. Consultar decisiones o conocimiento histórico
ctxmap personal query "tema de consulta"
```

## Protocolo de Inicio para Agentes

1. **Inspeccionar Brief**: Leer `.context-map/CONTEXT.md` (identidad, propósito y estado).
2. **Consultar Backlog Real**: Revisar `.context-map/vault-ContextMap/7.0-MANUAL/BACKLOG.md` y notas de diario recientes.
3. **Verificar Antes de Commit**:
   - Tests: `python -m pytest`
   - Refrescar grafo: `ctxmap refresh .`
   - Sin archivos sueltos en raíz.

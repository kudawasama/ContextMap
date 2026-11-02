# 🗺️ ContextMap

**La memoria permanente para tus asistentes de IA.**
Que tu IA no olvide tus decisiones, no queme tokens y no rompa tu código.

ContextMap escanea tu proyecto, entiende su estructura y su propósito, y produce
**dos artefactos portables** que cualquier agente puede leer:

1. 🗺️ **Una bóveda de Obsidian** — el mapa mental del proyecto: ideas, decisiones,
   riesgos y su historia, navegable como un grafo.
2. 📄 **Un brief ejecutivo (`CONTEXT.md`)** — un resumen de alta densidad: identidad,
   estado, riesgos y pendientes en unos pocos cientos de tokens.

> **Principio de diseño:** *el script propone, el agente dispone*. ContextMap no
> "adivina" tu proyecto: genera el borrador, y el agente lo revisa y lo humaniza.

## Instalación rápida

```bash
uv tool install "context-map-ai[mcp,secure]"   # CLI + servidor MCP
# o: pip install "context-map-ai[mcp,secure]"
```

## Uso en tres comandos

```bash
ctxmap scan .                  # escanea estructura, git, documentos y sesiones
ctxmap build --clean --brief   # genera la bóveda Obsidian y el brief
ctxmap check .                 # readiness del proyecto
```

`ctxmap refresh .` encadena los tres en un solo paso y preserva tus notas manuales.

## Servidor MCP

El paquete incluye un servidor MCP con **33 herramientas** que expone el contexto,
la búsqueda, el conocimiento y la gobernanza del proyecto a cualquier agente
compatible:

```bash
ctxmap mcp
```

## Documentación

| Página | Qué encontrarás |
|---|---|
| [Paquete e instalación](PI_PACKAGE.md) | Extras, entrypoints, extensión MCP y flujo de publicación |
| [Gobernanza de agentes](GOBERNANZA-AGENTES.md) | Reglas para Antigravity, Cursor, Hermes, Claude, Windsurf y Copilot |
| [Portabilidad y secretos](PORTABILIDAD.md) | Baúl cifrado, rekey y traslado entre máquinas |
| [Web Clipper](WEB_CLIPPER.md) | Ingesta de artículos y capturas al conocimiento vivo |
| [LLM y conocimiento](LLM.md) | Wiki, embeddings, revisión espaciada y consultas locales |
| [Launch Kit](LAUNCH_KIT.md) | Plantillas de difusión y registro en directorios MCP |
| [Comparativa del ecosistema](COMPARATIVO-ECOSISTEMA-CONTEXTO.md) | Frente a otras herramientas de contexto |
| [Investigación Jev](INVESTIGACION-JEV.md) | Origen del motor de clasificación calibrada |

## Enlaces del repositorio

- 📖 [README completo](https://github.com/kudawasama/ContextMap/blob/master/README.md)
- 🇬🇧 [English README](https://github.com/kudawasama/ContextMap/blob/master/README_EN.md)
- 📜 [Historial de versiones](https://github.com/kudawasama/ContextMap/blob/master/CHANGELOG.md)
- 🤝 [Contribuir](https://github.com/kudawasama/ContextMap/blob/master/CONTRIBUTING.md)
- 📦 [PyPI: context-map-ai](https://pypi.org/project/context-map-ai/)

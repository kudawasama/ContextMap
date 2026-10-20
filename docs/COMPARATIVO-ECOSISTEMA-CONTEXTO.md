# Comparativo — ContextMap frente al ecosistema de contexto, Obsidian y Second Brain

> Investigación realizada el **2026-10-13**. Estrellas de GitHub obtenidas vía API
> en esa fecha; son un indicador de tracción, no de calidad.

## 1. Panorama por área

### PKM / Second Brain (aplicaciones)

| Proyecto | ★ | Qué aporta |
|---|---|---|
| Joplin | 56.7k | Notas cifradas, sync, multiplataforma |
| Logseq | 45.2k | Outliner con grafo, privacidad primero |
| Trilium | 38.3k | Base de conocimiento jerárquica con scripting |
| Khoj | 37.7k | «AI second brain» autoalojable, responde sobre tus docs |
| QOwnNotes | 5.9k | Markdown plano + Nextcloud |
| Anytype | 8.9k | Objetos tipados, local-first, cifrado |
| Reor | 8.5k | PKM local con IA privada |

### Obsidian + agente

| Proyecto | ★ | Qué aporta |
|---|---|---|
| kepano/obsidian-skills | 49.5k | *Skills* para que el agente use Obsidian CLI y formatos abiertos |
| claudian | 15.7k | Plugin que embebe Claude Code/Codex dentro del vault |
| claude-obsidian | 15.6k | Second brain que se auto-organiza con Claude Code |
| obsidian-smart-connections | 5.5k | Notas relacionadas por embeddings mientras escribes |
| obsidian-mind | 5.3k | Vault que da memoria persistente a agentes |
| obsidian-mcp-plugin | 0.5k | Servidor MCP con acceso directo al vault |

### Memoria para agentes

| Proyecto | ★ | Qué aporta |
|---|---|---|
| mem0 | 67.1k | Capa de memoria *drop-in* para agentes y apps |
| cognee | 32.2k | Plataforma de memoria de largo plazo |
| graphiti (Zep) | 31.7k | **Grafo de conocimiento temporal** en tiempo real |
| letta (MemGPT) | 25.1k | Agentes con estado que aprenden y se auto-mejoran |
| basic-memory | 4.2k | Conversaciones con IA que recuerdan, en Markdown |
| MIRIX · memobase · deja-vu · okf-agent-memory | 3.4k · 2.9k · 1.2k · 0.8k | Memoria por perfil, por historial de sesiones, git-native |

### Contexto de código / ingeniería de contexto

| Proyecto | ★ | Qué aporta |
|---|---|---|
| github/spec-kit | 141k | Toolkit *spec-driven development* |
| OpenSpec | 71.8k | SDD para asistentes de código |
| context7 | 63k | Documentación de librerías actualizada para LLM |
| private-gpt | 57.6k | Capa RAG local para apps privadas |
| llama_index | 52.5k | Ingesta y procesamiento de documentos |
| aider | 49.5k | *Repo map* para pair programming |
| fabric | 44.2k | Patrones modulares de aumento con IA |
| PageIndex | 39.1k | RAG sin vectores basado en razonamiento |
| serena | 30.2k | MCP con recuperación y edición semántica de código |
| repomix | 28.8k | Empaqueta el repo en un archivo amigable para IA |

### Ingesta

| Proyecto | ★ | Qué aporta |
|---|---|---|
| markitdown | 190k | PDF/Office/imágenes → Markdown |
| ragflow | 92.2k | Motor RAG de extremo a extremo |

## 2. Capacidad por capacidad

| Capacidad | Quién la tiene | ContextMap |
|---|---|---|
| Vault Obsidian navegable como grafo | Obsidian + plugins | ✅ con **topología de árbol validada por test** (0 sin padre, 0 colisiones, 0 wikilinks rotos) — nadie más impone esa garantía |
| Brief portable para cualquier agente | spec-kit, context7, repomix | ✅ `CONTEXT.md` (+ `.min`, + secciones, + `context_diff`) |
| Memoria viva multi-proyecto | mem0, cognee, basic-memory | ✅ BD personal + FTS5 + panorama |
| Ingesta multiformato (chats, IDE, git, web, vídeo) | deja-vu, markitdown, ragflow | ✅ chats/IDE/git/sesiones/web/vídeo YouTube |
| Recuperación léxica con citas | casi todos usan embeddings | ✅ BM25 + semántico opcional |
| Humanización de la salida (nada de plantillas vacías) | — | ✅ único |
| Clasificación con **confianza calibrada** | Jev (externo) | ✅ implementado (local, determinista) |
| **Cola de revisión de ambigüedad** | — | ✅ `revision:clasificacion` |
| Grafo temporal de entidades | graphiti | ❌ |
| Spec-driven development | spec-kit, OpenSpec, BMAD | ❌ |
| Sync bidireccional con Obsidian | claudian, obsidian-mcp-plugin | ⚠️ solo escritura (genera el vault) |
| Memoria conversacional *drop-in* para apps | mem0, letta | ❌ (ContextMap es el mapa, no el runtime) |

## 3. Lectura estratégica

**Fortalezas diferenciales de ContextMap**

1. **Gobernanza de la salida**: es el único que trata el vault como artefacto
   verificable (test de topología, readiness, frescura, humanización). Los demás
   generan notas; ContextMap garantiza que el grafo no se corrompe.
2. **Portabilidad y coste cero**: un archivo Markdown + un brief optimizado para
   *prompt caching*; sin claves, sin nube, sin cuotas.
3. **Determinismo**: mismo repo → mismo vault. Ninguna de las alternativas
   basadas en LLM lo ofrece.

**Brechas reales (candidatas a roadmap, no a este plan)**

1. **Temporalidad**: graphiti modela *cuándo* cambió un hecho. ContextMap tiene
   diario y fechas, pero no un grafo temporal consultable.
2. **Feedback loop**: no hay forma de que el agente corrija una clasificación y
   el sistema aprenda del ajuste. La cola `revision:clasificacion` es el primer
   eslabón; falta el ciclo de vuelta.
3. **Spec-driven**: spec-kit/OpenSpec parten de especificaciones; ContextMap
   parte del código existente. Son complementarios, no sustitutos.
4. **Sync bidireccional**: si el humano edita el vault, hoy no vuelve al mapa.

## 4. Conclusión

ContextMap no compite con Obsidian (es su formato de salida), ni con mem0/letta
(esos viven dentro del runtime del agente), ni con spec-kit (esos parten de
especificaciones). Su nicho es **el mapa de contexto verificable y portable de un
proyecto**. La única capacidad del ecosistema que le daba ventaja competitiva y
no tenía era la **decisión calibrada** (Jev); al replicarla localmente se cierra
sin añadir dependencias, coste ni pérdida de determinismo.

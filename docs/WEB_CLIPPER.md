# 📥 Web Clipper — capturar la web a tu Second Brain

Guía del flujo **local-first** de captura web de ContextMap: sin servidor, sin
extensiones y sin dependencias. Tres piezas que se combinan:

| Pieza | Comando | Para qué |
| :--- | :--- | :--- |
| **Bookmarklet** | `ctxmap inbox bookmarklet --html` | Copia la página actual (título + URL + selección) al portapapeles |
| **Portapapeles** | `ctxmap inbox add --clipboard` | Convierte el portapapeles en una nota del inbox |
| **Artículo completo** | `ctxmap ingest --url "<url>"` | Descarga la página, la limpia a Markdown y la captura (inbox o wiki) |

La captura aterriza en el `90-CONOCIMIENTO/00-INBOX` de tu vault
(`.context-map/vault-<Proyecto>`), con `namespace: knowledge` y
`preserve: true`: el `build` **jamás** la borra.

---

## 1. Instalar el bookmarklet (una sola vez)

```bash
ctxmap inbox bookmarklet --html
```

Se genera `.context-map/clip-bookmarklet.html`. Ábrelo en el navegador y
**arrastra** el enlace «📥 Capturar en ContextMap» a tu barra de favoritos.

> ¿Sin HTML? `ctxmap inbox bookmarklet` imprime el código `javascript:` para
> pegarlo a mano como URL de un favorito nuevo.

## 2. Capturar una página

1. En cualquier web, pulsa el favorito: se copia al portapapeles algo como

   ```markdown
   - [Título de la página](https://ejemplo.com/articulo)

   > (el texto que tuvieras seleccionado, si había alguno)
   ```

2. En la terminal, desde la carpeta del proyecto:

   ```bash
   ctxmap inbox add --clipboard
   ```

Resultado: la nota se crea con **título legible** y **URL como fuente**
(ContextMap desglosa el enlace Markdown automáticamente):

```yaml
title: "Título de la página"
source: "https://ejemplo.com/articulo"
status: inbox
tags: [knowledge, inbox]
```

## 3. Variantes útiles

```bash
# Pipe clásico (macOS / Linux) — mismo resultado sin --clipboard
pbpaste | ctxmap inbox add -
xclip -selection clipboard -o | ctxmap inbox add -

# Windows (PowerShell)
Get-Clipboard | ctxmap inbox add -

# Título y etiquetas explícitos
ctxmap inbox add --clipboard --title "Idea para el README" --tags "docs,idea"

# Artículo completo → wiki (con entidades), en vez de una nota cruda
ctxmap ingest --url "https://ejemplo.com/articulo" --destino wiki --entidades "RAG, Embeddings"
```

## 4. Qué hace cada canal

- **`--clipboard`**: lee el portapapeles con la herramienta nativa del sistema
  (`pbpaste` · PowerShell `Get-Clipboard` · `wl-paste`/`xclip`/`xsel`). Si no hay
  ninguna disponible devuelve un mensaje claro y no rompe nada.
- **`-` / `--stdin`**: lee de la entrada estándar, ideal para pipelines.
- **`ingest --url`**: descarga y limpia el artículo completo (HTML → Markdown) y
  lo deposita en el inbox o directamente en la wiki con sus entidades.

## 5. Desde un agente (MCP)

Los mismos flujos están expuestos como herramientas MCP: `knowledge_inbox_add`
(nota cruda), `knowledge_inbox_move` (clasificar a PARA) y `knowledge_ingest`
(URL o video → inbox/wiki). El agente puede capturar sin que toques la terminal.

---

## 🔗 Relacionado

- Wiki y Second Brain: `ctxmap wiki {ingest|query|ask|moc|lint|embeddings}`
- Repaso espaciado: `ctxmap review {due|grade}`
- Clasificación PARA del inbox: `ctxmap inbox purge`

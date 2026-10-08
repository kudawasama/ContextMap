# 🧩 Paquete de pi — `@kudawa/pi-contextmap`

ContextMap también se distribuye como **paquete de [pi](https://pi.dev)** para que
cualquier agente traiga la memoria viva del proyecto con un solo comando.

```bash
pi install npm:@kudawa/pi-contextmap
```

- **Registro npm**: https://www.npmjs.com/package/@kudawa/pi-contextmap
- **Código**: https://github.com/kudawasama/pi-contextmap
- **Galería de pi**: https://pi.dev/packages (aparece por la keyword `pi-package`)

## Requisitos

El paquete no incluye el motor: instala el CLI de ContextMap.

```bash
uv tool install "context-map-ai[mcp]"     # o: pip install "context-map-ai[mcp]"
```

Si falta, la extensión **avisa al iniciar la sesión** con el comando exacto (no
deja errores de conexión ruidosos).

## Qué aporta

| Recurso | Nombre | Para qué |
|---|---|---|
| Extensión | MCP `contextmap` | Registra `ctxmap mcp` (29 herramientas). Las 4 de lectura (`context`, `personal_panorama`, `personal_query`, `knowledge_wiki_ask`) van `direct`; el resto en `codemode` |
| Skill | `/skill:contextmap` | Protocolo: ponerse en contexto, actualizar sin ensuciar, memoria viva, topología del vault |
| Prompt | `/contextmap-contexto` | Arrancar con brief + pendientes reales |
| Prompt | `/contextmap-cierre` | Cerrar sesión: refresh → verificar → documentar |
| Prompt | `/contextmap-preguntar` | Preguntar a la memoria de todos los proyectos, con citas |

## Publicación (Trusted Publishing / OIDC)

El paquete vive en su propio repo y se publica **sin tokens ni códigos**:
`.github/workflows/publish.yml` usa el OIDC de GitHub Actions + npm.

Un único paso manual (una sola vez): en npmjs.com → paquete →
**Settings → Trusted Publisher → GitHub Actions**, autorizar
`kudawasama/pi-contextmap` con el workflow `publish.yml`.

Después, publicar una versión nueva es:

```bash
npm version patch --no-git-tag-version    # sube package.json
python scripts/make_preview.py            # regenera la tarjeta si cambió el texto
git commit -am "chore: vX.Y.Z" && git tag vX.Y.Z && git push --follow-tags
```

El workflow verifica que el tag coincide con `package.json` y publica con
proveniencia firmada.

## Notas

- El nombre npm original (`pi-contextmap`) fue **rechazado por npm** por ser
  demasiado parecido a `pi-context-map`; se publicó con ámbito `@kudawa`.
- El paquete se mantiene **fuera** del repo de ContextMap para no meter npm/TS en
  el escáner del proyecto Python; aquí solo se documenta.
- Versiones: la del paquete de pi es **independiente** de la de PyPI
  (`context-map-ai`).

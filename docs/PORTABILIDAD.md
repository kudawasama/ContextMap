# 🌍 Portabilidad y recuperación (Fase 3)

Lleva tu memoria de ContextMap (**vault, brief, lecciones y el baúl de secretos
cifrado**) a otro PC, o restáurala si cambias de equipo.

## Opción A — vía Git (el contexto en el repositorio)

Por defecto `.context-map/` está en `.gitignore` (para no ensuciar el repo).
Si quieres que la memoria viaje con `git pull`:

1. **Deja de ignorarlo**: quita la línea `.context-map/` de tu `.gitignore`
   (o añade con fuerza la primera vez: `git add -f .context-map`).
2. Ejecuta `ctxmap refresh .` y **commitea**.
3. En el otro PC: `git pull` y `ctxmap refresh .` — la memoria y el brief quedan
   al día, y la **revisión automática** regenera las reglas de ese IDE.

**Los secretos viajan cifrados**: `secure/vault.json` se puede commitear con
tranquilidad — sin la **frase maestra** nadie lo descifra. `audit.log` no
contiene valores y `recetas/` son tus guiones.

> ⚠️ **Nunca** commitees la frase maestra ni valores en claro (busca el aviso
> de detección de secretos de `ctxmap` si un valor se cuela en una nota).

## Opción B — vía pendrive / Drive (la BD personal ya vive en F:)

La **memoria multi-proyecto** ya es transportable (`~/.context-map/personal/
personal.db` se mueve a F: o a un pendrive con `ctxmap personal backup`). Para
los secretos:

```bash
# Exportar el baúl cifrado (global) al pendrive
ctxmap secret backup "F:/context-map/vault-backup.json" --global

# En el otro PC, restaurarlo (con verificación de la frase)
ctxmap secret restore "F:/context-map/vault-backup.json" --global --verificar
```

## ♻️ Recuperación (equipo nuevo o perdido)

1. Instala: `pip install "context-map-ai[secure] mcp"` (o `uv tool install "context-map-ai[mcp,secure]"`).
2. Restaura el baúl con la **Opción A o B**.
3. Usa tu **frase maestra** — está en tu gestor de contraseñas. **Sin ella no
   hay recuperación**: es la única llave y ContextMap nunca la almacena.
4. `ctxmap refresh .` en cada proyecto para reconstruir vault + brief.

## Resumen de comandos del baúl

```bash
ctxmap secret init                        # crear el baúl (por proyecto o --global)
ctxmap secret backup <destino>            # exportar el baúl cifrado
ctxmap secret restore <origen> [--verificar] [--overwrite]   # importarlo
ctxmap secret where                       # dónde vive el baúl
```
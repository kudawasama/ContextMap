# Incidente del historial de snapshots (2026-10-13) — análisis y delta implementado

**Contexto:** servidor «kudawa» (Ubuntu 24.04). `~/Proyectos/.context-map/maps/HISTORY/` acumuló **103.354 archivos / 148 GB** y dejó la raíz `/dev/sda2` (233 GB) al **100 %** con 1,2 GB libres.

## Evidencia recogida

| Comando | Resultado |
|---|---|
| `df -h /` | `233G 220G 1,2G 100% /` |
| `du -sh ~/Proyectos/.context-map/maps/HISTORY` | `148G` |
| `ls -1 maps/HISTORY \| wc -l` | `103.353` |
| `ps` / `systemctl --user status ctxmap-watch.service` | `ctxmap watch /home/jose/Proyectos` activo, `Restart=always` |
| `systemctl list-timers` | `kudawa-page-deploy.timer` cada **60 s** (git pull → `frontend/version.json`) |
| `journalctl -u logrotate` | `gzip: stdout: No space left on device` — el disco lleno rompió el mantenimiento |
| muestra de `/var/log/syslog.1` | 5.676 × banner `ctxmap[...]` + 2.838 × `vault (hierarchical):ok` en 200k líneas (bucle de refrescos) |

## Causa raíz

1. **Historial sin tope** (versión instalada, v2.4.1): cada `build`/`refresh` copiaba el mapa completo (~2,9 MB con ~9.800 nodos) sin retención ni deduplicado, con series `-2…-N` sin cota de longitud.
2. **Daemon realimentado**: `ctxmap watch` se disparaba con *cualquier* archivo `.py/.md/.json/...` del árbol, incluidas las salidas que él mismo y otros servicios escribían (`version.json` cada minuto).
3. **Sin guarda de disco**: nada comprobaba el espacio libre antes de escribir.

Estado del repositorio en el momento del análisis: `master` remoto ya en **v2.13.0**, con retención (`purgar_snapshots`, v2.10.0) y deduplicado por hash en `snapshot_map`. El binario instalado en el servidor seguía en v2.4.1 porque el clon local estaba desfasado.

## Delta implementado en esta rama (sobre v2.13.0)

| # | Cambio | Archivo |
|---|---|---|
| 1 | Filtro de **salidas generadas** (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTEXT.md`, `.cursorrules`, `.windsurfrules`, `version.json`) | `domain/synchronization/watcher.py` |
| 2 | `min_interval_s` (60 s) + **ventana de supresión** de los eventos del propio refresco, en watchdog y en polling | `domain/synchronization/watcher.py` |
| 3 | `--no-snapshot` en `build`/`refresh`; el daemon refresca sin escribir historial | `application/commands/{build,refresh}.py`, `cli/parser.py` |
| 4 | **Guarda de disco** en `snapshot_map` (`CTXMAP_SNAPSHOT_MIN_FREE_MB`, 512 MB) + `espacio_libre_mb()` | `core/storage/store.py` |
| 5 | Colisiones de nombre con marca temporal + huella (fin de `-2…-N`) | `core/storage/store.py` |
| 6 | `purgar_snapshots(..., dry_run=True)` | `core/storage/store.py` |
| 7 | Comando `ctxmap history list\|prune [--keep\|--keep-days\|--delete\|--dry-run\|--json]` | `application/commands/history_cmd.py`, `cli/{parser,cli}.py` |
| 8 | Chequeo `history` en `ctxmap doctor` (WARN a 5× la retención; `--fix` archiva) | `domain/health/doctor.py` |

## Verificación

- Suite: `423 passed`, 2 skipped, **los mismos 14 fallos preexistentes de master** (12 de secretos por falta de `cryptography` en el entorno de pruebas, 2 conocidos). Baseline previa: 409 passed / 14 failed.
- 14 pruebas nuevas (ver CHANGELOG [Unreleased]).
- End-to-end con el binario instalado: 50 builds seguidos sin crecimiento del historial (deduplicado), `history prune --keep 20` deja 20 y archiva el resto, `--dry-run` no toca el disco, `doctor` informa del estado.

## Fase B — estado en el host (fuera del repositorio)

| Tarea | Estado |
|---|---|
| Daemon `ctxmap-watch` detenido y deshabilitado | hecho |
| `maps/HISTORY` vaciado (muestra e inventario en `~/backups/`) | hecho |
| Journal limitado a 300 MB (`/etc/systemd/journald.conf.d/limite.conf`) | hecho |
| Poda diaria de respaldo (`~/bin/ctxmap-history-prune.sh` + `ctxmap-history-prune.timer`) | hecho (sustituible por `ctxmap history prune` al actualizar) |
| `/var/log/syslog.1` (679 MB) borrado y `logrotate` con `su root syslog` + `maxsize 100M` | hecho |
| `kudawa-page-deploy.timer`: 60 s → 5 min | pendiente de aprobación sudo |
| `docker image prune -a` (26 GB de imágenes sin uso, 24 contenedores vivos) | pendiente de aprobación sudo |
| Reactivar el daemon | descartado: mejor un timer por proyecto (`ctxmap-refresh@<proyecto>.timer`, plantilla ya creada en `~/.config/systemd/user/`) |

Nota: el daemon `ctxmap watch` sobre un árbol multi-proyecto no se recomienda ni con estas guardas; el refresco periódico por proyecto es más barato y más predecible.

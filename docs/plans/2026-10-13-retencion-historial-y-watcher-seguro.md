# Plan de implementación — Retención del historial y watcher seguro (ContextMap v2.5.0) + hardening del servidor

> **Para Hermes:** ejecutar con el skill `subagent-driven-development` (un subagente por tarea, revisión de especificación y luego de calidad). No implementar antes de leer §0 y §3.

**Objetivo:** eliminar la clase de fallo que llenó la raíz del servidor al 100 % (148 GB / 103.354 archivos en `.context-map/maps/HISTORY/`) mediante retención, deduplicado y guardas de disco dentro de ContextMap, un watcher que no pueda entrar en bucle ni escribir historial, visibilidad (`ctxmap history`, `doctor`) y las salvaguardas pendientes del host.

**Arquitectura:** un módulo de responsabilidad única (`context_map/core/storage/history.py`) concentra métricas, huella de contenido, poda por cantidad/tamaño y chequeo de espacio. `snapshot_map` pasa a ser una secuencia guardas → dedupe → copia → poda. El `watch` deja de ser un escritor de historial: filtra sus propias salidas, impone intervalo mínimo con ventana de supresión y refresca con `--no-snapshot`. Configuración declarativa (`.contextmap.toml` / `pyproject.toml`) parametriza todo con valores seguros por defecto.

**Stack:** Python 3.11+ (`from __future__ import annotations`, type hints estrictos, docstrings Google en español), `watchdog` (opcional, ya instalado en el venv del tool), pytest 7+, hatchling, `uv` para instalación (`uv tool install --force`), systemd de usuario en el host (Ubuntu 24.04, Dell Latitude E7250 «kudawa»).

**Baseline verificado del repo** (`/home/jose/Proyectos/ContextMap`, commit `cf6ca1b` «v2.4.1»):

```
$ cd /home/jose/Proyectos/ContextMap
$ uv run --with pytest --with pytest-mock --quiet pytest -q
2 failed, 263 passed, 1 skipped in 9.15s
    FAILED context_map/__tests__/test_dependencias_mcp.py::test_pydantic_soporta_create_model_con_tipo_desnudo
    FAILED context_map/__tests__/test_enrich.py::test_cmd_enrich_persiste_cambios_en_disco
```
Ambos fallos son **preexistentes y ajenos a este plan** (pydantic/MCP y RAM disponible para Ollama). La línea base de aceptación es: **sin regresiones** — el conteo final debe ser `2 failed, 263+N passed`.

---

## 0. Evidencia del incidente (2026-10-13, host «kudawa»)

| # | Comando | Resultado |
|---|---|---|
| 1 | `df -h /` | `/dev/sda2 233G 220G 1,2G 100% /` |
| 2 | `du -sh ~/Proyectos/.context-map` | `148G` |
| 3 | `du -sh ~/Proyectos/.context-map/maps/HISTORY` | `148G` |
| 4 | `ls -1 maps/HISTORY \| wc -l` | `103.353` archivos planos |
| 5 | `ls -lat maps/HISTORY \| head` | snapshots de `2.915.072` bytes escritos a las 21:25–21:29 |
| 6 | `systemctl --user status ctxmap-watch.service` | activo, `Restart=always`, `ExecStart=ctxmap watch /home/jose/Proyectos` |
| 7 | `systemctl list-timers` | `kudawa-page-deploy.timer` **cada 60 s** (git pull + docker compose en `~/Proyectos/pagina_kudawa.com`) |
| 8 | `sudo journalctl -u logrotate` | `gzip: No space left on device` — el disco lleno rompió el mantenimiento del sistema |
| 9 | `sudo head -n 200000 /var/log/syslog.1 \| ...` | 5.676 × banner `ctxmap[...]: ⬆️ Hay una actualización disponible` + 2.838 × `vault (hierarchical):ok` (el watcher rebuilds en bucle) |
| 10 | `npm/tool` instalado | `context-map-ai 2.4.1` en `/home/jose/.local/bin/ctxmap` (uv tool) |

Acciones de contención ya aplicadas (no forman parte del código a escribir, ver §6): servicio `ctxmap-watch` detenido y deshabilitado, `maps/HISTORY` vaciado (148 GB liberados, raíz en 32 %), journal limitado a 300 MB, script + timer `ctxmap-history-prune` instalados.

---

## 1. Causa raíz (código actual)

**D1 — El historial no tiene retención.** `snapshot_map()` copia el mapa completo sin ningún límite de cantidad ni de tamaño.

`context_map/core/storage/store.py:163-176`
```python
    dst = os.path.join(".context-map", "maps", "HISTORY", out_name)
    if os.path.exists(dst):
        base_name = out_name.rsplit(".", 1)[0]
        contador = 2
        while os.path.exists(dst):
            dst = os.path.join(".context-map", "maps", "HISTORY", f"{base_name}-{contador}.md")
            contador += 1
    _ensure(dst)
    shutil.copy2(src, dst)
```

**D2 — Sin deduplicado por contenido.** El nombre es descriptivo del grafo (`_generar_nombre_descriptivo`, `store.py:88-125`), así que dos builds con el mismo conjunto de nodos producen el **mismo nombre** y el bucle anterior genera `-2`, `-3`, … `-1218` copias **idénticas** del mismo mapa.

**D3 — Sin guarda de disco.** Nada comprueba el espacio libre antes de copiar: el tool siguió escribiendo con 1,2 GB libres.

**D4 — El watcher re-dispara sin control.**
- `watcher.py:21-28` filtra por extensión y por `DIRECTORIOS_EXCLUIDOS`, pero **no** por archivos generados en la raíz: `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` / `.cursorrules` / `.windsurfrules` (los produce `presentation/briefs/agents.py:19` y `domain/ecosystem/rules_templates.py:16-19`) sí disparan.
- `watcher.py:95-101` no tiene intervalo mínimo entre refrescos ni ventana de supresión: cualquier tercero que escriba un `.json`/`.md` bajo el árbol (p. ej. `kudawa-page-deploy` cada minuto actualizando `frontend/version.json`) provoca un **refresh completo del árbol de ~9.815 nodos** y, con él, un snapshot de ~2,9 MB.
- `watch` refresca con el `build` normal (`refresh.py:199-213`), es decir **sí** escribe historial.

**Amplificador:** la unidad de la máquina apunta a un árbol multi-proyecto (`~/Proyectos`, 30+ repos) con escrituras externas constantes → el producto D1×D2×D4 es un crecimiento sin cota.

---

## 2. Criterios de aceptación

| ID | Criterio | Verificación |
|---|---|---|
| CA1 | `maps/HISTORY` nunca supera `max_snapshots` (por defecto 20) por repositorio | test unitario de `podar()` + test de integración de `snapshot_map` |
| CA2 | Nunca supera `history_max_mb` (por defecto 512 MB) | test unitario con archivos sintéticos |
| CA3 | Un snapshot con contenido idéntico al último **no** crea archivo | test de `snapshot_map` ejecutado dos veces → 1 archivo |
| CA4 | Con menos de `history_min_free_mb` libres, `snapshot_map` devuelve `None`, registra WARNING y **no** escribe | test con `shutil.disk_usage` monkeypatcheado |
| CA5 | El watcher **no** dispara por `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CONTEXT.md`, `.cursorrules`, `.windsurfrules` | test de `_es_archivo_relevante` |
| CA6 | El watcher no refresca más de una vez cada `--min-interval-s` (defecto 60) y suprime los eventos generados durante el propio refresh | test de bucle con `max_iterations` |
| CA7 | El refresh del watcher **no** escribe nada en `maps/HISTORY` | test con `cmd_build` monkeypatcheado: `build_args.no_snapshot is True` |
| CA8 | `ctxmap history list` y `ctxmap history prune --keep N [--dry-run]` funcionan; `ctxmap doctor` reporta el estado del historial | tests de CLI + doctor |
| CA9 | Reproducción del incidente en sandbox: 50 builds seguidos → `maps/HISTORY` ≤ 20 archivos y sin crecimiento monótono | runbook §7 |
| CA10 | Cero regresiones: `uv run --with pytest pytest -q` mantiene los 2 fallos preexistentes y suma los nuevos tests | §7 |

---

## 3. Diseño

```
                     ┌──────────────────────────────────────────────┐
   ctxmap build ────▶│ snapshot_map()  (core/storage/store.py)      │
   ctxmap refresh    │  1. hay_espacio(min_free_mb)   ← history.py  │
   ctxmap wrap       │  2. es_duplicado(src)          ← history.py  │
                     │  3. copiar con nombre seguro                 │
                     │  4. podar(keep, max_mb)        ← history.py  │
                     └──────────────────────────────────────────────┘
   ctxmap watch ────▶ refresh(no_snapshot=True)  →  NO toca HISTORY
                       + filtro ARCHIVOS_GENERADOS
                       + min_interval_s + ventana de supresión
   ctxmap history list|prune  ──▶ history.py (misma lógica, control manual)
   ctxmap doctor ───────────────▶ check_history (WARN/FAIL + sugerencia)
```

**Decisiones**
1. Módulo nuevo en `core/storage/history.py` sin importar de `application/` (evita invertir las capas; define su propia constante `HISTORY_DIR = ".context-map/maps/HISTORY"`).
2. Valores por defecto seguros y **efectivos sin configurar nada**: 20 snapshots / 512 MB / 512 MB libres mínimos.
3. Nombres de snapshot con sufijo legible `-YYYYmmdd-HHMMSS` en caso de colisión (nunca `-2…-N` sin tope).
4. El daemon no escribe historial: el historial es un acto deliberado (build/refresh humano o hook de commit).
5. La poda elimina **solo** archivos `.md` con `os.remove` (nunca `rmtree`) y jamás borra el snapshot más reciente (`len(conservar) > 1`).
6. Todo cambio va con test primero (TDD) y commit por tarea, mensajes Conventional Commits en español.

---

## 4. Fase A — ContextMap (TDD, tarea por tarea)

### Tarea A0: rama, baseline y encuadre

**Objetivo:** partir de un estado conocido y reproducible.

**Archivos:** ninguno (preparación).

**Pasos**
1. `cd /home/jose/Proyectos/ContextMap && git checkout -b fix/history-retencion-watcher`
2. Registrar baseline: `uv run --with pytest --with pytest-mock pytest -q` → anotar `2 failed, 263 passed, 1 skipped`.
3. `uv run --with pytest --with pytest-mock pytest -q context_map/__tests__/test_watcher.py context_map/__tests__/test_doctor.py` → debe pasar en verde.

**Verificación:** rama creada, baseline anotado en el cuerpo del PR.
**Commit:** ninguno.

---

### Tarea A1: módulo `history.py` — métricas, huella y poda

**Objetivo:** disponer de la lógica de historial aislada y testeada (CA1, CA2).

**Archivos**
- Crear: `context_map/core/storage/history.py`
- Test: `context_map/__tests__/test_history.py`

**Paso 1 — escribir el test que falla**

```python
"""Tests de la gestión del historial de snapshots (retención y métricas)."""

from __future__ import annotations

import os
import time

from context_map.core.storage.history import (
    PodaResult,
    espacio_libre_mb,
    estadisticas,
    hay_espacio,
    huella_archivo,
    podar,
)


def _crear_snapshots(dir_hist, cantidad: int, peso: int = 1024) -> None:
    """Crea `cantidad` snapshots .md con mtime creciente."""
    dir_hist.mkdir(parents=True, exist_ok=True)
    for i in range(cantidad):
        f = dir_hist / f"snap-{i:03d}.md"
        f.write_bytes(b"x" * peso)
        os.utime(f, (time.time() + i, time.time() + i))


def test_estadisticas_cuenta_y_suma(tmp_path):
    """Cuenta archivos y bytes del historial."""
    _crear_snapshots(tmp_path, 3, peso=100)
    st = estadisticas(str(tmp_path))
    assert st.files == 3
    assert st.bytes == 300


def test_podar_por_cantidad_conserva_los_mas_recientes(tmp_path):
    """Conserva exactamente `keep` snapshots y borra los más antiguos."""
    _crear_snapshots(tmp_path, 10)
    res = podar(str(tmp_path), keep=4, max_mb=0)   # max_mb=0 desactiva el tope por tamaño
    assert isinstance(res, PodaResult)
    assert len(res.borrados) == 6
    assert res.restantes == 4
    nombres = sorted(p.name for p in tmp_path.glob("*.md"))
    assert nombres == ["snap-006.md", "snap-007.md", "snap-008.md", "snap-009.md"]


def test_podar_por_tamano_nunca_borra_el_mas_reciente(tmp_path):
    """Con un tope muy bajo deja al menos un archivo (el más reciente)."""
    _crear_snapshots(tmp_path, 5, peso=1024 * 1024)   # 1 MB cada uno
    res = podar(str(tmp_path), keep=99, max_mb=2)
    assert res.restantes == 2
    assert (tmp_path / "snap-004.md").exists()


def test_podar_dry_run_no_borra(tmp_path):
    """`dry_run` calcula la poda sin tocar el disco."""
    _crear_snapshots(tmp_path, 6)
    res = podar(str(tmp_path), keep=2, max_mb=0, dry_run=True)
    assert len(res.borrados) == 4
    assert len(list(tmp_path.glob("*.md"))) == 6


def test_podar_directorio_inexistente(tmp_path):
    """No explota si el historial no existe."""
    res = podar(str(tmp_path / "no-existe"), keep=5)
    assert res.borrados == []
    assert res.restantes == 0


def test_huella_archivo_es_estable(tmp_path):
    """La huella depende del contenido, no del nombre."""
    a = tmp_path / "a.md"; b = tmp_path / "b.md"
    a.write_text("contenido", encoding="utf-8")
    b.write_text("contenido", encoding="utf-8")
    assert huella_archivo(str(a)) == huella_archivo(str(b))
    b.write_text("otro", encoding="utf-8")
    assert huella_archivo(str(a)) != huella_archivo(str(b))


def test_hay_espacio_umbral(tmp_path):
    """`hay_espacio` respeta el umbral pedido."""
    assert hay_espacio(str(tmp_path), min_free_mb=1) is True
    assert isinstance(espacio_libre_mb(str(tmp_path)), float)
```

**Paso 2 — ejecutar y ver el fallo**

```bash
uv run --with pytest python -m pytest -q context_map/__tests__/test_history.py
# Esperado: ModuleNotFoundError / ImportError: cannot import name 'podar'
```

**Paso 3 — implementación mínima completa**

`context_map/core/storage/history.py`
```python
"""Gestión del historial de snapshots (`.context-map/maps/HISTORY/`).

Motivo (incidente 2026-10-13): `snapshot_map` copiaba el mapa completo en cada
`build`/`refresh` sin límite de cantidad ni de tamaño, sin deduplicado por
contenido y sin comprobar el espacio libre. Con `ctxmap watch` sobre un árbol
multi-proyecto con escrituras externas constantes el historial alcanzó
103.354 archivos / 148 GB y llenó la raíz del servidor.

Este módulo centraliza: métricas del historial, huella de contenido, poda por
cantidad y por tamaño, y comprobación de espacio libre. No importa nada de
`context_map.application` para no invertir las capas.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HISTORY_DIR: str = os.path.join(".context-map", "maps", "HISTORY")
KEEP_DEFAULT: int = 20
MAX_MB_DEFAULT: int = 512
MIN_FREE_MB_DEFAULT: int = 512


@dataclass
class HistoryStats:
    """Métricas del directorio de historial.

    Attributes:
        files (int): Cantidad de snapshots `.md`.
        bytes (int): Tamaño total en bytes.
    """

    files: int = 0
    bytes: int = 0

    @property
    def mb(self) -> float:
        """Tamaño total en megabytes (2 decimales)."""
        return round(self.bytes / (1024 * 1024), 2)


@dataclass
class PodaResult:
    """Resultado de una poda del historial.

    Attributes:
        borrados (List[str]): Rutas eliminadas (o que se eliminarían con dry-run).
        liberado_bytes (int): Bytes liberados.
        restantes (int): Snapshots que quedan tras la poda.
    """

    borrados: list[str] = field(default_factory=list)
    liberado_bytes: int = 0
    restantes: int = 0

    @property
    def liberado_mb(self) -> float:
        """Bytes liberados expresados en megabytes (2 decimales)."""
        return round(self.liberado_bytes / (1024 * 1024), 2)


def _snapshots(history_dir: str) -> list[tuple[float, int, str]]:
    """Lista los snapshots del historial ordenados del más nuevo al más viejo.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        List[Tuple[float, int, str]]: Tuplas `(mtime, tamaño, ruta)`.
    """
    if not os.path.isdir(history_dir):
        return []
    items: list[tuple[float, int, str]] = []
    with os.scandir(history_dir) as entradas:
        for entrada in entradas:
            if not entrada.is_file() or not entrada.name.endswith(".md"):
                continue
            try:
                st = entrada.stat()
            except OSError as err:  # carrera con la poda u otro proceso
                logger.debug("Snapshot ilegible %s: %s", entrada.path, err)
                continue
            items.append((st.st_mtime, st.st_size, entrada.path))
    items.sort(key=lambda t: t[0], reverse=True)
    return items


def estadisticas(history_dir: str = HISTORY_DIR) -> HistoryStats:
    """Calcula cantidad de snapshots y tamaño total del historial.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        HistoryStats: Métricas consolidadas.
    """
    items = _snapshots(history_dir)
    return HistoryStats(files=len(items), bytes=sum(size for _, size, _ in items))


def huella_archivo(path: str) -> str:
    """Calcula la huella MD5 truncada (12 hex) del contenido de un archivo.

    Args:
        path (str): Ruta del archivo.

    Returns:
        str: Huella hexadecimal de 12 caracteres, o cadena vacía si falla.
    """
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    except OSError as err:
        logger.warning("No se pudo calcular la huella de %s: %s", path, err)
        return ""


def huella_ultimo_snapshot(history_dir: str = HISTORY_DIR) -> str | None:
    """Devuelve la huella del snapshot más reciente.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        Optional[str]: Huella del último snapshot o None si no hay historial.
    """
    items = _snapshots(history_dir)
    if not items:
        return None
    return huella_archivo(items[0][2]) or None


def es_duplicado(src: str, history_dir: str = HISTORY_DIR) -> bool:
    """Indica si `src` tiene el mismo contenido que el último snapshot.

    Args:
        src (str): Ruta del mapa activo que se pretende copiar.
        history_dir (str): Ruta del directorio `maps/HISTORY`.

    Returns:
        bool: True si el contenido coincide con el último snapshot.
    """
    ultimo = huella_ultimo_snapshot(history_dir)
    if not ultimo:
        return False
    return huella_archivo(src) == ultimo


def espacio_libre_mb(path: str = ".") -> float:
    """Espacio libre del sistema de archivos que contiene `path`.

    Args:
        path (str): Ruta dentro del sistema de archivos a consultar.

    Returns:
        float: Megabytes libres (0.0 si la consulta falla).
    """
    try:
        uso = shutil.disk_usage(path)
    except OSError as err:
        logger.warning("No se pudo consultar el espacio libre de %s: %s", path, err)
        return 0.0
    return round(uso.free / (1024 * 1024), 2)


def hay_espacio(path: str = ".", min_free_mb: int = MIN_FREE_MB_DEFAULT) -> bool:
    """Comprueba que quede espacio mínimo libre antes de escribir.

    Args:
        path (str): Ruta dentro del sistema de archivos a consultar.
        min_free_mb (int): Megabytes libres mínimos exigidos.

    Returns:
        bool: True si hay al menos `min_free_mb` MB libres.
    """
    return espacio_libre_mb(path) >= float(min_free_mb)


def podar(
    history_dir: str = HISTORY_DIR,
    keep: int = KEEP_DEFAULT,
    max_mb: int = MAX_MB_DEFAULT,
    dry_run: bool = False,
) -> PodaResult:
    """Poda el historial por cantidad y por tamaño, sin tocar el más reciente.

    Reglas:
        1. Conserva los `keep` snapshots más recientes.
        2. Si el tamaño resultante supera `max_mb`, elimina los más antiguos
           de los conservados hasta cumplir, dejando siempre al menos uno.
        3. `max_mb <= 0` desactiva el tope por tamaño.

    Args:
        history_dir (str): Ruta del directorio `maps/HISTORY`.
        keep (int): Snapshots a conservar (mínimo 1).
        max_mb (int): Tope de tamaño en MB para el historial restante.
        dry_run (bool): Si es True solo calcula, no borra.

    Returns:
        PodaResult: Rutas borradas (o a borrar), bytes liberados y restantes.
    """
    items = _snapshots(history_dir)
    if not items:
        return PodaResult()

    keep = max(int(keep), 1)
    conservar = items[:keep]
    descartar = items[keep:]

    if max_mb and max_mb > 0:
        tope = int(max_mb) * 1024 * 1024
        total = sum(size for _, size, _ in conservar)
        while len(conservar) > 1 and total > tope:
            _, size, ruta = conservar.pop()
            descartar.append((0.0, size, ruta))
            total -= size

    resultado = PodaResult(restantes=len(conservar))
    for _, size, ruta in descartar:
        if not dry_run:
            try:
                os.remove(ruta)
            except OSError as err:
                logger.warning("No se pudo eliminar el snapshot %s: %s", ruta, err)
                continue
        resultado.borrados.append(ruta)
        resultado.liberado_bytes += size
    return resultado
```

**Paso 4 — ejecutar y ver el verde**

```bash
uv run --with pytest python -m pytest -q context_map/__tests__/test_history.py
# Esperado: 7 passed
```

**Paso 5 — commit**

```bash
git add context_map/core/storage/history.py context_map/__tests__/test_history.py
git commit -m "feat(storage): módulo de historial con poda por cantidad y tamaño"
```

---

### Tarea A2: guarda de disco en `snapshot_map` (CA4)

**Objetivo:** que el tool nunca vuelva a escribir con el disco al borde del colapso.

**Archivos**
- Modificar: `context_map/core/storage/store.py:128-179` (`snapshot_map`)
- Test: `context_map/__tests__/test_snapshot_history.py` (nuevo)

**Paso 1 — test que falla**

```python
"""Tests de snapshot_map con retención, deduplicado y guarda de disco."""

from __future__ import annotations

import os
import shutil

import pytest

from context_map.core.storage import store
from context_map.core.storage.history import HISTORY_DIR


@pytest.fixture
def proyecto(tmp_path, monkeypatch):
    """Prepara un proyecto mínimo con su `.context-map/maps/ACTIVE.md`."""
    monkeypatch.chdir(tmp_path)
    maps = tmp_path / ".context-map" / "maps"
    maps.mkdir(parents=True)
    (maps / "ACTIVE.md").write_text("# mapa\ncontenido inicial\n", encoding="utf-8")
    return tmp_path


def test_snapshot_omitido_sin_espacio(proyecto, monkeypatch, caplog):
    """Sin espacio libre no se crea snapshot y se registra la causa."""
    monkeypatch.setattr(
        store, "hay_espacio", lambda *a, **k: False, raising=True
    )
    with caplog.at_level("WARNING"):
        resultado = store.snapshot_map(name="prueba.md")
    assert resultado is None
    assert not os.path.exists(os.path.join(HISTORY_DIR, "prueba.md"))
    assert "Snapshot omitido" in caplog.text


def test_snapshot_duplicado_no_repite(proyecto):
    """Dos llamadas con el mismo contenido dejan un único snapshot."""
    primero = store.snapshot_map(name="dup.md")
    segundo = store.snapshot_map(name="dup.md")
    assert primero is not None
    assert segundo is None
    assert len(os.listdir(HISTORY_DIR)) == 1
```

**Paso 2 — ver el fallo**

```bash
uv run --with pytest python -m pytest -q context_map/__tests__/test_snapshot_history.py
# Esperado: FAIL en ambos (hoy se crean duplicados y no existe `hay_espacio` en store)
```

**Paso 3 — implementación**

En `context_map/core/storage/store.py`, ampliar los imports y `snapshot_map`:

```python
from context_map.core.storage.history import (
    HISTORY_DIR,
    MAX_MB_DEFAULT,
    MIN_FREE_MB_DEFAULT,
    KEEP_DEFAULT,
    es_duplicado,
    hay_espacio,
    podar,
    espacio_libre_mb,
)
```

```python
def snapshot_map(
    from_rel: str = "maps/ACTIVE.md",
    name: str | None = None,
    nodes: list[Node] | None = None,
    edges: list[Edge] | None = None,
    keep: int | None = None,
    max_mb: int | None = None,
    min_free_mb: int | None = None,
) -> str | None:
    """Guarda una copia de respaldo (snapshot) del mapa en `.context-map/maps/HISTORY/`.

    Guardas aplicadas (incidente 2026-10-13): nunca escribe si queda menos de
    ``min_free_mb`` MB libres, nunca duplica un contenido idéntico al último
    snapshot y poda el historial a ``keep`` elementos / ``max_mb`` MB.

    Args:
        from_rel (str): Origen relativo del mapa activo.
        name (Optional[str]): Nombre explícito para el snapshot.
        nodes (Optional[List[Node]]): Nodos del grafo.
        edges (Optional[List[Edge]]): Aristas del grafo.
        keep (Optional[int]): Snapshots a conservar (default de configuración).
        max_mb (Optional[int]): Tope de tamaño del historial en MB.
        min_free_mb (Optional[int]): Espacio libre mínimo exigido en MB.

    Returns:
        Optional[str]: Ruta del snapshot creado, o None si se omitió.
    """
    cfg = load_project_config(".")
    keep = KEEP_DEFAULT if keep is None else keep
    max_mb = MAX_MB_DEFAULT if max_mb is None else max_mb
    min_free_mb = MIN_FREE_MB_DEFAULT if min_free_mb is None else min_free_mb

    src = os.path.join(".context-map", from_rel)
    if not os.path.exists(src):
        return None

    # Guarda 1 — disco: jamás escribir con el sistema al borde del colapso.
    if not hay_espacio(".", min_free_mb=min_free_mb):
        logger.warning(
            "Snapshot omitido: solo %.0f MB libres (mínimo %s MB). Revisa maps/HISTORY",
            espacio_libre_mb("."),
            min_free_mb,
        )
        return None

    # Guarda 2 — contenido idéntico al último snapshot: no aporta historial.
    if es_duplicado(src, HISTORY_DIR):
        logger.info("Snapshot omitido: contenido idéntico al último snapshot")
        return None

    ...  # (nombre del snapshot: bloque de la tarea A3)

    _ensure(dst)
    try:
        shutil.copy2(src, dst)
    except Exception as err:
        logger.warning("No se pudo crear snapshot %s: %s", dst, err)
        return None

    # Guarda 3 — retención: el historial no puede crecer sin cota.
    res = podar(HISTORY_DIR, keep=int(keep), max_mb=int(max_mb))
    if res.borrados:
        logger.info(
            "Historial podado: %d snapshots eliminados (%.2f MB), %d restantes",
            len(res.borrados),
            res.liberado_mb,
            res.restantes,
        )
    return dst
```

**Paso 4 — verde**

```bash
uv run --with pytest python -m pytest -q context_map/__tests__/test_snapshot_history.py context_map/__tests__/test_history.py
# Esperado: 9 passed
```

**Paso 5 — commit**

```bash
git add context_map/core/storage/store.py context_map/__tests__/test_snapshot_history.py
git commit -m "feat(storage): omitir snapshots sin espacio libre o con contenido duplicado"
```

---

### Tarea A3: nombres de snapshot acotados (fin del bucle `-2…-N`) (CA2)

**Objetivo:** que una colisión de nombre no genere series infinitas.

**Archivos**
- Modificar: `context_map/core/storage/store.py:163-171`
- Test: `context_map/__tests__/test_snapshot_history.py` (añadir)

**Paso 1 — test que falla**

```python
def test_colision_de_nombre_usa_timestamp_y_acota(proyecto):
    """Ante colisión de nombre se sufija con timestamp, sin series -2..-N."""
    (proyecto / ".context-map" / "maps" / "HISTORY").mkdir(parents=True)
    (proyecto / ".context-map" / "maps" / "HISTORY" / "forzado.md").write_text(
        "otro contenido\n", encoding="utf-8"
    )
    primero = store.snapshot_map(name="forzado.md")
    assert primero is not None
    segundo = store.snapshot_map(name="forzado.md")
    # El segundo se omite por deduplicado; forzamos contenido nuevo
    (proyecto / ".context-map" / "maps" / "ACTIVE.md").write_text(
        "# mapa\ncontenido nuevo\n", encoding="utf-8"
    )
    tercero = store.snapshot_map(name="forzado.md")
    assert tercero is not None
    assert "-2.md" not in tercero
```

**Paso 2 — ver el fallo:** el sufijo actual es `forzado-2.md` → `assert` falla.

**Paso 3 — implementación**

```python
    dst = os.path.join(HISTORY_DIR, out_name)
    if os.path.exists(dst):
        base_name, ext = os.path.splitext(out_name)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dst = os.path.join(HISTORY_DIR, f"{base_name}-{ts}{ext}")
        contador = 2
        while os.path.exists(dst):  # colisión dentro del mismo segundo
            dst = os.path.join(HISTORY_DIR, f"{base_name}-{ts}-{contador}{ext}")
            contador += 1
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_snapshot_history.py` → `4 passed`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "fix(storage): nombres de snapshot con timestamp en vez de series -2..-N"
```

---

### Tarea A4: configuración declarativa de retención

**Objetivo:** parametrizar retención y guardas por proyecto sin tocar código.

**Archivos**
- Modificar: `context_map/core/models/config.py:8-17`
- Modificar: `context_map/core/storage/config_loader.py:29-60`
- Test: `context_map/__tests__/test_history_config.py` (nuevo)

**Paso 1 — test que falla**

```python
def test_config_historial_desde_contextmap_toml(tmp_path):
    (tmp_path / ".contextmap.toml").write_text(
        'project_name = "Demo"\nmax_snapshots = 3\nhistory_max_mb = 64\n'
        'history_min_free_mb = 128\nwatch_min_interval_s = 120\n',
        encoding="utf-8",
    )
    cfg = load_project_config(str(tmp_path))
    assert cfg.max_snapshots == 3
    assert cfg.history_max_mb == 64
    assert cfg.history_min_free_mb == 128
    assert cfg.watch_min_interval_s == 120


def test_config_historial_defaults(tmp_path):
    cfg = load_project_config(str(tmp_path))
    assert (cfg.max_snapshots, cfg.history_max_mb, cfg.watch_min_interval_s) == (20, 512, 60)
```

**Paso 2 — ver el fallo:** `AttributeError: 'ContextMapConfig' object has no attribute 'max_snapshots'`.

**Paso 3 — implementación**

`context_map/core/models/config.py`
```python
    mode: str = "hierarchical"
    brief_enabled: bool = True
    quiet: bool = False
    # Retención del historial (incidente 2026-10-13: 148 GB en maps/HISTORY)
    max_snapshots: int = 20
    history_max_mb: int = 512
    history_min_free_mb: int = 512
    # Watcher
    watch_min_interval_s: int = 60
```

`context_map/core/storage/config_loader.py` — en ambos bloques (`.contextmap.toml` y `[tool.contextmap]`):
```python
                config.max_snapshots = int(data.get("max_snapshots", config.max_snapshots))
                config.history_max_mb = int(data.get("history_max_mb", config.history_max_mb))
                config.history_min_free_mb = int(
                    data.get("history_min_free_mb", config.history_min_free_mb)
                )
                config.watch_min_interval_s = int(
                    data.get("watch_min_interval_s", config.watch_min_interval_s)
                )
```

Y en `snapshot_map` (tarea A2) tomar los defaults de la config:
```python
    keep = KEEP_DEFAULT if keep is None else keep
    max_mb = cfg.history_max_mb if max_mb is None else max_mb
    min_free_mb = cfg.history_min_free_mb if min_free_mb is None else min_free_mb
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_history_config.py` → `2 passed`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "feat(config): parámetros de retención del historial y del watcher"
```

---

### Tarea A5: watcher — filtrar salidas propias (CA5)

**Objetivo:** que el daemon no se dispare con los archivos que él mismo (u otro generador agéntico) produce.

**Archivos**
- Modificar: `context_map/domain/synchronization/watcher.py:17-28`
- Test: `context_map/__tests__/test_watcher.py` (ampliar `test_es_archivo_relevante`)

**Paso 1 — test que falla** (añadir a `test_watcher.py`)

```python
def test_es_archivo_relevante_ignora_salidas_generadas():
    """Las salidas de gobernanza generadas no disparan el watcher."""
    from context_map.domain.synchronization.watcher import _es_archivo_relevante

    for nombre in ("AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONTEXT.md",
                   ".cursorrules", ".windsurfrules", "version.json"):
        assert not _es_archivo_relevante(f"/proyecto/{nombre}"), nombre
    assert _es_archivo_relevante("/proyecto/src/app.py")
```

Nota: `version.json` es el artefacto que `kudawa-page-deploy` reescribe cada minuto; si algún proyecto lo necesita como fuente, se puede re-habilitar por config (`watch_extra_files`), fuera del alcance de este plan.

**Paso 2 — ver el fallo:** `assert not _es_archivo_relevante("/proyecto/AGENTS.md")` → falla.

**Paso 3 — implementación**

```python
EXTENSIONES_MONITOREADAS = {".py", ".md", ".json", ".toml", ".yaml", ".yml", ".txt"}
DIRECTORIOS_EXCLUIDOS = {".context-map", ".git", "__pycache__", ".venv", "venv", "node_modules", ".pytest_cache"}
#: Salidas que genera ContextMap (u otros agentes) y que NO deben re-disparar el daemon.
ARCHIVOS_GENERADOS = {
    "AGENTS.md", "CLAUDE.md", "GEMINI.md", "CONTEXT.md",
    ".cursorrules", ".windsurfrules", "version.json",
}


def _es_archivo_relevante(path: str) -> bool:
    """Comprueba si el archivo modificado debe disparar la sincronización.

    Args:
        path (str): Ruta del archivo modificado.

    Returns:
        bool: True si el archivo debe provocar un refresco.
    """
    norm_path = path.replace("\\", "/")
    parts = norm_path.split("/")
    if any(p in DIRECTORIOS_EXCLUIDOS for p in parts):
        return False
    if os.path.basename(norm_path) in ARCHIVOS_GENERADOS:
        return False
    ext = os.path.splitext(path)[1].lower()
    return ext in EXTENSIONES_MONITOREADAS
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_watcher.py` → verde.

**Paso 5 — commit**

```bash
git add -A && git commit -m "fix(watcher): ignorar AGENTS.md/CLAUDE.md/CONTEXT.md y salidas generadas"
```

---

### Tarea A6: watcher — intervalo mínimo y ventana de supresión (CA6)

**Objetivo:** que el daemon no pueda saturar el refresco aunque algo escriba cada segundo.

**Archivos**
- Modificar: `context_map/domain/synchronization/watcher.py:52-155`
- Modificar: `context_map/application/commands/watch.py` (flags)
- Modificar: `context_map/application/cli/parser.py:154-157` (`watch`)
- Test: `context_map/__tests__/test_watcher.py` (ampliar)

**Paso 1 — test que falla**

```python
def test_watcher_respeta_intervalo_minimo(tmp_path, monkeypatch):
    """No refresca más de una vez cada `min_interval_s` segundos."""
    (tmp_path / "app.py").write_text("print('a')", encoding="utf-8")
    llamadas = []

    def _cb(ruta):
        llamadas.append(ruta)
        # durante el refresh se escribe un archivo: no debe contar
        (tmp_path / "AGENTS.md").write_text("x", encoding="utf-8")
        (tmp_path / "src_nuevo.py").write_text("print('b')", encoding="utf-8")

    iniciar_watcher(
        str(tmp_path), debounce_ms=10, callback=_cb, max_iterations=40,
        min_interval_s=1,
    )
    assert len(llamadas) == 1
```

**Paso 2 — ver el fallo:** `TypeError: iniciar_watcher() got an unexpected keyword argument 'min_interval_s'`.

**Paso 3 — implementación**

Firma y `Handler`:
```python
def iniciar_watcher(
    project_dir: str = ".",
    debounce_ms: int = 500,
    callback: Callable[[str], None] | None = None,
    max_iterations: int = 0,
    min_interval_s: int = 60,
) -> None:
    """Inicia el escuchador de eventos del sistema de archivos con debouncing.

    Args:
        project_dir (str): Directorio raíz a monitorear.
        debounce_ms (int): Espera tras la última modificación, en ms.
        callback (Callable): Función a invocar tras el debounce.
        max_iterations (int): Iteraciones máximas del bucle (0 = infinito).
        min_interval_s (int): Segundos mínimos entre refrescos consecutivos.
    """
```
```python
        class Handler(FileSystemEventHandler):
            def __init__(self) -> None:
                self.last_change = 0.0
                self.suprimir_hasta = 0.0  # ventana en la que ignoramos nuestro propio output

            def on_any_event(self, event) -> None:
                if event.is_directory:
                    return
                if time.time() < self.suprimir_hasta:
                    return
                if _es_archivo_relevante(event.src_path):
                    self.last_change = time.time()
```
Bucle watchdog:
```python
        last_processed = 0.0
        ultimo_refresco = 0.0
        iterations = 0
        while True:
            time.sleep(0.1)
            now = time.time()
            if (
                event_handler.last_change > 0
                and (now - event_handler.last_change) >= (debounce_ms / 1000.0)
                and event_handler.last_change > last_processed
                and (now - ultimo_refresco) >= min_interval_s
            ):
                last_processed = now
                ultimo_refresco = now
                event_handler.suprimir_hasta = now + min_interval_s
                cb(project_dir)
```
Fallback polling: mismas dos condiciones y la misma ventana (`suprimir_hasta` se implementa como variable local `suprimir_hasta`).

`watch.py` y parser:
```python
    min_interval_s = int(args.get("min_interval_s") or 60)
    print(f"   Intervalo mínimo entre refrescos: {min_interval_s}s")
    ...
    iniciar_watcher(project_dir=target_dir, debounce_ms=debounce_ms, min_interval_s=min_interval_s)
```
```python
    s_watch.add_argument("--debounce-ms", type=int, default=500, help="Tiempo en ms a esperar tras modificaciones (default: 500)")
    s_watch.add_argument("--min-interval-s", type=int, default=60, dest="min_interval_s",
                         help="Segundos mínimos entre refrescos (default: 60)")
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_watcher.py`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "fix(watcher): intervalo mínimo y ventana de supresión de eventos propios"
```

---

### Tarea A7: el watcher no escribe historial (CA7)

**Objetivo:** cortar el escritor que llenó el disco en su origen.

**Archivos**
- Modificar: `context_map/application/commands/build.py:140-143`
- Modificar: `context_map/application/cli/parser.py` (`build` y `refresh`)
- Modificar: `context_map/application/commands/refresh.py:199-213`
- Modificar: `context_map/domain/synchronization/watcher.py:44-49`
- Test: `context_map/__tests__/test_watcher.py` y `context_map/__tests__/test_cli.py` (ampliar)

**Paso 1 — test que falla**

```python
def test_ejecutar_refresco_default_no_escribe_historial(tmp_path, monkeypatch):
    """El refresco del daemon pide `no_snapshot=True` al build."""
    from context_map.application.commands import refresh as refresh_module
    from context_map.domain.synchronization.watcher import _ejecutar_refresco_default

    capturado = {}

    def _fake_cmd_build(args):
        capturado["no_snapshot"] = getattr(args, "no_snapshot", None)
        capturado["target"] = getattr(args, "target", None)

    monkeypatch.setattr(refresh_module, "cmd_build", _fake_cmd_build)
    monkeypatch.setattr(refresh_module, "cmd_scan", lambda args: None)
    monkeypatch.setattr(refresh_module, "cmd_check", lambda args: None)
    monkeypatch.chdir(tmp_path)

    _ejecutar_refresco_default(str(tmp_path))
    assert capturado["no_snapshot"] is True
```

**Paso 2 — ver el fallo:** `assert None is True`.

**Paso 3 — implementación**

Parser (`build` y `refresh`):
```python
    s_build.add_argument("--no-snapshot", action="store_true", dest="no_snapshot",
                         help="No crear snapshot en maps/HISTORY (modo daemon/CI)")
    ...
    s_refresh.add_argument("--no-snapshot", action="store_true", dest="no_snapshot",
                           help="No crear snapshot en maps/HISTORY (modo daemon/CI)")
```
`build.py`:
```python
    # Snapshot (omitido en modo daemon: el historial es un acto deliberado)
    if getattr(args, "no_snapshot", False):
        print("snapshot: omitido (--no-snapshot)")
    else:
        snapshot_name = getattr(args, "snapshot_name", "") or None
        snap = snapshot_map(nodes=nodes, edges=edges, name=snapshot_name)
        if snap:
            print(f"snapshot: {snap}")
```
`refresh.py` (bloque `build_args`):
```python
        build_args = types.SimpleNamespace(
            target=".",
            project=proj,
            brief=True,
            mode=vault_mode,
            raw=False,
            clean=False,
            quiet=True,
            import_sessions=False,
            snapshot_name="",
            no_snapshot=getattr(args, "no_snapshot", False),
        )
```
`watcher.py`:
```python
        args = argparse.Namespace(
            target=project_dir, project=None, quiet=True, no_snapshot=True
        )
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_watcher.py context_map/__tests__/test_cli.py`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "feat(build): flag --no-snapshot; el watcher deja de escribir historial"
```

---

### Tarea A8: comando `ctxmap history list|prune` (CA8)

**Objetivo:** dar control manual e inspección del historial, sin depender de scripts externos.

**Archivos**
- Crear: `context_map/application/commands/history_cmd.py`
- Modificar: `context_map/application/cli/parser.py` (nuevo subparser `history`)
- Modificar: `context_map/application/cli/cli.py:104-130` (dispatch + import)
- Test: `context_map/__tests__/test_history_cmd.py` (nuevo)

**Paso 1 — test que falla**

```python
"""Tests del comando `ctxmap history`."""

from __future__ import annotations

import json
import time

from context_map.application.commands.history_cmd import cmd_history


def _hist(tmp_path, n=30):
    d = tmp_path / ".context-map" / "maps" / "HISTORY"
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        f = d / f"snap-{i:03d}.md"
        f.write_bytes(b"x" * 2048)
        os.utime(f, (time.time() + i, time.time() + i))
    return d


def test_history_list_json(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _hist(tmp_path, 5)
    cmd_history({"action": "list", "target_dir": ".", "json": True})
    datos = json.loads(capsys.readouterr().out)
    assert datos["files"] == 5


def test_history_prune_keep_y_dry_run(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    d = _hist(tmp_path, 8)
    cmd_history({"action": "prune", "target_dir": ".", "keep": 3, "dry_run": True})
    assert len(list(d.glob("*.md"))) == 8          # dry-run no borra
    cmd_history({"action": "prune", "target_dir": ".", "keep": 3, "dry_run": False})
    assert len(list(d.glob("*.md"))) == 3
```

**Paso 2 — ver el fallo:** `ModuleNotFoundError: context_map.application.commands.history_cmd`.

**Paso 3 — implementación**

`context_map/application/commands/history_cmd.py`
```python
"""Comando CLI 'history' para inspeccionar y podar `.context-map/maps/HISTORY/`."""

from __future__ import annotations

import json
from typing import Any

from context_map.core.storage.history import (
    HISTORY_DIR,
    MAX_MB_DEFAULT,
    podar,
    estadisticas,
)


def cmd_history(args: dict[str, Any]) -> None:
    """Manejador del comando `ctxmap history <list|prune>`.

    Args:
        args (Dict[str, Any]): Argumentos parseados de CLI.
    """
    accion = (args.get("action") or "list").lower()
    as_json = bool(args.get("json", False))
    stats = estadisticas(HISTORY_DIR)

    if accion == "list":
        if as_json:
            print(json.dumps(
                {"dir": HISTORY_DIR, "files": stats.files, "bytes": stats.bytes,
                 "mb": stats.mb, "keep": int(args.get("keep") or 0)}, indent=2, ensure_ascii=False))
            return
        print(f"\n🗂️  Historial: {HISTORY_DIR}")
        print(f"   Snapshots: {stats.files} · Tamaño: {stats.mb} MB")
        return

    if accion == "prune":
        res = podar(
            HISTORY_DIR,
            keep=int(args.get("keep") or 20),
            max_mb=int(args.get("max_mb") or MAX_MB_DEFAULT),
            dry_run=bool(args.get("dry_run", False)),
        )
        if as_json:
            print(json.dumps(
                {"borrados": len(res.borrados), "liberado_mb": res.liberado_mb,
                 "restantes": res.restantes, "dry_run": bool(args.get("dry_run", False))},
                indent=2, ensure_ascii=False))
            return
        etiqueta = "(simulación)" if args.get("dry_run") else ""
        print(f"🧹 Poda {etiqueta}: {len(res.borrados)} snapshots · {res.liberado_mb} MB · {res.restantes} restantes")
        return

    print(f"⚠️  Acción desconocida: {accion}. Usa 'list' o 'prune'.")
```

Parser (dentro de `build_parser`):
```python
    s_hist = sub.add_parser("history", help="Inspecciona y poda el historial de snapshots (maps/HISTORY)")
    s_hist.add_argument("action", nargs="?", choices=["list", "prune"], default="list",
                        help="Acción: list (por defecto) o prune")
    s_hist.add_argument("--keep", type=int, default=20, help="Snapshots a conservar en prune (default: 20)")
    s_hist.add_argument("--max-mb", type=int, default=512, dest="max_mb",
                        help="Tope de tamaño del historial en MB (default: 512)")
    s_hist.add_argument("--dry-run", action="store_true", dest="dry_run",
                        help="Simula la poda sin borrar")
    s_hist.add_argument("--json", action="store_true", help="Salida JSON")
```
`cli.py`:
```python
    from context_map.application.commands.history_cmd import cmd_history
    ...
        "history": lambda a: _dispatch_cmd(cmd_history, a),
```

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_history_cmd.py` → `2 passed`. Prueba manual: `ctxmap history list` y `ctxmap history prune --dry-run`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "feat(cli): comando history list|prune para el historial de snapshots"
```

---

### Tarea A9: `doctor` vigila el historial (CA8)

**Objetivo:** que el fallo sea visible antes de llenar el disco.

**Archivos**
- Modificar: `context_map/domain/health/doctor.py` (nuevo `check_history` + registro en `CHECKS`)
- Test: `context_map/__tests__/test_doctor.py` (ampliar)

**Paso 1 — test que falla**

```python
def test_check_history_avisa_con_historial_grande(tmp_path, monkeypatch):
    """`doctor` marca WARN si el historial supera el umbral configurado."""
    from context_map.domain.health import doctor

    hist = tmp_path / ".context-map" / "maps" / "HISTORY"
    hist.mkdir(parents=True)
    for i in range(5):
        (hist / f"s{i}.md").write_bytes(b"x" * 1024)

    monkeypatch.setattr(doctor, "estadisticas", lambda *a, **k: doctor.HistoryStats(files=5, bytes=10 * 1024 * 1024))
    report = doctor.DoctorReport()
    doctor.check_history(report, fix=False, project_dir=str(tmp_path))
    assert report.checks[0].status == "WARN"
    assert "history prune" in report.checks[0].message
```
(El test importa `HistoryStats` desde `doctor`, que lo re-exporta: `from context_map.core.storage.history import HistoryStats, estadisticas`.)

**Paso 2 — ver el fallo:** `AttributeError: module 'context_map.domain.health.doctor' has no attribute 'check_history'`.

**Paso 3 — implementación**

```python
def check_history(report: DoctorReport, fix: bool = False, project_dir: str = ".") -> None:
    """Verifica el tamaño del historial de snapshots y ofrece poda.

    Args:
        report (DoctorReport): Reporte donde registrar el chequeo.
        fix (bool): Si es True aplica la poda con los valores por defecto.
        project_dir (str): Directorio del proyecto a diagnosticar.
    """
    hist = os.path.join(project_dir, HISTORY_DIR)
    stats = estadisticas(hist)

    if stats.files == 0:
        report.add(DoctorCheck("history", "OK", "Sin snapshots en maps/HISTORY"))
        return

    if stats.mb > MAX_MB_DEFAULT or stats.files > KEEP_DEFAULT * 5:
        mensaje = (
            f"{stats.files} snapshots / {stats.mb} MB — por encima del umbral "
            f"({KEEP_DEFAULT} snapshots, {MAX_MB_DEFAULT} MB). Ejecuta `ctxmap history prune`."
        )
        if fix:
            res = podar(hist, keep=KEEP_DEFAULT, max_mb=MAX_MB_DEFAULT)
            report.add(DoctorCheck(
                "history", "OK" if res.restantes else "WARN", mensaje,
                fix_applied=True,
                fix_message=f"{len(res.borrados)} borrados · {res.liberado_mb} MB liberados",
            ))
            return
        report.add(DoctorCheck("history", "WARN", mensaje))
        return

    report.add(DoctorCheck("history", "OK", f"{stats.files} snapshots / {stats.mb} MB"))
```
Y en la lista `CHECKS` (doctor.py:283-292) agregar `check_history`.

**Paso 4 — verde:** `uv run --with pytest python -m pytest -q context_map/__tests__/test_doctor.py`.

**Paso 5 — commit**

```bash
git add -A && git commit -m "feat(doctor): chequeo de tamaño del historial con poda opcional"
```

---

### Tarea A10: documentación, CHANGELOG y release v2.5.0

**Archivos**
- Modificar: `pyproject.toml:7` → `version = "2.5.0"`
- Modificar: `CHANGELOG.md` (entrada `## [2.5.0]`)
- Modificar: `README.md` (sección «Historial de snapshots y retención»: `max_snapshots`, `history_max_mb`, `history_min_free_mb`, `ctxmap history prune`, `--no-snapshot`, `watch --min-interval-s`)
- Modificar: `docs/` (si existe página de comandos, añadir `history`)
- Modificar: skill `contextmap` (`.hermes/skills/devops/contextmap/SKILL.md`) — ampliar el pitfall ya registrado con la versión corregida y los nuevos comandos

**Pasos**
1. Escribir las entradas de CHANGELOG (Added / Fixed con el incidente y su mitigación).
2. `uv run --with pytest --with pytest-mock pytest -q` → sin regresiones.
3. Instalar local para validar la feature antes del push:
   ```bash
   uv tool install --force /home/jose/Proyectos/ContextMap
   ctxmap --version          # esperado: 2.5.0
   ctxmap history list
   ```
4. Commit + push de la rama + PR (skill `github-pr-workflow`):
   ```bash
   git add -A && git commit -m "chore(release): v2.5.0 — retención de historial y watcher seguro"
   git push -u origin fix/history-retencion-watcher
   gh pr create --fill --title "fix: retención del historial y watcher seguro (incidente 148 GB)"
   ```
5. Tras el merge y el tag: `uv tool install --force git+https://github.com/kudawasama/ContextMap.git@v2.5.0` para dejar el binario global en la versión publicada.

**Verificación:** `ctxmap --version` = 2.5.0 y `ctxmap history list` operativo.

---

## 5. Fase B — hardening del host (Ubuntu 24.04 «kudawa»)

| # | Tarea | Estado | Comando / archivo |
|---|---|---|---|
| B1 | Detener y deshabilitar el daemon responsable | **HECHO** | `systemctl --user stop ctxmap-watch.service && systemctl --user disable ctxmap-watch.service` |
| B2 | Vaciar `maps/HISTORY` conservando muestra e inventario | **HECHO** | `find … -print0 \| xargs -0 -n 2000 rm -f --`; muestra en `~/backups/ctxmap-history-sample/` |
| B3 | Limitar el journal del sistema | **HECHO** | `journalctl --vacuum-size=300M` + `/etc/systemd/journald.conf.d/limite.conf` (`SystemMaxUse=300M`) — 4,0 GB → 251 MB |
| B4 | Poda automática del historial (script + timer de usuario) | **HECHO** | `~/bin/ctxmap-history-prune.sh` (keep 20, alerta >2 GB) + `ctxmap-history-prune.timer` (diario). Reemplazable por `ctxmap history prune` cuando A8 esté publicado |
| B5 | Borrar `/var/log/syslog.1` (679 MB de flood ctxmap+tailscale) | **PENDIENTE (requiere aprobación)** | `sudo rm -f /var/log/syslog.1 /var/log/kern.log.1 /var/log/user.log.1` |
| B6 | Dejar coherente `/etc/logrotate.d/rsyslog`: quitar `daily` duplicado junto a `weekly` y añadir `su root syslog` (hoy avisa «parent directory has insecure permissions» por `/var/log` en `root:syslog`) | **PENDIENTE (requiere aprobación)** | bloque `{ su root syslog; rotate 7; maxsize 100M; weekly; … }` + `sudo logrotate -d /etc/logrotate.d/rsyslog` sin errores |
| B7 | Revisar cadencia de `kudawa-page-deploy.timer` (git pull cada 60 s: ruido y CPU; fue el disparador externo del bucle) | **DECISIÓN DEL USUARIO** | `/etc/systemd/system/kudawa-page-deploy.timer` → `OnUnitActiveSec=5min` |
| B8 | Reclamar imágenes Docker sin uso (26,21 GB reclamables de 28,62 GB, 24 contenedores vivos) | **DECISIÓN DEL USUARIO** | `docker image prune -a` tras revisar `docker images` |
| B9 | Re-activar el daemon | **SOLO TRAS A6+A7** | `systemctl --user enable --now ctxmap-watch.service` con `--min-interval-s 60`, y nunca sobre `~/Proyectos` (árbol multi-proyecto). Alternativa recomendada: timer `OnCalendar=*:0/15` ejecutando `ctxmap refresh <proyecto>` por repo |
| B10 | Verificación final del host | **PENDIENTE** | `df -h /` ≥ 100 GB libres, `du -sh ~/Proyectos/.context-map` ≤ 300 MB, `systemctl --user list-timers` con la poda activa |

---

## 6. Runbook de verificación y aceptación

```bash
# 1. Suite completa sin regresiones (esperado: 2 failed preexistentes, todo lo demás verde)
cd /home/jose/Proyectos/ContextMap
uv run --with pytest --with pytest-mock --quiet pytest -q

# 2. Sólo lo nuevo
uv run --with pytest python -m pytest -q \
  context_map/__tests__/test_history.py \
  context_map/__tests__/test_snapshot_history.py \
  context_map/__tests__/test_history_config.py \
  context_map/__tests__/test_history_cmd.py \
  context_map/__tests__/test_watcher.py \
  context_map/__tests__/test_doctor.py

# 3. Reproducción del incidente en sandbox (CA9): 50 builds seguidos con el tool instalado
rm -rf /tmp/ctxmap-sandbox && mkdir -p /tmp/ctxmap-sandbox && cd /tmp/ctxmap-sandbox
ctxmap init . >/dev/null
for i in $(seq 1 50); do
  echo "print($i)" >> app.py
  ctxmap build . --quiet >/dev/null
done
ls -1 .context-map/maps/HISTORY | wc -l        # esperado: <= 20 (antes: crecía sin cota)
du -sh .context-map/maps/HISTORY               # esperado: pocos MB

# 4. Guarda de disco (CA4) — se valida con test monkeypatcheado, no se prueba llenando el disco

# 5. Herramientas nuevas
ctxmap history list
ctxmap history prune --dry-run
ctxmap doctor | grep -i history

# 6. Host (tras B5–B8)
df -h / ; sudo journalctl --disk-usage ; ls -1 /home/jose/Proyectos/.context-map/maps/HISTORY | wc -l
```

---

## 7. Riesgos, reversibilidad y decisiones abiertas

| Riesgo | Mitigación |
|---|---|
| La poda borra historial que el usuario quería conservar | `keep=20` + `max_mb=512` por defecto, `--dry-run`, y la poda **nunca** elimina el snapshot más reciente. Todo el historial es regenerable desde `state/graph.jsonl` + `raw/events.jsonl` |
| El deduplicado oculta la cadencia real de builds | El log INFO registra cada omisión (`Snapshot omitido: contenido idéntico…`); el conteo de refrescos sigue disponible en el journal |
| Romper expectativas del sufijo `-2…-N` | Ningún test ni documentación del repo referencia ese patrón (verificado con `grep -rn "snapshot_map\|-2.md" context_map/__tests__` → sin resultados) |
| `version.json` deja de disparar el watcher en algún proyecto real | Re-habilitable por config (`watch_extra_files`, trabajo futuro); en el caso del servidor era justamente el disparador del bucle |
| Re-activar `ctxmap watch` sobre `~/Proyectos` reproduce el fallo | B9 lo condiciona a A6+A7 y desaconseja el árbol multi-proyecto; el timer por proyecto es la alternativa soportada |
| `docker image prune -a` borra una imagen que se quería conservar | Solo imágenes sin contenedor asociado; revisar la lista antes (B8) |
| `su root syslog` mal aplicado en logrotate | Copia de seguridad `/etc/logrotate.d/rsyslog.bak.20261013` + validación con `logrotate -d` antes de confiar |

**Decisiones abiertas (responder antes de A10)**
1. ¿`max_snapshots=20` o se prefiere historial por tiempo (p. ej. 30 días)?
2. ¿Debe `--no-snapshot` ser el comportamiento **por defecto** de `ctxmap refresh` (el snapshot explícito se hace con `build`)?
3. ¿Vale la pena un `ctxmap history export <archivo.tar.zst>` para archivar el historial antes de podar?
4. Cadencia final de `kudawa-page-deploy.timer` (B7) y si se autoriza `docker image prune -a` (B8).

---

## 8. Orden de ejecución sugerido

```
A0 → A1 → A2 → A3 → A4 → A5 → A6 → A7 → A8 → A9 → A10      (código, TDD, un commit por tarea)
B5, B6 (aprobación)  → B7, B8 (decisión)  → B9 (solo con v2.5.0 instalada) → B10
```

Ruta del plan: `/home/jose/.hermes/plans/2026-10-13_214500-contextmap-historial-retencion-y-watcher.md`
Para versionarlo con el código: copiar a `/home/jose/Proyectos/ContextMap/docs/plans/2026-10-13-retencion-historial.md` y commitear con `docs: plan de retención de historial y watcher seguro`.

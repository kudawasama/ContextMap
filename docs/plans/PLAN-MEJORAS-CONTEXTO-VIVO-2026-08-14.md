---
type: plan
status: activo
preserve: true
concept: MEJORAS
created: 2026-08-14T15:10:00
updated: 2026-08-14T15:10:00
project: "ContextMap"
tags: ["manual", "plan", "implementacion", "contexto-vivo", "auditoria"]
---

# 🗺️ Plan de Mejoras — Contexto Vivo (auditoría 2026-08-14)

> **Origen**: auditoría de las últimas 30h de uso real (Gobernanza, mi-app-utm,
> CotanoPet, ContextMap). Hallazgos: el contexto se queda atrás cuando el agente
> no recuerda refrescar, el diario se llena de ruido del scanner, y las
> decisiones detectadas en sesiones no se clasifican. Este plan convierte esos
> síntomas en funcionalidad de ContextMap.
>
> **Fuente de verdad**: `7.0-MANUAL/BACKLOG.md` + diario más reciente.

---

## 🎯 Objetivo

Que **el contexto no se quede atrás solo**: ContextMap debe detectar actividad
(commits + sesiones) posterior al último build, auto-importar la memoria viva en
cada commit, y registrar lo conversado con calidad (diario sin ruido, decisiones
clasificadas, títulos legibles).

## 📊 Vista general de etapas

| # | Etapa | Prioridad | Estado | Entregable |
|---|-------|-----------|--------|------------|
| 1 | Señal de frescura en `check` (R1) | 🔴 Alta | ✅ Completa (`4eaa088`) | `check` avisa: N commits / N sesiones sin importar |
| 2 | Memoria viva en pre-commit (R2) | 🔴 Alta | ✅ Completa (`f4560d6`) | Cada commit importa sesiones + build |
| 3 | Diario sin ruido: consolidar bloques scanner (R4) | 🟠 Media | ✅ Completa (`d2730f5`) | 1 solo bloque autogenerado por día |
| 4 | Títulos legibles en el diario (R5) | 🟠 Media | ✅ Completa (`d2730f5`) | Sin truncado a 60 chars |
| 5 | Clasificar decisiones/lecciones en sesiones (R6) | 🟠 Media | ✅ Completa (`0b8f9b3`) | Nodos DECISION/CORRECCION/LECCION sugeridos |
| 6 | Comando `ctxmap wrap` (fin de sesión) (R3) | 🟠 Media | ✅ Completa (`9470146`) | refresh + resumen "registrado vs sin importar" |
| 7 | Métrica de memoria viva en `check` (R7) | 🟡 Baja | ✅ Completa (`cdfe3c8`) | % sesiones recientes con eventos |
| 8 | Validar consistencia del nombre del proyecto (R8) | 🟡 Baja | ✅ Completa (`cdfe3c8`) | Aviso vault-<X> ≠ project ≠ repo |
| 9 | Sugerir limpieza de temporales en refresh (R9) | 🟡 Baja | ✅ Completa (`cdfe3c8`) | Aviso `piloto_*/scripts/debug` sin trackear |
| 10 | Reconocer catálogo de reglas de negocio (R10) | 🟠 Media | ⬜ Pendiente | Nodos REGLA + sección en brief (fuente: references/reglas/) |

---

## ✅ ETAPA 10 — Reconocer catálogo de reglas de negocio (R10)

> **Origen**: pregunta del usuario (2026-08-14) — ¿guardar las reglas de Gobernanza
> en ContextMap? Respuesta: la fuente vive en el REPO del proyecto
> (`references/reglas/reglas_registro.yaml` + normas generadas), NO en el vault
> (que se regenera y no se versiona). ContextMap debe **reflejarlas**: detectar
> el catálogo, crear nodos `REGLA` y mostrarlo en el brief.

**Objetivo**: cuando un proyecto tiene un catálogo de reglas de negocio en
`<repo>/references/reglas/reglas_registro.yaml` (convención Gobernanza), el
scan/build lo detecta, registra los nodos `REGLA` (con ID jerárquico,
categoría, prioridad, estado) y el brief añade una sección "Reglas de Negocio"
con el conteo por categoría y la ruta de la fuente única de verdad.

### Archivos
- Modify: `context_map/domain/scanning/scanner.py` (detectar YAML de reglas)
- Create: `context_map/domain/reglas/reglas.py` (parser del catálogo → nodos)
- Modify: `context_map/presentation/briefs/generadores.py` (sección en brief)
- Modify: `context_map/application/cli/parser.py` (flag `--reglas` en scan/build opcional)
- Test: `context_map/__tests__/test_reglas_catalogo.py` (nuevo)

### Task 10.1: test que falla (parser)
```python
"""El catálogo de reglas se parsea a nodos REGLA (R10, 2026-08-14)."""
from __future__ import annotations

from context_map.domain.reglas.reglas import parsear_catalogo


def test_parsea_yaml_de_reglas(tmp_path):
    yaml_path = tmp_path / "reglas_registro.yaml"
    yaml_path.write_text("""
version: 1.0
proyecto: "MiProyecto"
reglas:
  - id: REG-ING-001
    nombre: "DB activa"
    categoria: REG-ING
    categoria_nombre: "Ingesta DTE"
    prioridad: critica
    estado: implementada
    norma: "REG-ING-001_db_activa.md"
  - id: REG-ATR-001
    nombre: "Atribución CC"
    categoria: REG-ATR
    categoria_nombre: "Atribución CC"
    prioridad: critica
    estado: implementada
    norma: "REG-ATR-001_4_niveles.md"
""", encoding="utf-8")
    reglas = parsear_catalogo(str(yaml_path))
    assert len(reglas) == 2
    assert reglas[0]["id"] == "REG-ING-001"
    assert reglas[0]["categoria_nombre"] == "Ingesta DTE"


def test_sin_catalogo_devuelve_vacio(tmp_path):
    assert parsear_catalogo(str(tmp_path / "no-existe.yaml")) == []
```

### Task 10.2: test que falla (scanner registra nodos)
```python
"""El scan registra nodos REGLA cuando existe el catálogo (R10)."""
from __future__ import annotations

from context_map.domain.reglas.reglas import nodos_regla_desde_catalogo


def test_nodos_regla_desde_catalogo(tmp_path):
    yaml_path = tmp_path / "reglas_registro.yaml"
    yaml_path.write_text("""
reglas:
  - id: REG-ING-001
    nombre: "DB activa"
    categoria: REG-ING
    categoria_nombre: "Ingesta DTE"
    prioridad: critica
    estado: implementada
    norma: "REG-ING-001_db_activa.md"
""", encoding="utf-8")
    nodos = nodos_regla_desde_catalogo(str(yaml_path), "MiProyecto")
    assert len(nodos) == 1
    n = nodos[0]
    assert n.type == "REGLA"
    assert "REG-ING-001" in n.title
    assert "DB activa" in n.title
```

### Task 10.3: test que falla (brief incluye sección)
```python
"""El brief añade la sección Reglas de Negocio (R10)."""
from __future__ import annotations

from context_map.domain.reglas.reglas import resumen_catalogo


def test_resumen_catalogo_por_categoria(tmp_path):
    yaml_path = tmp_path / "reglas_registro.yaml"
    yaml_path.write_text("""
reglas:
  - id: REG-ING-001
    nombre: "A"
    categoria: REG-ING
    categoria_nombre: "Ingesta DTE"
    prioridad: critica
    estado: implementada
    norma: "a.md"
  - id: REG-ATR-001
    nombre: "B"
    categoria: REG-ATR
    categoria_nombre: "Atribución CC"
    prioridad: critica
    estado: implementada
    norma: "b.md"
""", encoding="utf-8")
    resumen = resumen_catalogo(str(yaml_path))
    assert resumen["total"] == 2
    assert resumen["categorias"]["REG-ING"] == 1
    assert resumen["categorias"]["REG-ATR"] == 1
```

### Task 10.4: implementación
- `domain/reglas/reglas.py`:
  - `parsear_catalogo(ruta) -> list[dict]` — lee YAML (usa `yaml.safe_load`
    con fallback al mini-parser sin pyyaml, igual que dominios.yaml).
  - `nodos_regla_desde_catalogo(ruta, proyecto) -> list[Node]` — crea nodos
    `type="REGLA"` con `title=f"{id}: {nombre}"`, tags [categoría, prioridad,
    estado], source "reglas", `created_at` estable (idempotente).
  - `resumen_catalogo(ruta) -> dict` — total + conteo por categoría.
- `scanning/scanner.py`: al escanear, buscar `references/reglas/reglas_registro.yaml`
  (y `**/reglas_registro.yaml` en 2 niveles) y anexar los nodos REGLA.
- `presentation/briefs/generadores.py`: si hay catálogo, sección
  `## Reglas de Negocio` con total, categorías y ruta del YAML.
- `standardize.py`: añadir `REGLA` al vocabulario de tipos conocidos (sin romper
  la topología — los nodos REGLA se renderizan como hojas de 3.0-ESTRUCTURA).

### Task 10.5: verificación
```bash
python -m pytest context_map/__tests__/test_reglas_catalogo.py -v   # 5 passed
python -m context_map.cli scan . && python -m context_map.cli build --brief .
grep -A4 "Reglas de Negocio" .context-map/CONTEXT.md                # sección visible
python -m pytest -q                                                  # suite completa
```

### Task 10.6: commit
```bash
git add context_map/domain/reglas/ context_map/domain/scanning/scanner.py \
        context_map/presentation/briefs/generadores.py \
        context_map/core/normalization/standardize.py \
        context_map/__tests__/test_reglas_catalogo.py
git commit -m "feat(reglas): reconoce el catálogo de reglas de negocio — nodos REGLA + sección en brief (R10)"
```

---

## ✅ ETAPA 1 — Señal de frescura en `check` (R1)

**Objetivo**: `ctxmap check .` (y por tanto `refresh`) detecta actividad posterior
al último build y avisa al agente que debe refrescar.

### Archivos
- Modify: `context_map/domain/analysis/checker.py` (nueva señal + `_ultima_actividad`)
- Test: `context_map/__tests__/test_checker_frescura.py` (nuevo)

### Task 1.1: escribir el test que falla

```python
"""Tests de la señal de frescura del contexto (R1, auditoría 2026-08-14)."""
from __future__ import annotations

import json
import os

from context_map.domain.analysis.checker import (
    ResultadoReadiness,
    analizar_readiness,
    _ultima_actividad,
)


def _hacer_repo(tmp_path, con_git: bool = True) -> str:
    """Crea un mini proyecto con .context-map/state/last_build.json."""
    ctx = tmp_path / ".context-map" / "state"
    ctx.mkdir(parents=True)
    (ctx / "last_build.json").write_text(
        json.dumps({"clean": False, "manuales_preservadas": 0,
                    "timestamp": "2000-01-01T00:00:00"}),
        encoding="utf-8",
    )
    if con_git:
        (tmp_path / ".git").mkdir(exist_ok=True)
    return str(tmp_path)


def test_ultima_actividad_detecta_commit_posterior_al_build(tmp_path, monkeypatch):
    """Si hay un commit posterior al last_build, la señal avisa."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        if args and args[0] == "log":
            return "9999999 2026-08-14 10:00:00 -0400"
        return ""

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    actividad = _ultima_actividad(ruta)
    assert actividad["commits_posteriores"] > 0
    assert "commit" in actividad["aviso"].lower()


def test_check_avisa_con_sesiones_sin_importar(tmp_path, monkeypatch):
    """Si hay sesiones de Hermes posteriores al build, la señal avisa."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        return ""

    def _fake_sesiones(_ruta):
        return 3

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    monkeypatch.setattr("context_map.domain.analysis.checker._sesiones_posteriores", _fake_sesiones)
    resultado = analizar_readiness(ruta)
    texto = resultado.sugerencias  # el aviso vive en sugerencias
    assert any("sesione" in s.lower() for s in texto)


def test_check_sin_actividad_no_avisa(tmp_path, monkeypatch):
    """Sin commits ni sesiones posteriores, no hay falso aviso."""
    ruta = _hacer_repo(tmp_path)

    def _fake_git(_ruta, args):  # noqa: ANN001
        return ""

    def _fake_sesiones(_ruta):
        return 0

    monkeypatch.setattr("context_map.domain.analysis.checker._ejecutar_git", _fake_git)
    monkeypatch.setattr("context_map.domain.analysis.checker._sesiones_posteriores", _fake_sesiones)
    resultado = analizar_readiness(ruta)
    assert not any("sin importar" in s for s in resultado.sugerencias)
```

### Task 1.2: implementación mínima en `checker.py`

- Añadir `_ejecutar_git` (reutiliza la de `infrastructure/integrations/git.py`; mover o importar).
- `_ultima_actividad(ruta) -> dict`: lee `last_build.json.timestamp`; si no existe → aviso "nunca se ha hecho build".
- `_sesiones_posteriores(ruta) -> int`: cuenta sesiones de Hermes (reutiliza `leer_sesiones` de `hermes.py`) con `last_active > build`.
- En `formatear_readiness`: imprimir la sección "Frescura del Contexto" con el aviso.
- Guard: sin `.context-map` o sin git → no avisar (tolerante).

### Task 1.3: verificación
```bash
python -m pytest context_map/__tests__/test_checker_frescura.py -v   # 3 passed
python -m context_map.cli check .                                    # aviso si aplica
```

### Task 1.4: commit
```bash
git add context_map/domain/analysis/checker.py context_map/__tests__/test_checker_frescura.py
git commit -m "feat(check): señal de frescura — avisa commits/sesiones posteriores al último build"
```

---

## ✅ ETAPA 2 — Memoria viva en pre-commit (R2)

**Objetivo**: que **cada commit** importe las sesiones recientes del proyecto y
regenere el vault — la memoria viva deja de depender de la disciplina del agente.

### Archivos
- Modify: `context_map/application/commands/hook.py` (script generado)
- Modify: `context_map/application/commands/build.py` (flag `--import-sessions` opcional)
- Modify: `context_map/application/cli/parser.py` (flag en build)
- Test: `context_map/__tests__/test_hook_memoria_viva.py` (nuevo)

### Task 2.1: test que falla
```python
"""El pre-commit hook generado debe importar sesiones antes del build (R2)."""
from __future__ import annotations

from context_map.application.commands.hook import _script_hook


def test_script_hook_incluye_import_sesiones():
    script = _script_hook()
    assert "--import-sessions" in script
    assert "importar" in script.lower()
```

### Task 2.2: implementación
- Extraer el script del hook a `_script_hook()` (hoy está inline en `cmd_hook_install`).
- Cambiar la primera línea por:
  `python -m context_map.cli build --brief --quiet --import-sessions`
- En `build.py`: si `args.import_sessions`, llamar a `importar_sesiones(limite=5, project=project_name)` (reutilizar la lógica de `refresh.py`).
- En `parser.py`: `s_build.add_argument("--import-sessions", action="store_true")`.

### Task 2.3: verificación
```bash
python -m pytest context_map/__tests__/test_hook_memoria_viva.py -v
python -m context_map.cli hook install .   # regenera el hook
cat .git/hooks/pre-commit                  # ver la línea --import-sessions
```

### Task 2.4: commit
```bash
git commit -m "feat(hook): el pre-commit importa sesiones recientes (memoria viva por commit)"
```

---

## ✅ ETAPA 3 — Diario sin ruido (R4) + títulos legibles (R5)

**Objetivo**: el diario del día acumula los nodos del scanner en **un solo bloque**
en vez de anexar una sección "🤖" por cada build; títulos completos (sin `[:60]`).

### Archivos
- Modify: `context_map/presentation/vault/consolidated/canvas.py` (`render_nota_dia`)
- Test: `context_map/__tests__/test_diario_consolidado.py` (nuevo)

### Task 3.1: test que falla
```python
"""El diario consolida bloques del scanner en uno solo (R4) y no trunca (R5)."""
from __future__ import annotations

from context_map.core.models import Node
from context_map.presentation.vault.consolidated.canvas import render_nota_dia


def _nodo(titulo: str, fecha: str) -> Node:
    return Node(id=titulo, type="BASE", title=titulo, created_at=f"{fecha}T10:00:00")


def test_anexa_una_sola_seccion_autogenerada(tmp_path):
    out = str(tmp_path)
    hoy = "2026-08-14"
    n1 = _nodo("Primer nodo del día", hoy)
    n2 = _nodo("Segundo nodo del día", hoy)
    render_nota_dia(out, "MiProyecto", [n1])
    render_nota_dia(out, "MiProyecto", [n1, n2])
    ruta = tmp_path / ".context-map" / "vault-MiProyecto" / "7.0-MANUAL" / "Diario" / f"{hoy}.md"
    contenido = ruta.read_text(encoding="utf-8")
    assert contenido.count("🤖 Ingresados por el scanner") == 1
    assert "Segundo nodo del día" in contenido


def test_no_trunca_titulos_a_60(tmp_path):
    out = str(tmp_path)
    hoy = "2026-08-14"
    titulo_largo = "x" * 120
    render_nota_dia(out, "MiProyecto", [_nodo(titulo_largo, hoy)])
    ruta = tmp_path / ".context-map" / "vault-MiProyecto" / "7.0-MANUAL" / "Diario" / f"{hoy}.md"
    assert titulo_largo in ruta.read_text(encoding="utf-8")
```

### Task 3.2: implementación
- En `render_nota_dia`, si la nota existe: **reescribir** la sección autogenerada
  (borrar la última `## 🤖` y anexar los faltantes ahí) en vez de añadir otra sección.
- Título completo: `n.title` sin `[:60]` (el wikilink mantiene el nombre de archivo).

### Task 3.3: verificación + commit
```bash
python -m pytest context_map/__tests__/test_diario_consolidado.py -v
git commit -m "fix(diario): consolida bloques del scanner por día + títulos completos"
```

---

## ✅ ETAPA 4 — Clasificar decisiones/lecciones en sesiones (R6)

**Objetivo**: `importar_sesiones` detecta mensajes de cierre (*"quedó
implementado"*, *"regla definitiva"*, *"el usuario rechazó"*, *"commit X"*) y los
importa como `DECISION`/`CORRECCION`/`LECCION` en vez de `IDEA` genérica.

### Archivos
- Modify: `context_map/infrastructure/integrations/hermes.py` (`extraer_contexto_sesion`)
- Test: `context_map/__tests__/test_hermes_clasificacion.py` (nuevo)

### Task 4.1: test que falla
```python
"""Patrones de cierre → tipos específicos (R6, auditoría 2026-08-14)."""
from __future__ import annotations

from context_map.infrastructure.integrations.hermes import extraer_contexto_sesion
from context_map.infrastructure.integrations.hermes import Mensaje, Sesion


def _sesion_con(rol: str, contenido: str) -> Sesion:
    return Sesion(
        id="s1", titulo="Test", cwd="", git_repo_root="", fecha="2026-08-14",
        mensajes=[Mensaje(rol=rol, contenido=contenido, herramienta="")],
    )


def test_quedo_implementado_es_correccion():
    ev = extraer_contexto_sesion(_sesion_con("assistant", "quedó implementado en commit abc"))
    assert any(e["type"] == "CORRECCION" for e in ev)


def test_regla_definitiva_es_decision():
    ev = extraer_contexto_sesion(_sesion_con("assistant", "la regla definitiva es el cruce fiel"))
    assert any(e["type"] == "DECISION" for e in ev)


def test_leccion_es_leccion():
    ev = extraer_contexto_sesion(_sesion_con("assistant", "Lección: no inventar estados sin confirmar"))
    assert any(e["type"] == "LECCION" for e in ev)
```

### Task 4.2: implementación
- Añadir patrones de cierre al clasificador de mensajes del asistente:
  `["quedó implementado", "commit", "pusheado", "desplegado"]` → CORRECCION;
  `["regla definitiva", "decisión", "confirmado por el usuario", "el usuario rechazó"]` → DECISION;
  `["lección", "aprendizaje"]` → LECCION.
- Mantener los existentes (RIESGO/IDEA/CAMBIO) sin romper.

### Task 4.3: verificación + commit
```bash
python -m pytest context_map/__tests__/test_hermes_clasificacion.py -v
git commit -m "feat(hermes): clasifica decisiones/correcciones/lecciones en sesiones importadas"
```

---

## ✅ ETAPA 5 — Comando `ctxmap wrap` (R3)

**Objetivo**: cierre de sesión en 1 comando: refresh + resumen de lo registrado vs
lo que queda sin importar.

### Archivos
- Create: `context_map/application/commands/wrap.py`
- Modify: `context_map/application/cli/parser.py` (`s_wrap`)
- Modify: `context_map/application/cli/cli.py` (registro)
- Test: `context_map/__tests__/test_wrap.py`

### Task 5.1-5.3: TDD
- `wrap` = `cmd_refresh` + imprimir conteo de `events.jsonl` y "N sesiones sin importar".
- Test: `cmd_wrap` con monkeypatch de refresh → imprime resumen.

---

## ✅ ETAPA 6 — Métrica de memoria viva (R7) + nombre consistente (R8) + limpieza (R9)

- **R7**: en `formatear_readiness`, añadir `% sesiones recientes que generaron eventos` (leer `events.jsonl` y comparar con sesiones).
- **R8**: en `check`, comparar `vault-<X>` vs `project` del CONTEXT vs nombre del repo → aviso si difieren (ataca duplicados en BD personal).
- **R9**: en `cmd_refresh`, detectar carpetas tipo `piloto_*`, `scripts/debug` sin trackear y avisar "¿mover a _legacy/ o borrar?".

---

## 🚫 Fuera de alcance (por ahora)
- NO tocar mi-app-utm / Gobernanza / CotanoPet (esta es mejora de ContextMap).
- NO implementar watcher (`ctxmap watch`) — la gobernanza sigue por instrucción.
- NO cambiar la topología del vault (regla inamovible 4.x).

---
[[00-MEJORAS|⬅ Volver a Mejoras]]

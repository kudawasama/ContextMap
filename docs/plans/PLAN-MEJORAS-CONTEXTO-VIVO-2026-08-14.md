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

# Mapa Mental Conectado — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Convertir el vault de ContextMap de un árbol aislado en un mapa mental profesional: jerarquía visual ordenada intacta + conexiones semánticas entre notas reales + herramientas de Obsidian (bases/Dataview, lienzo Canvas, plantillas, nota del día, etiquetas, adjuntos, grupos) + orden por fecha de ingreso.

**Architecture:** Mantener el árbol jerárquico como columna vertebral visual (no se rompe la topología actual). Agregar una capa de conexiones reales entre archivos que SÍ existen (`🔗 Conexiones` en cada nota + `00-CONEXIONES.md` con wikilinks reales), un generador de Canvas (`00-MAPA-MENTAL.canvas`), grupos de colores en el Graph View (`.obsidian/graph.json`), bloques Dataview con fallback estático para ordenar por fecha, plantillas y nota del día para el trabajo manual, y edges `relaciona` creados por los importadores cuando una conversación menciona varios nodos.

**Tech Stack:** Python (ContextMap), Obsidian (wikilinks, .canvas JSON, graph.json, Dataview queries), pytest.

**Principios:** TDD (test → fail → implement → pass), commits frecuentes, DRY, YAGNI. Cada wikilink nuevo DEBE apuntar a un archivo que existe (0 nodos fantasma — el audit `scripts/audit_vault_topology.py` debe seguir pasando).

---

## Fase 1 — Fundamentos: resolver archivos reales y conexiones semánticas

### Task 1: Helper `ruta_archivo_nodo()` — resolver el archivo real de un nodo

**Objective:** Dado un nodo, devolver la ruta relativa (al vault) del archivo .md que lo materializa, o `None` si no existe archivo individual (nodos agrupados: BASE, FUTURO, CAMBIO/CORRECCION en secciones; IDEAS completadas en batches).

**Files:**
- Create: `context_map/presentation/vault/consolidated/rutas.py`
- Test: `context_map/__tests__/test_conexiones.py` (nuevo)

**Step 1: Write failing test**

```python
def test_ruta_archivo_nodo():
    from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo
    # IDEA pendiente → archivo individual
    idea = Node(id="FUTURO001", type="IDEA", title="Nueva feature", status="pendiente", concept="DEVOPS")
    ruta = ruta_archivo_nodo(idea)
    assert ruta == "2.0-IDEAS/2.1-Ideas-Pendientes/DEVOPS/idea_FUTURO001_NUEVA_FUNCIONALIDAD.md"
    # RIESGO → archivo individual sanitizado
    riesgo = Node(id="R1", type="RIESGO", title="Deuda técnica en parser.py")
    assert ruta_archivo_nodo(riesgo).startswith("4.0-RIESGOS/")
    # BASE/FUTURO/CAMBIO agrupados → None (sin archivo individual)
    assert ruta_archivo_nodo(Node(id="B1", type="BASE", title="x")) is None
    assert ruta_archivo_nodo(Node(id="F1", type="FUTURO", title="y")) is None
```

**Step 2: Run test → FAIL** (`ModuleNotFoundError`).

**Step 3: Implement**

```python
"""Resolución de la ruta real de archivo de un nodo en el vault jerárquico."""
from __future__ import annotations
import os
from context_map.core.models import Node

# Mismo criterio que secciones_ideas.py: idea_{id_limpio}_{ACCION}.md
_ACCION = {"feature": "NUEVA_FUNCIONALIDAD", "fix": "CORRECCION_BUG",
           "update": "MEJORA", "chore": "MANTENIMIENTO", "docs": "DOCUMENTACION",
           "refactor": "REFACTOR", "test": "PRUEBA", "idea": "IDEA"}

def _accion(node: Node) -> str:
    return _ACCION.get(getattr(node, "classification", "") or "", "IDEA")

def ruta_archivo_nodo(node: Node) -> str | None:
    """Ruta relativa (al vault) del archivo que materializa el nodo, o None."""
    if node.type == "IDEA" and node.status in ("pendiente", "activo"):
        carpeta = "2.1-Ideas-Pendientes" if node.status == "pendiente" else "2.2-Ideas-Futuras"
        concept = getattr(node, "concept", "") or "GENERAL"
        return f"2.0-IDEAS/{carpeta}/{concept}/idea_{node.id}_{_accion(node)}.md"
    if node.type == "RIESGO":
        # mismo safe_filename que el renderizador (60 chars, sin caracteres especiales)
        return f"4.0-RIESGOS/{node.title[:60].strip()}.md"  # Ajustar al _safe_filename real
    # Agrupados (BASE→3.1, FUTURO→5.1, CAMBIO/CORRECCION→6.1/6.2, IDEA completada→batch)
    return None
```

> NOTA implementación: reutilizar `_safe_filename` de `presentation/vault/templates.py` en vez del `[:60]` (verificar el nombre real del archivo RIESGO generado; el test debe usar el mismo sanitizado).

**Step 4: Run test → PASS**

**Step 5: Commit**

```bash
git add context_map/presentation/vault/consolidated/rutas.py context_map/__tests__/test_conexiones.py
git commit -m "feat(vault): resolver ruta real de archivo por nodo (base de conexiones sin nodos fantasma)"
```

---

### Task 2: Generador de conexiones semánticas `conexiones_de_nodo()`

**Objective:** Para un nodo, calcular sus top-5 nodos relacionados (por mismo concepto, misma fecha de ingreso/sesión, o referencia cruzada en summaries), excluyendo nodos agrupados sin archivo individual.

**Files:**
- Modify: `context_map/presentation/vault/consolidated/rutas.py`
- Test: `context_map/__tests__/test_conexiones.py`

**Step 1: Write failing test**

```python
def test_conexiones_semanticas():
    from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo, ruta_archivo_nodo
    a = Node(id="I1", type="IDEA", title="Bot contable", concept="AUTOMATIZACION", status="pendiente", created="2026-08-01T10:00:00")
    b = Node(id="I2", type="IDEA", title="Reporte diario", concept="AUTOMATIZACION", status="pendiente", created="2026-08-01T10:05:00")
    c = Node(id="I3", type="IDEA", title="UI nueva", concept="UI", status="pendiente", created="2026-08-02T09:00:00")
    cons = conexiones_de_nodo(a, [a, b, c])
    rutas = [ruta_archivo_nodo(n) for n in cons]
    assert "I2" in [n.id for n in cons]       # mismo concepto
    assert "I3" not in [n.id for n in cons]   # concepto distinto y fecha distinta
    assert len(cons) <= 5
```

**Step 2: Run → FAIL.**

**Step 3: Implement** — scoring en `conexiones_de_nodo(node, todos, limite=5)`:
- +3 mismo `concept`; +2 misma fecha (`created[:10]` igual); +1 si el título del otro aparece en `node.summary` (o viceversa).
- Excluir `node` mismo y nodos con `ruta_archivo_nodo() is None` (evitar fantasma).
- Ordenar por score desc, devolver top-N.

**Step 4: Run → PASS.**

**Step 5: Commit** — `feat(vault): conexiones semanticas entre nodos (concepto/fecha/menciones) con limite de 5`.

---

## Fase 2 — Conexiones visibles: notas + 00-CONEXIONES

### Task 3: Sección "🔗 Conexiones" en notas de ideas

**Objective:** Cada nota individual de idea (pendiente/activa) incluye su sección de conexiones con wikilinks a archivos reales, sin tocar el pie `⬅` (el árbol queda intacto).

**Files:**
- Modify: `context_map/presentation/vault/consolidated/secciones_ideas.py` (función que escribe cada nota, ~línea 153)
- Test: `context_map/__tests__/test_conexiones.py`

**Step 1: Test**

```python
def test_nota_idea_incluye_conexiones():
    # render 2 ideas del mismo concepto → la nota de la primera contiene
    # [[2.0-IDEAS/2.1-Ideas-Pendientes/AUTOMATIZACION/idea_I2_....md|...
    # y NO rompe: sigue teniendo el pie '⬅ Volver'
```

**Step 2: FAIL.** **Step 3: Implement** — en el render de la nota, tras las secciones narrativas y antes del pie:

```python
from context_map.presentation.vault.consolidated.rutas import conexiones_de_nodo, ruta_archivo_nodo
if ruta_archivo_nodo(node):
    partes.append("## 🔗 Conexiones")
    partes.append("")
    for rel in conexiones_de_nodo(node, todos):
        destino = ruta_archivo_nodo(rel)
        if destino:
            partes.append(f"- [[{destino}|{rel.title[:40]}]]")
    partes.append("")
```

**Step 4: PASS.** **Step 5: Commit** — `feat(vault): notas de idea con seccion de conexiones (wikilinks a archivos reales)`.

---

### Task 4: Sección "🔗 Conexiones" en notas de riesgos

**Files:** `context_map/presentation/vault/consolidated/secciones_riesgos.py` (o el que renderiza los archivos de riesgo). Mismo patrón que Task 3. Test: riesgo enlaza a la idea que lo menciona. Commit: `feat(vault): notas de riesgo con conexiones`.

---

### Task 5: `00-CONEXIONES.md` con wikilinks reales

**Objective:** `_render_grafo_conexiones` pasa de `con_wikilinks=False` (todo texto) a renderizar cada arista con wikilinks SI ambos extremos tienen archivo real; los demás (ids sin archivo) quedan como texto plano → 0 nodos fantasma.

**Files:**
- Modify: `context_map/presentation/vault/consolidated/jerarquico.py:223` y la función `_render_grafo_conexiones`
- Test: `context_map/__tests__/test_conexiones.py`

**Step 1: Test**

```python
def test_conexiones_md_con_wikilinks_solo_archivos_reales():
    # edge entre 2 ideas pendientes → aparece [[2.0-IDEAS/.../idea_X...]]
    # edge depends_on hacia un id sin archivo → texto plano, sin '[['
```

**Step 2: FAIL.** **Step 3: Implement** — en `_render_grafo_conexiones`:

```python
from context_map.presentation.vault.consolidated.rutas import ruta_archivo_nodo
nodos_por_id = {n.id: n for n in nodes}
for e in edges:
    src = nodos_por_id.get(e.source); dst = nodos_por_id.get(e.target)
    r_src = ruta_archivo_nodo(src) if src else None
    r_dst = ruta_archivo_nodo(dst) if dst else None
    if r_src and r_dst:
        lineas.append(f"- {src.title[:40]} ↔ [[{r_dst}|{dst.title[:40]}]] ({e.kind})")
    else:
        lineas.append(f"- {e.source} → {e.target} ({e.kind}) [sin archivo individual]")
```

**Step 4: PASS** + correr `python scripts/audit_vault_topology.py .context-map/vault-ContextMap` → 0 enlaces rotos. **Step 5: Commit** — `feat(vault): 00-CONEXIONES con wikilinks reales sin nodos fantasma`.

---

## Fase 3 — Fecha de ingreso y herramientas de Obsidian

### Task 6: Orden cronológico por fecha de ingreso en listados

**Files:**
- Modify: `context_map/presentation/vault/consolidated/secciones_ideas.py` (2.4-Ideas-Relevantes) y `secciones_backlog.py` (5.1-Tareas)

**Step 1: Test** — dado 2 nodos con created distinto, el listado sale ordenado ASC por `created`.

**Step 2-4:** ordenar `sorted(nodos, key=lambda n: n.created)` al renderizar; añadir la fecha visible `(2026-08-01)` en cada ítem. PASS.

**Step 5: Commit** — `feat(vault): listados ordenados por fecha de ingreso`.

---

### Task 7: Bloques Dataview (bases) con fallback estático

**Objective:** En `2.4-Ideas-Relevantes.md` incluir un bloque Dataview (tabla: archivo, created, concepto, status, orden por fecha). Como Dataview es plugin, el fallback estático (lista ordenada de Task 6) SIEMPRE se mantiene debajo.

**Files:** Modify: `context_map/presentation/vault/consolidated/secciones_ideas.py`

```markdown
## 📊 Base de Ideas (Dataview)
```dataview
TABLE created AS "Ingreso", concepto, status
FROM "2.0-IDEAS"
SORT created ASC
```
```

**Test:** el archivo generado contiene `\`\`\`dataview` y la lista estática ordenada. **Commit:** `feat(vault): base dataview de ideas con fallback estatico`.

---

### Task 8: Generador de Lienzo `00-MAPA-MENTAL.canvas`

**Objective:** ContextMap genera un Canvas Obsidian con el mapa mental completo: nodos `file` (solo archivos reales) + aristas `relaciona`/`depends_on`.

**Files:**
- Create: `context_map/presentation/vault/consolidated/canvas.py`
- Modify: `context_map/presentation/vault/consolidated/jerarquico.py` (llamar al final de `_render_hierarchical_vault`)

**Step 1: Test** — genera el archivo, es JSON válido, cada node tiene `type:"file"` con ruta que existe en el vault, cada edge referencia `fromNode`/`toNode` existentes.

**Step 2: FAIL.** **Step 3: Implement:**

```python
import json, uuid
def render_canvas(output_dir, nodes, edges):
    """00-MAPA-MENTAL.canvas — nodos file + aristas."""
    por_id = {n.id: n for n in nodes}
    canvas_nodes, canvas_edges = [], []
    ids = {}
    # Layout radial simple por orden de nodos (x = 200*idx % 1200, y = 200*(idx//6))
    for i, n in enumerate(nodes):
        ruta = ruta_archivo_nodo(n)
        if not ruta:
            continue
        uid = str(uuid.uuid4())
        ids[n.id] = uid
        canvas_nodes.append({"id": uid, "type": "file", "file": ruta,
                             "x": 200 * (i % 6), "y": 200 * (i // 6),
                             "width": 260, "height": 60})
    for e in edges:
        if e.source in ids and e.target in ids:
            canvas_edges.append({"id": str(uuid.uuid4()),
                                 "fromNode": ids[e.source], "fromSide": "right",
                                 "toNode": ids[e.target], "toSide": "left"})
    payload = {"nodes": canvas_nodes, "edges": canvas_edges}
    ruta_canvas = os.path.join(output_dir, "00-MAPA-MENTAL.canvas")
    with open(ruta_canvas, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return ruta_canvas
```

**Step 4: PASS.** **Step 5: Commit** — `feat(vault): lienzo 00-MAPA-MENTAL.canvas con mapa mental conectado`.

---

### Task 9: Grupos de colores del Graph View (`.obsidian/graph.json`)

**Objective:** Generar `.context-map/vault-<proj>/.obsidian/graph.json` con grupos por estado (Pendientes/Activas/Completadas/Riesgos) con colores — la vista "profesional".

**Files:** Modify: `context_map/presentation/vault/consolidated/canvas.py` (o nuevo `graph_config.py`)

```python
def render_graph_json(output_dir, nodes):
    """.obsidian/graph.json — grupos por estado con colores (rgb int)."""
    grupos = [
        {"query": "path:2.1-Ideas-Pendientes", "color": {"a": 1, "rgb": 0xEAB308}},  # amarillo
        {"query": "path:2.2-Ideas-Futuras",    "color": {"a": 1, "rgb": 0x3B82F6}},  # azul
        {"query": "path:2.3-Ideas-Completas",  "color": {"a": 1, "rgb": 0x22C55E}},  # verde
        {"query": "path:4.0-RIESGOS",          "color": {"a": 1, "rgb": 0xEF4444}},  # rojo
    ]
    conf = {"collapse-filter": True, "search": "", "showTags": False,
            "groups": grupos}
    obs = os.path.join(output_dir, ".obsidian")
    os.makedirs(obs, exist_ok=True)
    with open(os.path.join(obs, "graph.json"), "w", encoding="utf-8") as f:
        json.dump(conf, f, ensure_ascii=False, indent=2)
```

**Test:** `.obsidian/graph.json` existe con 4 grupos y colores. **Commit:** `feat(vault): grupos de color del graph view por estado`.

---

### Task 10: Plantillas y nota del día para el trabajo manual

**Files:**
- Modify: `context_map/presentation/briefs/skill.py` (referencia a plantillas)
- Create generador: `context_map/presentation/vault/consolidado/plantillas.py`

**Step 1:** Generar `.context-map/plantillas/nota-sesion.md`:

```markdown
---
type: nota-manual
preserve: true
created: {{fecha}}
project: "{{proyecto}}"
tags: [sesion, manual]
---
# Sesión — {{fecha}}
## ¿Qué se hizo?
## Decisiones
## Pendiente
```

**Step 2:** Generar `.context-map/vault-<proj>/.manual/Diario/YYYY-MM-DD.md` (nota del día) si hay eventos con esa fecha: enlaza a los nodos tocados ese día (`[[idea_X]]`). Se regenera en cada `refresh`.

**Test:** plantilla existe; si hay nodos con created de hoy, existe la nota diaria con wikilinks. **Commit:** `feat(vault): plantillas para notas manuales y nota del dia automatica`.

---

### Task 11: Carpeta de adjuntos

**Files:** `context_map/application/commands/build.py` (`ensure_dirs`) — crear `.context-map/vault-<proj>/adjuntos/` al build. Documentar en la skill. Test trivial (dir existe). **Commit:** `feat(vault): carpeta de adjuntos del vault`.

---

## Fase 4 — Historia → conexiones (menciones cruzadas)

### Task 12: Importadores crean edges `relaciona` por menciones cruzadas

**Objective:** Cuando una conversación importada (sessions/antigravity/chat) menciona 2+ nodos existentes, crear un edge `relaciona` entre ellos (persistido en `edges.jsonl`), de modo que el mapa mental conecta lo que la historia conversada conectó.

**Files:**
- Modify: `context_map/application/commands/importers.py` (tras crear nodos de la conversación) o `context_map/domain/synchronization/sync.py`
- Test: `context_map/__tests__/test_conexiones.py`

**Step 1: Test** — importar un chat que menciona "Bot contable" y "Reporte diario" → `edges.jsonl` contiene un edge `relaciona` entre esos ids.

**Step 2: FAIL.** **Step 3: Implement** — tras normalizar los nodos nuevos: para cada par de nodos cuyo título aparezca en el texto del evento, `append_jsonl(edges, {"source": a.id, "target": b.id, "kind": "relaciona", "summary": "mencion cruzada en conversacion"})` (dedup por (source,target,kind)).

**Step 4: PASS.** **Step 5: Commit** — `feat(importers): edges 'relaciona' por menciones cruzadas en conversaciones`.

---

## Fase 5 — Integración, verificación y documentación

### Task 13: Suite completa + regenerar el propio vault

**Steps:**
1. `python -m pytest` → todos pasan.
2. `python scripts/audit_vault_topology.py .context-map/vault-ContextMap` → 0 colisiones, 0 huérfanos, 0 enlaces rotos.
3. `ctxmap refresh . --project ContextMap` → regenera todo; verificar: notas con "🔗 Conexiones", `00-CONEXIONES.md` con wikilinks, `00-MAPA-MENTAL.canvas` válido, `.obsidian/graph.json` presente, listados ordenados por fecha.
4. `ctxmap check .` → Salud del Vault OK.

**Commit:** `feat(vault): mapa mental conectado completo — verificado con audit y refresh`.

### Task 14: Documentar en README y skill

**Files:** `README.md` (sección nueva "🗺️ Mapa Mental Conectado" con las herramientas: lienzo, grupos, dataview, plantillas, nota del día, adjuntos), `references/brief-specification.md` y `SKILL.md` de la skill `context-mapping` (regla de conexiones: jerarquía intacta + wikilinks solo a archivos reales + límite 5 + sin nodos fantasma).

**Commit:** `docs: documentar mapa mental conectado y herramientas de Obsidian`.

---

## Criterios de aceptación

1. El Graph View sigue mostrando el árbol ordenado (jerarquía intacta) — la regla inamovible de topología NO se rompe (audit 0/0/0).
2. Al abrir una nota (tomarla), el Local Graph muestra sus conexiones `🔗` con otras notas.
3. `00-CONEXIONES.md` y `00-MAPA-MENTAL.canvas` materializan el grafo conectado sin nodos fantasma.
4. Los listados ordenan por fecha de ingreso (created) y `2.4-Ideas-Relevantes` tiene base Dataview con fallback estático.
5. `.obsidian/graph.json` colorea el grafo por estado (grupos profesionales).
6. Existen plantillas para notas manuales y la nota del día se genera automáticamente.
7. Las conversaciones importadas crean conexiones `relaciona` (la historia conecta el mapa).
8. 50+ tests pasan; audit 0/0/0; `ctxmap refresh` regenera todo sin borrar `.manual/`.

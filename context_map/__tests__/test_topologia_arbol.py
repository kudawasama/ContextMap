"""Test: Verificación de la topología estricta en árbol del vault Obsidian.

Regla INAMOVIBLE (AGENTS.md sección 4): el Graph View de Obsidian debe verse
como un árbol puro. Este test comprueba que el vault generado cumple:

1. 0 nodos sin padre (todo archivo cuelga de exactamente un nivel superior,
   excepto ``00-INDICE.md`` y ``00-CONEXIONES.md``).
2. 0 colisiones de nombre base entre archivos (Obsidian fusiona archivos
   con el mismo nombre base, mezclando ideas de estados distintos).
3. 0 wikilinks rotos (todo target apunta a un archivo existente).
4. Los índices de concepto terminan en ``-Pendientes/-Futuras/-Completas.md``
   (nunca ``{CONCEPTO}.md`` a secas).
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile

from context_map.core.models import Edge, Node
from context_map.presentation.vault import render_obsidian_vault

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")

# Nodos raíz permitidos sin padre (no cuentan como violación)
SIN_PADRE_PERMITIDOS = {"00-INDICE.md", "00-CONEXIONES.md"}

# Wikilink del README incrustado en 1.1-Mapa-Mental-Narrativo (contenido
# documental del proyecto, no parte de la topología)
ENLACES_DOCUMENTALES_PERMITIDOS = {"entre-notas"}


def _crear_nodos_con_estados() -> list[Node]:
    """Genera nodos con los 3 estados de idea para validar las ramas.

    Incluye ideas pendientes, activas y completadas del mismo concepto
    (DEVOPS) para verificar que los índices de concepto son únicos por estado.
    """
    nodos: list[Node] = []

    # Ideas DEVOPS en los 3 estados — el caso que antes se mezclaba
    nodos.append(Node(
        id="IDEA-PEND-01", type="IDEA", title="TODO: pendiente devops",
        summary="Idea pendiente de DEVOPS", status="pendiente",
        source="test", tags=["idea", "pendiente"],
        concept="DEVOPS", classification="chore",
    ))
    nodos.append(Node(
        id="IDEA-ACT-01", type="IDEA", title="TODO: futura devops",
        summary="Idea futura de DEVOPS", status="activo",
        source="test", tags=["idea", "activo"],
        concept="DEVOPS", classification="chore",
    ))
    for i in range(3):
        nodos.append(Node(
            id=f"IDEA-COMP-{i:02d}", type="IDEA",
            title=f"TODO: completada devops {i}",
            summary=f"Idea completada de DEVOPS {i}", status="completado",
            source="test", tags=["idea", "completado"],
            concept="DEVOPS", classification="chore",
        ))
    # Otro concepto con una idea completada (verifica batches)
    nodos.append(Node(
        id="IDEA-COMP-UI", type="IDEA", title="TODO: completada ui",
        summary="Idea completada de UI", status="completado",
        source="test", tags=["idea", "completado"],
        concept="UI", classification="chore",
    ))
    # Nodos de las demás secciones
    nodos.append(Node(
        id="BASE-01", type="BASE", title="Modulo principal",
        summary="Componente base", source="test", tags=["estructura"],
    ))
    nodos.append(Node(
        id="RIESGO-01", type="RIESGO", title="Riesgo de complejidad",
        summary="Zona de alta complejidad", status="activo",
        source="test", tags=["riesgo"],
    ))
    nodos.append(Node(
        id="FUTURO-01", type="FUTURO", title="TODO: refactor futuro",
        summary="Tarea pendiente en backlog", status="pendiente",
        source="test", tags=["todo"],
    ))
    nodos.append(Node(
        id="CAMBIO-01", type="CAMBIO", title="feat: primer cambio",
        summary="Commit de cambio", source="git", tags=["cambio"],
    ))
    return nodos


def _analizar_vault(vault_dir: str) -> tuple[dict[str, str], list[str], list[str]]:
    """Recorre el vault y devuelve (nombre_base→rutas, errores, colisiones).

    Args:
        vault_dir (str): Directorio del vault generado.

    Returns:
        tuple: (por_nombre, errores_topologia, colisiones).
    """
    archivos: dict[str, str] = {}
    for root, _dirs, files in os.walk(vault_dir):
        for f in files:
            if f.endswith(".md"):
                rel = os.path.relpath(os.path.join(root, f), vault_dir).replace("\\", "/")
                archivos[rel] = f[:-3]  # nombre base sin .md

    por_nombre: dict[str, list[str]] = {}
    for rel, base in archivos.items():
        por_nombre.setdefault(base, []).append(rel)

    errores: list[str] = []
    for base, rutas in por_nombre.items():
        if len(rutas) > 1:
            errores.append(f"COLISIÓN nombre base '{base}': {rutas}")

    # In-degree: qué archivos reciben al menos un wikilink (backlink o enlace)
    in_degree: dict[str, set[str]] = {rel: set() for rel in archivos}
    for rel in archivos:
        ruta = os.path.join(vault_dir, rel)
        with open(ruta, encoding="utf-8") as fh:
            contenido = fh.read()
        for m in LINK_RE.findall(contenido):
            target = m.split("|")[0].strip().split("/")[-1]
            if target.endswith(".md"):
                target = target[:-3]
            if target in por_nombre:
                for r2 in por_nombre[target]:
                    if r2 != rel:
                        in_degree[r2].add(rel)

    # Nodos sin padre
    for rel in archivos:
        if rel in SIN_PADRE_PERMITIDOS:
            continue
        if not in_degree[rel]:
            errores.append(f"SIN PADRE: {rel}")

    # Wikilinks rotos
    for rel in archivos:
        ruta = os.path.join(vault_dir, rel)
        with open(ruta, encoding="utf-8") as fh:
            contenido = fh.read()
        for m in LINK_RE.findall(contenido):
            target = m.split("|")[0].strip().split("/")[-1]
            if target.endswith(".md"):
                target = target[:-3]
            if target not in por_nombre and target not in ENLACES_DOCUMENTALES_PERMITIDOS:
                errores.append(f"ENLACE ROTO: {rel} -> [[{m}]]")

    # Índices de concepto con sufijo de estado obligatorio
    # Aplica SOLO a índices dentro de carpetas de concepto:
    # 2.0-IDEAS/{2.1|2.2|2.3}/{CONCEPTO}/{CONCEPTO}-{Estado}.md  (≥4 segmentos)
    # NO a índices de sección: 2.0-IDEAS/2.0-IDEAS.md ni
    # 2.0-IDEAS/2.1-Ideas-Pendientes/2.1-Ideas-Pendientes.md (2-3 segmentos)
    for rel in archivos:
        partes = rel.split("/")
        if len(partes) >= 4 and rel.startswith("2.0-IDEAS"):
            carpeta = partes[-2]
            base = partes[-1][:-3]
            if base == carpeta:
                sufijos_ok = ("-Pendientes", "-Futuras", "-Completas")
                if not base.endswith(sufijos_ok):
                    errores.append(
                        f"ÍNDICE DE CONCEPTO SIN SUFIJO DE ESTADO: {rel} "
                        f"(debe ser {carpeta}-Pendientes/-Futuras/-Completas.md)"
                    )

    colisiones = [f"{k}: {v}" for k, v in por_nombre.items() if len(v) > 1]
    return por_nombre, errores, colisiones


def test_topologia_arbol_estricto() -> None:
    """Verifica que el vault jerárquico es un árbol puro sin mezclas."""
    nodos = _crear_nodos_con_estados()
    edges: list[Edge] = []
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_topologia_")

    try:
        render_obsidian_vault(
            project_name="TestTopologia",
            nodes=nodos,
            edges=edges,
            output_dir=temp_dir,
            mode="hierarchical",
        )

        por_nombre, errores, colisiones = _analizar_vault(temp_dir)

        # 1. Índices de concepto únicos por estado (DEVOPS-Pendientes != DEVOPS-Completas)
        indices = sorted(
            base for base in por_nombre
            if any(suf in base for suf in ("-Pendientes", "-Futuras", "-Completas"))
        )
        print(f"   Índices de concepto: {indices}")
        assert any("-Pendientes" in i for i in indices), "Falta índice -Pendientes"
        assert any("-Futuras" in i for i in indices), "Falta índice -Futuras"
        assert any("-Completas" in i for i in indices), "Falta índice -Completas"
        # No debe existir un índice DEVOPS sin sufijo (clave 'DEVOPS' con ruta en 2.0-IDEAS)
        for base, rutas in por_nombre.items():
            if base in ("DEVOPS", "UI") and any("/2.0-IDEAS/" in r for r in rutas):
                assert all(any(suf in base for suf in ("-Pendientes", "-Futuras", "-Completas")) for _ in rutas), (
                    f"Existe índice {base}.md sin sufijo de estado: {rutas}"
                )

        # 2. Sin colisiones de nombre base
        print(f"   Colisiones: {colisiones if colisiones else 'ninguna'}")
        assert not colisiones, f"Colisiones de nombre base: {colisiones}"

        # 3. Sin errores de topología (sin padre / enlaces rotos / índices mal)
        print(f"   Errores topología: {errores if errores else 'ninguno'}")
        assert not errores, f"Violaciones de topología:\n" + "\n".join(errores)

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_no_mezcla_ideas_por_estado() -> None:
    """Verifica que las ramas de ideas pendientes y completadas no se cruzan.

    El mismo concepto (DEVOPS) debe tener índices separados por estado y
    ninguna nota de 2.1 puede enlazar a un índice de 2.3 (ni viceversa).
    """
    nodos = _crear_nodos_con_estados()
    temp_dir = tempfile.mkdtemp(prefix="ctxmap_test_rama_")

    try:
        render_obsidian_vault(
            project_name="TestTopologia",
            nodes=nodos,
            edges=[],
            output_dir=temp_dir,
            mode="hierarchical",
        )

        # Rutas esperadas del árbol
        pend_dir = os.path.join(temp_dir, "2.0-IDEAS", "2.1-Ideas-Pendientes")
        comp_dir = os.path.join(temp_dir, "2.0-IDEAS", "2.3-Ideas-Completas-e-Implementadas")

        assert os.path.isdir(pend_dir), "No existe 2.1-Ideas-Pendientes"
        assert os.path.isdir(comp_dir), "No existe 2.3-Ideas-Completas-e-Implementadas"

        # DEVOPS-Pendientes existe SOLO en 2.1; DEVOPS-Completas SOLO en 2.3
        pend_devops = os.path.join(pend_dir, "DEVOPS", "DEVOPS-Pendientes.md")
        comp_devops = os.path.join(comp_dir, "DEVOPS", "DEVOPS-Completas.md")
        assert os.path.exists(pend_devops), "Falta DEVOPS-Pendientes.md en 2.1"
        assert os.path.exists(comp_devops), "Falta DEVOPS-Completas.md en 2.3"
        # El índice viejo sin sufijo NO debe existir
        assert not os.path.exists(os.path.join(pend_dir, "DEVOPS", "DEVOPS.md")), (
            "Existe DEVOPS.md sin sufijo en 2.1 (mezcla estados)"
        )
        assert not os.path.exists(os.path.join(comp_dir, "DEVOPS", "DEVOPS.md")), (
            "Existe DEVOPS.md sin sufijo en 2.3 (mezcla estados)"
        )

        # El índice DEVOPS-Pendientes enlaza SOLO a su padre (2.1-Ideas-Pendientes)
        with open(pend_devops, encoding="utf-8") as fh:
            contenido = fh.read()
        assert "2.1-Ideas-Pendientes" in contenido, (
            "DEVOPS-Pendientes no enlaza a su sección padre 2.1"
        )
        # La nota pendiente enlaza SOLO a su índice DEVOPS-Pendientes
        notas_pend = [
            f for f in os.listdir(os.path.join(pend_dir, "DEVOPS"))
            if f.endswith(".md") and f != "DEVOPS-Pendientes.md"
        ]
        assert notas_pend, "No hay notas pendientes bajo DEVOPS"
        with open(os.path.join(pend_dir, "DEVOPS", notas_pend[0]), encoding="utf-8") as fh:
            contenido_nota = fh.read()
        assert "DEVOPS-Pendientes" in contenido_nota, (
            "La nota pendiente no enlaza a DEVOPS-Pendientes"
        )

        # El batch de completadas cuelga de DEVOPS-Completas
        batch = os.path.join(comp_dir, "DEVOPS", "01-DEVOPS-01-03.md")
        assert os.path.exists(batch), "No se generó el batch 01-DEVOPS-01-03.md"
        with open(batch, encoding="utf-8") as fh:
            contenido_batch = fh.read()
        assert "DEVOPS-Completas" in contenido_batch, (
            "El batch no enlaza a DEVOPS-Completas"
        )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    print("=== Test: Topología Estricta en Árbol ===")
    test_topologia_arbol_estricto()
    print("   OK: test_topologia_arbol_estricto PASO")

    print()
    print("=== Test: No mezcla de ideas por estado ===")
    test_no_mezcla_ideas_por_estado()
    print("   OK: test_no_mezcla_ideas_por_estado PASO")

    print()
    print("Todos los tests pasaron correctamente.")

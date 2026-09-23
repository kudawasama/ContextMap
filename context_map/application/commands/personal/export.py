"""Exportación de la base de datos personal al Vault de Obsidian v2.

Genera una nota individual limpia por proyecto con metadatos, riesgos,
tareas y eventos, además de un índice general navegable sin wikilinks rotos.
"""

from __future__ import annotations

import os
import re

from context_map.core.personal import PersonalDB


def _generar_slugs_unicos(nombres_proyectos: list[str]) -> dict[str, str]:
    """Genera slugs deterministas y únicos para una lista de proyectos."""
    slugs: dict[str, str] = {}
    usados: dict[str, int] = {}

    for nombre in nombres_proyectos:
        base = re.sub(r"[^\w\-]+", "-", nombre.strip()).strip("-") or "proyecto"
        clave_base = base.lower()
        if clave_base not in usados:
            usados[clave_base] = 1
            slugs[nombre] = base
        else:
            usados[clave_base] += 1
            slugs[nombre] = f"{base}-{usados[clave_base]}"

    return slugs


def _sanear_texto_markdown(texto: str) -> str:
    """Sanea el texto de markdown para no romper la jerarquía del índice ni crear enlaces rotos."""
    if not texto:
        return ""
    sin_wikilinks = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", texto)
    lineas = []
    for linea in sin_wikilinks.splitlines():
        l_limpia = re.sub(r"^\s*#{1,6}\s*", "", linea).strip()
        if l_limpia:
            lineas.append(l_limpia)
    return " ".join(lineas)


def _seccion_notas_proyecto(
    db: PersonalDB,
    destino: str,
    secciones: list[str],
) -> list[str]:
    """Añade la sección de notas reales por proyecto (<slug>.md) v2."""
    proyectos = db.listar_proyectos()
    secciones.append("## Proyectos")
    os.makedirs(destino, exist_ok=True)

    slug_map = _generar_slugs_unicos(proyectos)
    notas_escritas = 0

    for nombre in proyectos:
        slug = slug_map[nombre]
        ruta_nota = os.path.join(destino, f"{slug}.md")

        fila_proy = db._conn.execute(
            "SELECT id, ruta, ultimo_sync FROM proyectos WHERE nombre = ?",
            (nombre,),
        ).fetchone()
        pid = fila_proy["id"] if fila_proy else None
        ruta_p = fila_proy["ruta"] if fila_proy else ""
        sync_p = fila_proy["ultimo_sync"] if fila_proy else ""

        lineas_nota = [
            f"# {nombre}",
            "",
            f"- **Proyecto**: {nombre}",
            f"- **Ruta**: `{ruta_p}`" if ruta_p else "- **Ruta**: *(no registrada)*",
            f"- **Último sync**: {sync_p}" if sync_p else "- **Último sync**: *(sin sync)*",
            "",
        ]

        # Riesgos vigentes
        riesgos = db._conn.execute(
            "SELECT texto, timestamp FROM eventos WHERE proyecto_id = ? AND tipo = 'RIESGO' "
            "ORDER BY id DESC LIMIT 5",
            (pid,),
        ).fetchall()
        if riesgos:
            lineas_nota.append("### ⚠️ Riesgos Vigentes")
            for r in riesgos:
                ts = f" _{r['timestamp'][:10]}_" if r["timestamp"] else ""
                r_txt = _sanear_texto_markdown(str(r["texto"]))[:160]
                lineas_nota.append(f"- {r_txt}{ts}")
            lineas_nota.append("")

        # Tareas pendientes
        pendientes = db._conn.execute(
            "SELECT texto, timestamp FROM eventos WHERE proyecto_id = ? AND tipo = 'FUTURO' "
            "ORDER BY id DESC LIMIT 5",
            (pid,),
        ).fetchall()
        if pendientes:
            lineas_nota.append("### 📝 Tareas Pendientes")
            for p in pendientes:
                ts = f" _{p['timestamp'][:10]}_" if p["timestamp"] else ""
                p_txt = _sanear_texto_markdown(str(p["texto"]))[:160]
                lineas_nota.append(f"- {p_txt}{ts}")
            lineas_nota.append("")

        # Eventos agrupados por día
        filas_ev = db._conn.execute(
            "SELECT tipo, texto, timestamp FROM eventos WHERE proyecto_id = ? "
            "ORDER BY timestamp DESC, id DESC LIMIT 100",
            (pid,),
        ).fetchall()

        if filas_ev:
            lineas_nota.append(f"### 📋 Historial de Eventos ({len(filas_ev)})")
            dia_actual = ""
            for ev in filas_ev:
                ts = str(ev["timestamp"] or "")
                dia = ts[:10] if ts else "Sin fecha"
                if dia != dia_actual:
                    dia_actual = dia
                    lineas_nota.append(f"\n#### 📅 {dia_actual}")

                tipo = ev["tipo"]
                texto_limpio = _sanear_texto_markdown(str(ev["texto"]))[:140]
                lineas_nota.append(f"- **[{tipo}]** {texto_limpio}")
            lineas_nota.append("")

        lineas_nota.append("---")
        lineas_nota.append("[[00-INDICE|⬅ Volver al Índice General]]")

        with open(ruta_nota, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas_nota))

        notas_escritas += 1
        secciones.append(f"- [[{slug}|{nombre}]]")

    secciones.append("")
    assert notas_escritas == len(proyectos), (
        f"Inconsistencia en export: {notas_escritas} notas escritas para {len(proyectos)} proyectos"
    )
    return secciones


def _seccion_lecciones(db: PersonalDB, secciones: list[str]) -> list[str]:
    """Añade la sección de lecciones compacta al índice del vault personal v2."""
    filas_lec = db._conn.execute(
        "SELECT leccion, instruccion, como_se_resolvio, proyectos.nombre AS proy "
        "FROM lecciones LEFT JOIN proyectos ON proyectos.id = lecciones.proyecto_id "
        "ORDER BY lecciones.id"
    ).fetchall()
    if filas_lec:
        secciones.append("## Lecciones de Conocimiento (8.0-KNOWLEDGE)")
        for fila in filas_lec:
            proy = f" *({fila['proy']})*" if fila["proy"] else ""
            tit = _sanear_texto_markdown(str(fila["leccion"]))
            secciones.append(f"### 🎯 {tit}{proy}")

            instruccion = str(fila["instruccion"] or fila["como_se_resolvio"] or "")
            inst_limpia = _sanear_texto_markdown(instruccion)
            if inst_limpia:
                if len(inst_limpia) > 250:
                    inst_limpia = inst_limpia[:247] + "..."
                secciones.append(f"> 📋 **Instrucción**: {inst_limpia}")
            secciones.append("")
    return secciones


def _seccion_decisiones(db: PersonalDB, secciones: list[str]) -> list[str]:
    """Añade la sección de decisiones al índice del vault personal."""
    filas_dec = db._conn.execute(
        "SELECT decision, contexto, proyectos.nombre AS proy "
        "FROM decisiones LEFT JOIN proyectos ON proyectos.id = decisiones.proyecto_id "
        "ORDER BY decisiones.id"
    ).fetchall()
    if filas_dec:
        secciones.append("## Decisiones Arquitectónicas")
        for fila in filas_dec:
            proy = f" *({fila['proy']})*" if fila["proy"] else ""
            dec_txt = _sanear_texto_markdown(str(fila["decision"]))
            secciones.append(f"- **{dec_txt}**{proy}")
            if fila["contexto"]:
                ctx_txt = _sanear_texto_markdown(str(fila["contexto"]))
                secciones.append(f"  _{ctx_txt}_")
        secciones.append("")
    return secciones


def _cmd_personal_export(args) -> None:
    """Genera un vault personal Obsidian desde la BD v2."""
    db = PersonalDB(getattr(args, "db", None))
    try:
        destino = getattr(args, "destino", None) or os.path.expanduser(
            "~/.context-map/vault-Personal"
        )
        os.makedirs(destino, exist_ok=True)

        secciones: list[str] = ["# 🌐 Vault Personal — ContextMap", ""]

        secciones = _seccion_notas_proyecto(db, destino, secciones)
        secciones = _seccion_lecciones(db, secciones)
        secciones = _seccion_decisiones(db, secciones)

        ruta_indice = os.path.join(destino, "00-INDICE.md")
        contenido_indice = "\n".join(secciones)
        with open(ruta_indice, "w", encoding="utf-8") as f:
            f.write(contenido_indice)

        total_archivos = len(os.listdir(destino))
        tamano_kb = os.path.getsize(ruta_indice) / 1024
        print(f"personal: vault exportado en {destino}")
        print(f"  archivos: {total_archivos} (índice + nota por proyecto)")
        print(f"  índice: 00-INDICE.md ({tamano_kb:.1f} KB)")
    finally:
        db.cerrar()

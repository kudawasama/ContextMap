"""Comando personal: base de datos global consolidada y transportable.

Permite sincronizar el contexto de todos los proyectos en una única base
de datos SQLite (F: drive o pendrive), registrar lecciones y decisiones al
vuelo, buscar con full-text (FTS5) y exportar un vault personal Obsidian.

Subcomandos:
    sync    Consolida proyectos en la BD personal.
    add     Agrega una lección o decisión al vuelo.
    query   Busca en eventos, lecciones y decisiones (FTS5).
    export  Genera un vault personal Obsidian desde la BD.
    backup  Copia la BD a otra ruta (pendrive, disco externo).
"""

from __future__ import annotations

import logging
import os
import re

from context_map.core.parsing import (
    load_events_from_chat_folder,
    load_events_from_jsonl,
)
from context_map.core.personal import Decision, Leccion, PersonalDB

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers compartidos
# ---------------------------------------------------------------------------


def sincronizar_proyecto_automatico(
    proj_name: str,
    target_dir: str = ".",
) -> None:
    """Consolida el proyecto en la BD personal de forma silenciosa.

    Se invoca al final de ``do_sync`` (build/scan/refresh) para conectar el
    contexto del proyecto con el contexto global personal. Nunca lanza
    excepciones: si la BD no está accesible (ej. sin F: en CI), simplemente
    se registra en DEBUG y el flujo principal continúa intacto.

    Args:
        proj_name: Nombre del proyecto (clave en la tabla ``proyectos``).
        target_dir: Directorio raíz del proyecto a consolidar.
    """
    try:
        db = PersonalDB()
        try:
            events_path, chats_path, vault_base = _rutas_proyecto(target_dir)
            eventos: list[dict] = []
            for ev in load_events_from_jsonl(events_path):
                eventos.append(ev.to_dict())
            for ev in load_events_from_chat_folder(chats_path):
                eventos.append(ev.to_dict())

            nuevos = db.cargar_eventos(proj_name, eventos)
            lecciones = 0
            for leccion in _leer_lecciones_vault(vault_base, proj_name):
                if db.agregar_leccion(leccion):
                    lecciones += 1
            if nuevos or lecciones:
                logger.info(
                    "personal: %s consolidado (+%d eventos, +%d lecciones) en %s",
                    proj_name, nuevos, lecciones, db.ruta,
                )
        finally:
            db.cerrar()
    except Exception as err:  # pragma: no cover - tolerancia total
        logger.debug("personal: consolidación automática omitida: %s", err)


def _rutas_proyecto(target_dir: str) -> tuple[str, str, str]:
    """Resuelve las rutas internas de eventos de un proyecto.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        tuple[str, str, str]: (ruta_events_jsonl, ruta_chats, ruta_vault)
    """
    base = os.path.join(target_dir, ".context-map")
    return (
        os.path.join(base, "raw", "events.jsonl"),
        os.path.join(base, "chats"),
        base,
    )


def _nombre_proyecto_por_ruta(target_dir: str) -> str:
    """Deriva el nombre del proyecto desde su ruta.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        str: Nombre del proyecto (carpeta base).
    """
    nombre = os.path.basename(os.path.abspath(target_dir))
    return nombre or "Repo"


def _leer_lecciones_vault(vault_base: str, proyecto: str) -> list[Leccion]:
    """Extrae lecciones de la zona 8.0-KNOWLEDGE del vault (si existe).

    Args:
        vault_base: Directorio base de ``.context-map`` del proyecto.
        proyecto: Nombre del proyecto para asociar las lecciones.

    Returns:
        list[Leccion]: Lecciones encontradas en ``8.0-KNOWLEDGE/*.md``.
    """
    knowledge_dir = None
    for candidato in (
        os.path.join(vault_base, "vault", "8.0-KNOWLEDGE"),
        os.path.join(vault_base, "vault-" + proyecto, "8.0-KNOWLEDGE"),
        os.path.join(vault_base, "8.0-KNOWLEDGE"),
    ):
        if os.path.isdir(candidato):
            knowledge_dir = candidato
            break
    if not knowledge_dir:
        return []

    lecciones: list[Leccion] = []
    for nombre in sorted(os.listdir(knowledge_dir)):
        if not nombre.endswith(".md"):
            continue
        ruta = os.path.join(knowledge_dir, nombre)
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
        except OSError:
            continue

        # Extraer título (primer encabezado) y cuerpo limpio de frontmatter
        titulo = nombre[:-3].replace("-", " ").replace("_", " ").strip()
        m_titulo = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
        if m_titulo:
            titulo = m_titulo.group(1).strip()
        cuerpo = re.sub(r"^---.*?---\s*", "", contenido, flags=re.DOTALL)
        cuerpo = re.sub(r"^#\s+.+$", "", cuerpo, count=1, flags=re.MULTILINE).strip()

        lecciones.append(
            Leccion(
                leccion=titulo,
                como_se_resolvio=cuerpo[:500],
                proyecto=proyecto,
                conexiones=f"Origen: {nombre}",
            )
        )
    return lecciones


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------


def _cmd_personal_sync(args) -> None:
    """Consolida proyectos en la BD personal.

    Args:
        args: Namespace con ``--db``, ``--todos`` y ``target``.
    """
    db = PersonalDB(args.db)
    try:
        proyectos: list[tuple[str, str]] = []

        if getattr(args, "todos", False):
            # Escanear ~/Proyectos y ~/Documents por carpetas con .context-map
            for base_dir in (
                os.path.expanduser("~/Proyectos"),
                os.path.expanduser("~/Documents"),
                os.path.expanduser("~/Desktop"),
            ):
                if not os.path.isdir(base_dir):
                    continue
                for entrada in sorted(os.listdir(base_dir)):
                    ruta = os.path.join(base_dir, entrada)
                    if os.path.isdir(ruta) and os.path.isdir(
                        os.path.join(ruta, ".context-map")
                    ):
                        proyectos.append((entrada, ruta))
        else:
            target = getattr(args, "target", ".") or "."
            target = os.path.abspath(target)
            proyectos.append((_nombre_proyecto_por_ruta(target), target))

        total_nuevos = 0
        total_lecciones = 0
        for nombre, ruta in proyectos:
            events_path, chats_path, vault_base = _rutas_proyecto(ruta)

            eventos: list[dict] = []
            for ev in load_events_from_jsonl(events_path):
                eventos.append(ev.to_dict())
            for ev in load_events_from_chat_folder(chats_path):
                eventos.append(ev.to_dict())

            nuevos = db.cargar_eventos(nombre, eventos)
            total_nuevos += nuevos

            for leccion in _leer_lecciones_vault(vault_base, nombre):
                if db.agregar_leccion(leccion):
                    total_lecciones += 1

            print(
                f"sync {nombre}: {len(eventos)} eventos "
                f"(+{nuevos} nuevos), lecciones +{total_lecciones}"
            )

        stats = db.estadisticas()
        print()
        print(f"BD personal: {db.ruta}")
        print(
            f"  proyectos={stats['proyectos']} eventos={stats['eventos']} "
            f"lecciones={stats['lecciones']} decisiones={stats['decisiones']}"
        )
        print(f"  nuevos en esta ejecución: {total_nuevos} eventos, {total_lecciones} lecciones")
    finally:
        db.cerrar()


def _cmd_personal_add(args) -> None:
    """Registra una lección o decisión al vuelo en la BD.

    Args:
        args: Namespace con ``texto``, ``--tipo``, ``--proyecto``,
            ``--contexto``, ``--tags`` y ``--db``.
    """
    db = PersonalDB(args.db)
    try:
        texto = args.texto.strip()
        tipo = getattr(args, "tipo", "leccion") or "leccion"
        proyecto = getattr(args, "proyecto", None)
        contexto = getattr(args, "contexto", "") or ""
        tags = [t.strip() for t in (getattr(args, "tags", "") or "").split(",") if t.strip()]

        if tipo == "decision":
            ok = db.agregar_decision(
                Decision(
                    decision=texto,
                    contexto=contexto,
                    proyecto=proyecto,
                )
            )
            etiqueta = "decisión"
        else:
            ok = db.agregar_leccion(
                Leccion(
                    leccion=texto,
                    como_se_resolvio=contexto,
                    proyecto=proyecto,
                    tags=tags,
                )
            )
            etiqueta = "lección"

        if ok:
            print(f"personal: {etiqueta} guardada en {db.ruta}")
        else:
            print(f"personal: {etiqueta} ya existía (idempotente, sin duplicado)")
    finally:
        db.cerrar()


def _cmd_personal_query(args) -> None:
    """Busca en eventos, lecciones y decisiones con FTS5.

    Args:
        args: Namespace con ``consulta``, ``--proyecto``, ``--limite`` y ``--db``.
    """
    db = PersonalDB(args.db)
    try:
        resultados = db.buscar(
            args.consulta,
            proyecto=getattr(args, "proyecto", None),
            limite=getattr(args, "limite", 10) or 10,
        )
        if not resultados:
            print(f"personal: sin resultados para '{args.consulta}'")
            return

        print(f"personal: {len(resultados)} resultado(s) para '{args.consulta}':")
        print()
        for i, r in enumerate(resultados, 1):
            proy = f" [{r.proyecto}]" if r.proyecto else " [personal]"
            print(f"{i:2d}. ({r.tabla}){proy}")
            print(f"    {r.texto}")
            print()
    finally:
        db.cerrar()


def _cmd_personal_export(args) -> None:
    """Genera un vault personal Obsidian desde la BD.

    Args:
        args: Namespace con ``--destino`` y ``--db``.
    """
    db = PersonalDB(args.db)
    try:
        destino = getattr(args, "destino", None) or os.path.expanduser(
            "~/.context-map/vault-Personal"
        )
        os.makedirs(destino, exist_ok=True)

        secciones: list[str] = ["# Vault Personal — ContextMap", ""]

        # Índice por proyecto
        proyectos = db.listar_proyectos()
        secciones.append("## Proyectos")
        for p in proyectos:
            secciones.append(f"- [[{p}]]")
        secciones.append("")

        # Eventos por proyecto
        for nombre in proyectos:
            filas = db._conn.execute(
                "SELECT tipo, texto, timestamp FROM eventos "
                "JOIN proyectos ON proyectos.id = eventos.proyecto_id "
                "WHERE proyectos.nombre = ? ORDER BY timestamp DESC LIMIT 50",
                (nombre,),
            ).fetchall()
            if not filas:
                continue
            secciones.append(f"## {nombre}")
            for fila in filas:
                tipo = fila["tipo"]
                texto = str(fila["texto"])[:200]
                ts = str(fila["timestamp"] or "")
                secciones.append(f"- **[{tipo}]** {texto} _{ts}_")
            secciones.append("")

        # Lecciones
        filas_lec = db._conn.execute(
            "SELECT leccion, como_se_resolvio, proyectos.nombre AS proy "
            "FROM lecciones LEFT JOIN proyectos ON proyectos.id = lecciones.proyecto_id "
            "ORDER BY lecciones.id"
        ).fetchall()
        if filas_lec:
            secciones.append("## Lecciones")
            for fila in filas_lec:
                proy = f" ({fila['proy']})" if fila["proy"] else ""
                secciones.append(f"### {fila['leccion']}{proy}")
                if fila["como_se_resolvio"]:
                    secciones.append(str(fila["como_se_resolvio"]))
                secciones.append("")

        # Decisiones
        filas_dec = db._conn.execute(
            "SELECT decision, contexto, proyectos.nombre AS proy "
            "FROM decisiones LEFT JOIN proyectos ON proyectos.id = decisiones.proyecto_id "
            "ORDER BY decisiones.id"
        ).fetchall()
        if filas_dec:
            secciones.append("## Decisiones")
            for fila in filas_dec:
                proy = f" ({fila['proy']})" if fila["proy"] else ""
                secciones.append(f"- **{fila['decision']}**{proy}")
                if fila["contexto"]:
                    secciones.append(f"  _{fila['contexto']}_")
            secciones.append("")

        ruta_indice = os.path.join(destino, "00-INDICE.md")
        with open(ruta_indice, "w", encoding="utf-8") as f:
            f.write("\n".join(secciones))

        print(f"personal: vault exportado en {destino}")
        print(f"  archivos: {len(os.listdir(destino))} (índice + notas por proyecto)")
    finally:
        db.cerrar()


def _cmd_personal_backup(args) -> None:
    """Copia la BD personal a otra ruta (pendrive, disco externo).

    Args:
        args: Namespace con ``--destino`` y ``--db``.
    """
    import shutil

    db = PersonalDB(args.db)
    db.cerrar()  # cerrar antes de copiar para garantizar consistencia

    destino = getattr(args, "destino", None)
    if not destino:
        print("personal: usa --destino <ruta> (ej. /run/media/usb/personal.db)")
        return

    os.makedirs(os.path.dirname(os.path.abspath(destino)), exist_ok=True)
    shutil.copy2(db.ruta, destino)
    print(f"personal: backup -> {destino}")
    print(f"  origen: {db.ruta}")


# ---------------------------------------------------------------------------
# Despacho principal
# ---------------------------------------------------------------------------


def cmd_personal(args) -> None:
    """Despacha el subcomando personal solicitado.

    Args:
        args: Namespace de argparse con ``personal_cmd``.
    """
    sub = str(getattr(args, "personal_cmd", "") or "")
    despacho: dict[str, object] = {
        "sync": _cmd_personal_sync,
        "add": _cmd_personal_add,
        "query": _cmd_personal_query,
        "export": _cmd_personal_export,
        "backup": _cmd_personal_backup,
    }
    handler = despacho.get(sub)
    if callable(handler):
        handler(args)
    else:
        print("personal: usa uno de sync | add | query | export | backup")

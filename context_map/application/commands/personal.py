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

            nuevos = db.cargar_eventos(proj_name, eventos, os.path.abspath(target_dir))
            lecciones = 0
            for leccion in _leer_lecciones_vault(vault_base, proj_name):
                if db.agregar_leccion(leccion):
                    lecciones += 1

            decisiones = 0
            for decision in _leer_decisiones_vault(vault_base, proj_name):
                if db.agregar_decision(decision):
                    decisiones += 1

            if nuevos or lecciones or decisiones:
                logger.info(
                    "personal: %s consolidado (+%d eventos, +%d lecciones, +%d decisiones) en %s",
                    proj_name, nuevos, lecciones, decisiones, db.ruta,
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
    """Deriva el nombre del proyecto con la MISMA regla que la consolidación.

    Antes había dos criterios: el descubrimiento de ``sync --todos`` tomaba el
    nombre del vault (``vault-<slug>``, con guiones) y la consolidación
    automática de cada ``ctxmap sync`` usaba la regla de ``project_name``
    (config → repo GitHub → carpeta). El mismo proyecto entraba dos veces en la
    BD personal: «Mitos y Leyendas» y «Mitos-y-Leyendas», 85 eventos cada uno.

    Un solo criterio: el de ``project_name``, que además es el que nombra el
    vault, la carpeta y el brief.

    Args:
        target_dir: Directorio raíz del proyecto.

    Returns:
        str: Nombre estable del proyecto.
    """
    from types import SimpleNamespace

    from context_map.application.commands._helpers import project_name

    return project_name(SimpleNamespace(project=None, target=target_dir))


def _bases_gdrive_estandar() -> list[str]:
    """Carpetas de Google Drive montadas en ubicaciones estándar.

    Returns:
        list[str]: Bases de Drive halladas (ruta raíz y ``Desarrollo y Proyectos``).
    """
    bases: list[str] = []
    for ruta_estandar in [
        os.path.expanduser("~/Google Drive/Mi unidad"),
        os.path.expanduser("~/GoogleDrive/Mi unidad"),
        "G:\\Mi unidad",
        "H:\\Mi unidad",
    ]:
        if os.path.isdir(ruta_estandar):
            bases.append(os.path.join(ruta_estandar, "Desarrollo y Proyectos"))
            bases.append(ruta_estandar)
    return bases


def _bases_gdrive_letras() -> list[str]:
    """Busca ``Mi unidad`` de Google Drive en las letras de unidad de Windows.

    Returns:
        list[str]: Bases de Drive halladas en letras montadas.
    """
    bases: list[str] = []
    for letra in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        unidad = f"{letra}:\\"
        if not os.path.isdir(unidad):
            continue
        mi_unidad = os.path.join(unidad, "Mi unidad")
        if os.path.isdir(mi_unidad):
            bases.append(os.path.join(mi_unidad, "Desarrollo y Proyectos"))
            bases.append(mi_unidad)
    return bases


def _bases_por_defecto() -> list[str]:
    """Carpetas base que se escanean en ``sync --todos``.

    Incluye las carpetas típicas del usuario y cualquier ``Mi unidad`` de
    Google Drive montada (H:, G:, ...) que contenga ``Desarrollo y Proyectos``.

    Returns:
        list[str]: Rutas base a escanear (solo las que podrían existir).
    """
    bases = [
        os.path.expanduser("~/Proyectos"),
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
    ]

    # 1. Rutas configuradas explícitamente vía variable de entorno
    gdrive_env = os.environ.get("CTXMAP_GDRIVE_ROOTS", "").strip()
    if gdrive_env:
        for r in gdrive_env.split(";" if ";" in gdrive_env else ","):
            r_limpia = r.strip()
            if r_limpia and os.path.isdir(r_limpia):
                bases.append(r_limpia)
        return bases

    # 2. Rutas estándar conocidas de Google Drive
    bases.extend(_bases_gdrive_estandar())

    # 3. Búsqueda acotada en letras de unidad montadas en Windows si no se halló en las estándar
    if os.name == "nt" and not any("Mi unidad" in b for b in bases):
        bases.extend(_bases_gdrive_letras())

    return bases


def _descubrir_proyectos(base_dir: str, profundidad: int = 4) -> list[tuple[str, str]]:
    """Descubre proyectos con ``.context-map`` bajo ``base_dir`` (recursivo).

    Una carpeta puede ser proyecto directo (tiene ``.context-map``) y a la vez
    contener subproyectos (ej. ``H:\\...\\GitHub`` con ``.context-map`` propio y
    ``Bot_AX_Contable`` adentro) — se incluyen ambos.

    Args:
        base_dir: Carpeta raíz a explorar.
        profundidad: Máximo de niveles de descenso.

    Returns:
        list[tuple[str, str]]: Pares (nombre_proyecto, ruta).
    """
    encontrados: list[tuple[str, str]] = []
    if os.path.isdir(os.path.join(base_dir, ".context-map")):
        encontrados.append((_nombre_proyecto_por_ruta(base_dir), base_dir))
    if profundidad <= 0:
        return encontrados
    try:
        for entrada in sorted(os.listdir(base_dir)):
            ruta = os.path.join(base_dir, entrada)
            if os.path.isdir(ruta) and not entrada.startswith("."):
                encontrados.extend(_descubrir_proyectos(ruta, profundidad - 1))
    except OSError:
        pass
    return encontrados


def _campo_knowledge(marca: str, cuerpo_nota: str) -> str:
    """Extrae un campo del formato knowledge (marca emoji -> siguiente marca).

    Args:
        marca (str): Marca emoji del campo (p. ej. '🎯 Lección').
        cuerpo_nota (str): Cuerpo de la nota sin frontmatter.

    Returns:
        str: Valor del campo, o string vacío si no se encontró.
    """
    patron = rf"{re.escape(marca)}\s*:?\s*(.*?)(?=\n\s*(?:🎯|🛠️|💬|📋|🔗)|\Z)"
    m = re.search(patron, cuerpo_nota, re.DOTALL)
    return m.group(1).strip() if m else ""


def _parsear_leccion(proyecto: str, cuerpo: str, titulo: str, nombre: str) -> Leccion:
    """Convierte el cuerpo de una nota knowledge en una Leccion estructurada.

    Extrae los 5 campos del formato knowledge (2026-08-13); si la nota no
    tiene el formato estructurado, usa un fallback de cuerpo plano.

    Args:
        proyecto (str): Nombre del proyecto para asociar la lección.
        cuerpo (str): Cuerpo de la nota sin frontmatter.
        titulo (str): Título derivado de la nota (primer encabezado o nombre).
        nombre (str): Nombre del archivo de la nota.

    Returns:
        Leccion: Lección estructurada con los campos disponibles.
    """
    leccion = _campo_knowledge("🎯 Lección", cuerpo)
    leccion = re.sub(r"^#\s*", "", leccion).strip() or titulo
    como = _campo_knowledge("🛠️ Cómo se resolvió", cuerpo)
    prompt = _campo_knowledge("💬 Prompt", cuerpo)
    instruccion = _campo_knowledge("📋 Instrucción", cuerpo)
    conexiones = _campo_knowledge("🔗 Conexiones", cuerpo)
    if not como and not prompt and not instruccion:
        # Fallback: nota sin el formato estructurado → cuerpo plano
        cuerpo_limpio = re.sub(r"^#\s+.+$", "", cuerpo, count=1, flags=re.MULTILINE).strip()
        como = cuerpo_limpio[:500]
        conexiones = f"Origen: {nombre}"
    return Leccion(
        leccion=leccion,
        como_se_resolvio=como,
        prompt=prompt,
        instruccion=instruccion,
        conexiones=conexiones,
        proyecto=proyecto,
    )


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
        # Ignorar índices y notas estructurales
        nombre_upper = nombre.upper()
        if (
            nombre_upper.startswith("00-")
            or "INDICE" in nombre_upper
            or nombre in ("8.0-KNOWLEDGE.md", "README.md", "TEMPLATE.md", "PLANTILLA.md")
        ):
            continue

        ruta = os.path.join(knowledge_dir, nombre)
        try:
            with open(ruta, encoding="utf-8") as f:
                contenido = f.read()
        except OSError:
            continue

        # Validar que contenga contenido estructurado o marca de lección
        cuerpo = re.sub(r"^---.*?---\s*", "", contenido, flags=re.DOTALL).strip()
        if not cuerpo or ("🎯 Lección" not in cuerpo and "## " not in cuerpo):
            continue

        # Extraer título (primer encabezado) y cuerpo limpio de frontmatter
        titulo = nombre[:-3].replace("-", " ").replace("_", " ").strip()
        m_titulo = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
        if m_titulo:
            titulo = m_titulo.group(1).strip()

        lec_obj = _parsear_leccion(proyecto, cuerpo, titulo, nombre)
        if lec_obj and lec_obj.leccion:
            lecciones.append(lec_obj)
    return lecciones


def _leer_decisiones_vault(vault_base: str, proyecto: str) -> list[Decision]:
    """Extrae decisiones de arquitectura y directrices desde el vault.

    Inspecciona carpetas como ``7.0-MANUAL/`` y ``vault-*/`` buscando notas
    con frontmatter ``type: decision``, ``type: directriz``, ``type: regla`` o
    secciones marcadas con ``## Decisiones``.

    Args:
        vault_base: Directorio base de ``.context-map`` del proyecto.
        proyecto: Nombre del proyecto.

    Returns:
        list[Decision]: Lista de decisiones estructuradas.
    """
    decisiones: list[Decision] = []
    candidatos_dirs = [
        os.path.join(vault_base, "vault", "7.0-MANUAL"),
        os.path.join(vault_base, "vault-" + proyecto, "7.0-MANUAL"),
        os.path.join(vault_base, "7.0-MANUAL"),
    ]

    for cdir in candidatos_dirs:
        if not os.path.isdir(cdir):
            continue
        for raiz, _, archivos in os.walk(cdir):
            for arch in archivos:
                if not arch.endswith(".md"):
                    continue
                ruta_arch = os.path.join(raiz, arch)
                try:
                    with open(ruta_arch, encoding="utf-8") as f:
                        contenido = f.read()
                except OSError:
                    continue

                # 1. Si la nota completa es de tipo decision o directriz
                m_type = re.search(r"^type:\s*(decision|directriz|regla|adr)\b", contenido, re.MULTILINE | re.I)
                if m_type:
                    tit = arch[:-3].replace("-", " ").replace("_", " ").strip()
                    m_tit = re.search(r"^#\s+(.+)$", contenido, re.MULTILINE)
                    if m_tit:
                        tit = m_tit.group(1).strip()
                    cuerpo = re.sub(r"^---.*?---\s*", "", contenido, flags=re.DOTALL).strip()
                    decisiones.append(Decision(decision=tit, contexto=cuerpo[:400], proyecto=proyecto))
                    continue

                # 2. Si contiene viñetas en sección ## Decisiones
                m_sec = re.search(r"##\s+(?:🎯\s*)?Decisiones.*?\n(.*?)(?=\n##|\Z)", contenido, re.DOTALL | re.I)
                if m_sec:
                    bloque = m_sec.group(1).strip()
                    for linea in bloque.splitlines():
                        linea_limpia = linea.strip()
                        if linea_limpia.startswith(("-", "*")) and len(linea_limpia) > 5:
                            texto_dec = linea_limpia.lstrip("-* ").strip()
                            decisiones.append(Decision(decision=texto_dec[:200], contexto=f"En {arch}", proyecto=proyecto))

    return decisiones


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------


def _deduplicar_por_ruta(proyectos: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Elimina proyectos repetidos conservando el orden de descubrimiento.

    Las bases de ``sync --todos`` se solapan (``H:\\Mi unidad`` contiene a
    ``H:\\Mi unidad\\Desarrollo y Proyectos``), así que el mismo proyecto se
    descubría y escaneaba 2-3 veces por corrida: 19 hallazgos para 11 proyectos
    reales, con el doble de trabajo y de escrituras en la BD.

    Args:
        proyectos (list[tuple[str, str]]): Pares (nombre, ruta) descubiertos.

    Returns:
        list[tuple[str, str]]: Pares únicos por ruta real.
    """
    vistos: set[str] = set()
    unicos: list[tuple[str, str]] = []
    for nombre, ruta in proyectos:
        clave = os.path.normcase(os.path.realpath(ruta))
        if clave in vistos:
            logger.debug("Proyecto repetido omitido: %s (%s)", nombre, ruta)
            continue
        vistos.add(clave)
        unicos.append((nombre, ruta))
    return unicos


def _proyectos_para_sync(args) -> list[tuple[str, str]]:
    """Determina los proyectos a consolidar según los flags del comando sync.

    Con ``--todos`` recorre las bases por defecto (incluye Google Drive
    ``Mi unidad``) más ``--rutas``; sin él consolida el proyecto objetivo.
    El resultado se deduplica por ruta real (T1.6).

    Args:
        args: Namespace con ``--todos``, ``--rutas`` y ``target``.

    Returns:
        list[tuple[str, str]]: Pares (nombre_proyecto, ruta).
    """
    proyectos: list[tuple[str, str]] = []
    if getattr(args, "todos", False):
        bases = _bases_por_defecto()
        rutas_extra = [
            r.strip()
            for r in (getattr(args, "rutas", "") or "").split(";")
            if r.strip()
        ]
        bases.extend(rutas_extra)
        for base_dir in bases:
            if not os.path.isdir(base_dir):
                continue
            proyectos.extend(_descubrir_proyectos(base_dir))
    else:
        target = getattr(args, "target", ".") or "."
        target = os.path.abspath(target)
        proyectos.append((_nombre_proyecto_por_ruta(target), target))
    return _deduplicar_por_ruta(proyectos)


def _cmd_personal_sync(args) -> None:
    """Consolida proyectos en la BD personal.

    Args:
        args: Namespace con ``--db``, ``--todos`` y ``target``.
    """
    db = PersonalDB(args.db)
    try:
        proyectos = _proyectos_para_sync(args)

        total_nuevos = 0
        total_lecciones = 0
        total_decisiones = 0
        total_omitidos = 0
        for nombre, ruta in proyectos:
            events_path, chats_path, vault_base = _rutas_proyecto(ruta)

            eventos: list[dict] = []
            for ev in load_events_from_jsonl(events_path):
                eventos.append(ev.to_dict())
            for ev in load_events_from_chat_folder(chats_path):
                eventos.append(ev.to_dict())

            lecciones = _leer_lecciones_vault(vault_base, nombre)
            decisiones = _leer_decisiones_vault(vault_base, nombre)

            # Un proyecto sin eventos, lecciones ni decisiones no aporta a la memoria global
            if not eventos and not lecciones and not decisiones:
                total_omitidos += 1
                print(f"sync {nombre}: sin contenido, omitido")
                continue

            nuevos = db.cargar_eventos(nombre, eventos, ruta)
            total_nuevos += nuevos

            # Contadores POR PROYECTO
            lecciones_proyecto = 0
            for leccion in lecciones:
                if db.agregar_leccion(leccion):
                    total_lecciones += 1
                    lecciones_proyecto += 1

            decisiones_proyecto = 0
            for decision in decisiones:
                if db.agregar_decision(decision):
                    total_decisiones += 1
                    decisiones_proyecto += 1

            print(
                f"sync {nombre}: {len(eventos)} eventos (+{nuevos} nuevos), "
                f"lecciones +{lecciones_proyecto}, decisiones +{decisiones_proyecto}"
            )

        stats = db.estadisticas()
        print()
        print(f"BD personal: {db.ruta}")
        print(
            f"  proyectos={stats['proyectos']} eventos={stats['eventos']} "
            f"lecciones={stats['lecciones']} decisiones={stats['decisiones']}"
        )
        print(f"  nuevos en esta ejecución: {total_nuevos} eventos, {total_lecciones} lecciones, {total_decisiones} decisiones")
        if total_omitidos:
            print(f"  omitidos por no tener contenido: {total_omitidos}")
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
        if getattr(args, "json", False):
            # Salida estructurada para uso programático / agentes
            import json as _json

            print(
                _json.dumps(
                    [
                        {
                            "tabla": r.tabla,
                            "texto": r.texto,
                            "proyecto": r.proyecto,
                            "puntaje": r.puntaje,
                        }
                        for r in resultados
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
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


def _generar_slugs_unicos(nombres_proyectos: list[str]) -> dict[str, str]:
    """Genera slugs deterministas y únicos para una lista de proyectos.

    Evita colisiones entre nombres como 'Mitos y Leyendas' y 'Mitos-y-Leyendas'
    asignando un sufijo numérico cuando dos proyectos producen el mismo slug.

    Args:
        nombres_proyectos: Lista de nombres de proyectos.

    Returns:
        dict[str, str]: Mapeo de nombre_proyecto -> slug_unico.
    """
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
    """Sanea el texto de markdown para no romper la jerarquía del índice.

    - Elimina encabezados Markdown (#, ##, ###) para evitar romper la jerarquía de secciones.
    - Convierte wikilinks [[destino|alias]] o [[destino]] en texto plano alias o destino
      para evitar crear wikilinks rotos (fantasmas) en el vault personal.

    Args:
        texto: Cadena original de texto.

    Returns:
        str: Texto limpio y plano.
    """
    if not texto:
        return ""
    # Quitar wikilinks
    sin_wikilinks = re.sub(r"\[\[([^|\]]+\|)?([^\]]+)\]\]", r"\2", texto)
    # Quitar encabezados iniciales o intermedios (#, ##, ###)
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
    """Añade la sección de notas reales por proyecto (<slug>.md) v2.

    Escribe una nota por proyecto con sus metadatos, riesgos vigentes,
    pendientes y eventos agrupados por día, asegurando 0 wikilinks rotos
    y 1 nota física por cada proyecto.

    Args:
        db: Base de datos personal abierta.
        destino: Directorio de salida del vault personal.
        secciones: Acumulador de líneas del índice.

    Returns:
        list[str]: Acumulador actualizado con la sección de proyectos.
    """
    proyectos = db.listar_proyectos()
    secciones.append("## Proyectos")
    os.makedirs(destino, exist_ok=True)

    slug_map = _generar_slugs_unicos(proyectos)
    notas_escritas = 0

    for nombre in proyectos:
        slug = slug_map[nombre]
        ruta_nota = os.path.join(destino, f"{slug}.md")

        # Obtener metadatos del proyecto
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

        # Pie de navegación de regreso al índice
        lineas_nota.append("---")
        lineas_nota.append("[[00-INDICE|⬅ Volver al Índice General]]")

        with open(ruta_nota, "w", encoding="utf-8") as f:
            f.write("\n".join(lineas_nota))

        notas_escritas += 1
        secciones.append(f"- [[{slug}|{nombre}]]")

    secciones.append("")
    # Verificación de consistencia: 1 nota por proyecto
    assert notas_escritas == len(proyectos), (
        f"Inconsistencia en export: {notas_escritas} notas escritas para {len(proyectos)} proyectos"
    )
    return secciones


def _seccion_lecciones(db: PersonalDB, secciones: list[str]) -> list[str]:
    """Añade la sección de lecciones compacta al índice del vault personal v2.

    Args:
        db: Base de datos personal abierta.
        secciones: Acumulador de líneas del índice.

    Returns:
        list[str]: Acumulador actualizado con la sección de lecciones.
    """
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

            # Mostrar instrucción o cómo se resolvió de forma compacta (<=250 caracteres)
            instruccion = str(fila["instruccion"] or fila["como_se_resolvio"] or "")
            inst_limpia = _sanear_texto_markdown(instruccion)
            if inst_limpia:
                if len(inst_limpia) > 250:
                    inst_limpia = inst_limpia[:247] + "..."
                secciones.append(f"> 📋 **Instrucción**: {inst_limpia}")
            secciones.append("")
    return secciones


def _seccion_decisiones(db: PersonalDB, secciones: list[str]) -> list[str]:
    """Añade la sección de decisiones al índice del vault personal.

    Args:
        db: Base de datos personal abierta.
        secciones: Acumulador de líneas del índice.

    Returns:
        list[str]: Acumulador actualizado con la sección de decisiones.
    """
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
    """Genera un vault personal Obsidian desde la BD v2.

    Crea una nota REAL por proyecto (``<slug>.md`` con sus eventos) y un
    ``00-INDICE.md`` cuyos wikilinks apuntan a esas notas — sin nodos
    fantasma (los [[...]] siempre tienen su archivo existente).

    Args:
        args: Namespace con ``--destino`` y ``--db``.
    """
    db = PersonalDB(getattr(args, "db", None))
    try:
        destino = getattr(args, "destino", None) or os.path.expanduser(
            "~/.context-map/vault-Personal"
        )
        os.makedirs(destino, exist_ok=True)

        secciones: list[str] = ["# 🌐 Vault Personal — ContextMap", ""]

        # Nota real por proyecto (con sus eventos y metadatos)
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


def _cmd_personal_panorama(args) -> None:
    """Genera y muestra el tablero general de actividad multi-proyecto.

    Args:
        args: Namespace con ``--dias``, ``--proyecto``, ``--solo-sesiones``, ``--json`` y ``--db``.
    """
    import json
    from context_map.core.personal.panorama import (
        construir_panorama,
        formatear_panorama_texto,
    )

    db = PersonalDB(getattr(args, "db", None))
    try:
        dias = int(getattr(args, "dias", 14) or 14)
        proyecto = getattr(args, "proyecto", None)
        solo_sesiones = bool(getattr(args, "solo_sesiones", False))
        json_output = bool(getattr(args, "json", False))

        report = construir_panorama(
            db=db,
            dias=dias,
            proyecto=proyecto,
            solo_sesiones=solo_sesiones,
        )

        if json_output:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(formatear_panorama_texto(report))
    finally:
        db.cerrar()


def _cmd_personal_timeline(args) -> None:
    """Genera y muestra la línea temporal agregada de sesiones y eventos.

    Args:
        args: Namespace con ``--dias``, ``--proyecto``, ``--json`` y ``--db``.
    """
    import json
    from dataclasses import asdict
    from context_map.core.personal.panorama import (
        construir_timeline,
        formatear_timeline_texto,
    )

    db = PersonalDB(getattr(args, "db", None))
    try:
        dias = int(getattr(args, "dias", 30) or 30)
        proyecto = getattr(args, "proyecto", None)
        json_output = bool(getattr(args, "json", False))

        items = construir_timeline(
            db=db,
            dias=dias,
            proyecto=proyecto,
        )

        if json_output:
            print(json.dumps([asdict(it) for it in items], indent=2, ensure_ascii=False))
        else:
            print(formatear_timeline_texto(items))
    finally:
        db.cerrar()


def _cmd_personal_repair(args) -> None:
    """Ejecuta el saneamiento y reparación integral de la BD personal.

    Args:
        args: Namespace con flags de repair y ``--db``.
    """
    import json
    from context_map.core.personal.repair import (
        formatear_repair_texto,
        reparar_bd_personal,
    )

    db = PersonalDB(getattr(args, "db", None))
    try:
        dry_run = bool(getattr(args, "dry_run", False))
        is_all = bool(getattr(args, "all", False))
        merge_duplicados = is_all or bool(getattr(args, "merge_duplicados", False))
        fill_ruta = is_all or bool(getattr(args, "fill_ruta", False))
        drop_vacios = is_all or bool(getattr(args, "drop_vacios", False))
        purge_ruido = is_all or bool(getattr(args, "purge_ruido", False))
        vacuum = is_all or bool(getattr(args, "vacuum", False))
        json_output = bool(getattr(args, "json", False))

        # Si no se pasó ningún flag específico ni --all, ejecutar todas las reparaciones por defecto
        if not (merge_duplicados or fill_ruta or drop_vacios or purge_ruido or vacuum):
            merge_duplicados = fill_ruta = drop_vacios = purge_ruido = vacuum = True

        rutas_extra = [
            r.strip()
            for r in (getattr(args, "rutas", "") or "").split(";")
            if r.strip()
        ]

        report = reparar_bd_personal(
            db=db,
            dry_run=dry_run,
            merge_duplicados=merge_duplicados,
            fill_ruta=fill_ruta,
            drop_vacios=drop_vacios,
            purge_ruido=purge_ruido,
            vacuum=vacuum,
            rutas_busqueda=rutas_extra,
        )

        if json_output:
            print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        else:
            print(formatear_repair_texto(report))
    finally:
        db.cerrar()


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
        "panorama": _cmd_personal_panorama,
        "timeline": _cmd_personal_timeline,
        "repair": _cmd_personal_repair,
    }
    handler = despacho.get(sub)
    if callable(handler):
        handler(args)
    else:
        print("personal: usa uno de sync | add | query | export | backup | panorama | timeline | repair")


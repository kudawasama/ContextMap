"""Esqueleto del mundo CONOCIMIENTO (namespace ``knowledge``).

Siembra ``90-CONOCIMIENTO/`` — el segundo mundo del vault, independiente del
mundo de código (namespace ``code``). Implementa la fusión del curso de
Obsidian (Second Brain de Tiago Forte + LLM Wiki de Karpathy) sin colisionar
con la topología del proyecto:

- **PARA**: 00-INBOX, 01-PROJECTS, 02-AREAS, 03-RESOURCES, 04-ARCHIVE.
- **LLM Wiki**: 05-WIKI (resúmenes, entidades, entry log).

Reglas:
- Es **idempotente**: solo crea el esqueleto si no existe; nunca sobrescribe.
- Todo es ``preserve: true`` y ``namespace: knowledge``: el build de código
  nunca lo regenera ni lo borra (ver ``ZONAS_MANUALES``).
- **Cero wikilinks cruzados**: estas notas solo se enlazan entre sí; el índice
  de código (``00-INDICE``) no las lista.
"""

from __future__ import annotations

import os
from datetime import datetime

NS_CONOCIMIENTO = "90-CONOCIMIENTO"
ROOT_FILE = "90-CONOCIMIENTO.md"

# (ruta relativa, título, cuerpo) del esqueleto. Los backlinks del pie cierran
# el árbol: cada nota cuelga de exactamente un padre.
_FRONTMATTER = """---
type: indice
namespace: knowledge
preserve: true
created: {fecha}
title: "{titulo}"
tags: [{tags}]
---
"""


def _nota(titulo: str, cuerpo: str, padre: str | None, tags: str, fecha: str) -> str:
    """Construye una nota del mundo conocimiento con frontmatter y pie.

    Args:
        titulo (str): Título visible de la nota.
        cuerpo (str): Cuerpo Markdown (sin frontmatter ni pie).
        padre (str | None): Ruta del nodo padre para el backlink; ``None`` para
            la raíz (``90-CONOCIMIENTO.md``).
        tags (str): CSV de etiquetas.
        fecha (str): Timestamp ISO de creación.

    Returns:
        str: Contenido completo de la nota.
    """
    partes = [_FRONTMATTER.format(fecha=fecha, titulo=titulo, tags=tags).rstrip()]
    partes.append("")
    partes.append(cuerpo.rstrip())
    partes.append("")
    if padre:
        partes.append("---")
        partes.append(f"[[{padre}|⬅ Volver a {padre.split('/')[-1]}]]")
        partes.append("")
    return "\n".join(partes)


def _definiciones(fecha: str) -> dict[str, str]:
    """Devuelve el mapa ruta-relativa → contenido del esqueleto PKM.

    Args:
        fecha (str): Timestamp ISO de creación de las notas.

    Returns:
        dict[str, str]: Ruta relativa (bajo ``90-CONOCIMIENTO/``) → contenido.
    """
    raiz = NS_CONOCIMIENTO
    return {
        ROOT_FILE: _nota(
            "90 Conocimiento",
            f"""# 🧠 90 CONOCIMIENTO — Second Brain + LLM Wiki

> Este es el **mundo CONOCIMIENTO** (namespace `knowledge`). Vive en el mismo
> vault que el proyecto, pero es una **isla separada**: el build de código
> jamás lo regenera ni lo borra, y no enlaza notas del proyecto.

Metodología: **PARA** (Projects · Areas · Resources · Archive) + **LLM Wiki**
(resúmenes, entidades y bitácora).

## 📂 Secciones

- [[{raiz}/00-INBOX/00-INBOX|📥 00 Inbox]]
- [[{raiz}/01-PROJECTS/01-PROJECTS|🎯 01 Projects]]
- [[{raiz}/02-AREAS/02-AREAS|🔁 02 Areas]]
- [[{raiz}/03-RESOURCES/03-RESOURCES|📚 03 Resources]]
- [[{raiz}/04-ARCHIVE/04-ARCHIVE|🗄️ 04 Archive]]
- [[{raiz}/05-WIKI/05-WIKI|🧩 05 Wiki]]

## 🔄 Flujo

1. Capturá en `00-INBOX` (`ctxmap inbox add "..."`).
2. Depurá (`ctxmap inbox purge`) → el agente clasifica a PARA.
3. Consultá (`ctxmap wiki query "..."`) y cuidá la salud (`ctxmap wiki lint`).""",
            padre=None,
            tags="knowledge, pkm, para, wiki",
            fecha=fecha,
        ),
        "00-INBOX/00-INBOX.md": _nota(
            "00 Inbox",
            """# 📥 00 INBOX — Captura cruda

> Todo entra acá sin pensar dónde va. Después `ctxmap inbox purge` clasifica a
> PARA (o a la wiki) y vacía el inbox.

## 📝 Notas en el inbox

- _(vacío — agregá con `ctxmap inbox add "..."`)_""",
            padre=raiz,
            tags="knowledge, inbox",
            fecha=fecha,
        ),
        "01-PROJECTS/01-PROJECTS.md": _nota(
            "01 Projects",
            """# 🎯 01 PROJECTS — Cosas con fin

> Proyectos con resultado concreto y fecha de fin (publicar un artículo, un
> curso, implementar un sistema). Cuando terminan → 04-ARCHIVE.

## 📝 Proyectos

- _(vacío)_""",
            padre=raiz,
            tags="knowledge, para, projects",
            fecha=fecha,
        ),
        "02-AREAS/02-AREAS.md": _nota(
            "02 Areas",
            """# 🔁 02 AREAS — Responsabilidades permanentes

> Áreas que nunca terminan: trabajo, salud, formación, un hobby. No tienen
> fecha de fin; se mantienen en el tiempo.

## 📝 Áreas

- _(vacío)_""",
            padre=raiz,
            tags="knowledge, para, areas",
            fecha=fecha,
        ),
        "03-RESOURCES/03-RESOURCES.md": _nota(
            "03 Resources",
            """# 📚 03 RESOURCES — Temas de interés

> Conocimiento que quizá uses en el futuro, sin proyecto ni fecha asociada.
> Es el "lo guardo porque me va a servir".

## 📝 Recursos

- _(vacío)_""",
            padre=raiz,
            tags="knowledge, para, resources",
            fecha=fecha,
        ),
        "04-ARCHIVE/04-ARCHIVE.md": _nota(
            "04 Archive",
            """# 🗄️ 04 ARCHIVE — Lo cerrado

> Proyectos, áreas o recursos que ya no se usan. Se guardan por historia,
> fuera del foco activo.

## 📝 Archivado

- _(vacío)_""",
            padre=raiz,
            tags="knowledge, para, archive",
            fecha=fecha,
        ),
        "05-WIKI/05-WIKI.md": _nota(
            "05 Wiki",
            f"""# 🧩 05 WIKI — LLM Wiki (patrón Karpathy)

> Páginas que escribe el agente: resúmenes de fuentes, entidades/conceptos y
> una bitácora. Operaciones: `ingest`, `query` (con citas), `lint` (salud).

## 📚 Subsecciones

- [[{raiz}/05-WIKI/resumenes/resumenes|📄 Resúmenes de fuentes]]
- [[{raiz}/05-WIKI/entidades/entidades|🔖 Entidades / conceptos]]
- [[{raiz}/05-WIKI/entry-log|🧾 Entry log]]""",
            padre=raiz,
            tags="knowledge, wiki, llm-wiki",
            fecha=fecha,
        ),
        "05-WIKI/entry-log.md": _nota(
            "Entry log",
            """# 🧾 Entry log

> Bitácora cronológica de lo que entra a la wiki.

| Fecha | Acción | Página |
|---|---|---|
| — | — | — |""",
            padre=f"{raiz}/05-WIKI/05-WIKI",
            tags="knowledge, wiki, entry-log",
            fecha=fecha,
        ),
        "05-WIKI/entidades/entidades.md": _nota(
            "Entidades",
            """# 🔖 Entidades / conceptos

> Una página por concepto importante (con su definición y enlaces). El `lint`
> detecta conceptos mencionados que todavía no tienen página.

## 🔖 Páginas

- _(vacío)_""",
            padre=f"{raiz}/05-WIKI/05-WIKI",
            tags="knowledge, wiki, entidades",
            fecha=fecha,
        ),
        "05-WIKI/resumenes/resumenes.md": _nota(
            "Resúmenes",
            """# 📄 Resúmenes de fuentes

> Una página por fuente ingerida (artículo, video, PDF, chat): resumen,
> puntos clave y enlaces a las entidades relacionadas.

## 📄 Resúmenes

- _(vacío)_""",
            padre=f"{raiz}/05-WIKI/05-WIKI",
            tags="knowledge, wiki, resumenes",
            fecha=fecha,
        ),
    }


def sembrar_conocimiento(output_dir: str) -> bool:
    """Crea el esqueleto de ``90-CONOCIMIENTO/`` si aún no existe.

    Idempotente: si la raíz ya existe, no sobrescribe nada (el mundo PKM es del
    usuario/agente). Asegura las subcarpetas aunque el índice ya exista.

    Args:
        output_dir (str): Directorio raíz del vault Obsidian.

    Returns:
        bool: True si creó el esqueleto; False si ya existía.
    """
    raiz_dir = os.path.join(output_dir, NS_CONOCIMIENTO)
    root_path = os.path.join(raiz_dir, ROOT_FILE)

    existia = os.path.exists(root_path)
    fecha = datetime.now().isoformat(timespec="seconds")

    for rel, contenido in _definiciones(fecha).items():
        destino = os.path.join(raiz_dir, rel)
        if existia and os.path.exists(destino):
            continue  # respetar el trabajo del usuario/agente
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "w", encoding="utf-8") as f:
            f.write(contenido)

    # Carpetas destino para las futuras notas del agente.
    for sub in ("entidades", "resumenes"):
        os.makedirs(os.path.join(raiz_dir, "05-WIKI", sub), exist_ok=True)

    return not existia

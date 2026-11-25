"""Reglas fijas de estabilidad del motor (invariantes no negociables).

Un **invariante** es una condición que ContextMap exige siempre para poder
confiar en su propio diagnóstico. Cada invariante se apoya en un chequeo del
``doctor`` ya existente; aquí solo se declara el contrato: nombre, chequeo que
lo mide, severidad con la que se incumple y cómo se repara.

Para qué sirve:

- **Puerta de calidad**: ``ctxmap doctor --strict-warn`` devuelve código 1 si
  cualquier invariante se incumple, de modo que la CI o el humano que cierra la
  sesión no puede ignorar un aviso.
- **Contrato ejecutable**: ``context_map/__tests__/test_invariantes.py``
  verifica que cada invariante declarado aquí siga existiendo en
  ``doctor.CHECKS``. Si alguien borra o renombra un chequeo, el test lo dice.

Estas reglas son del MOTOR (el intérprete, las dependencias y el vault). Las
reglas de NEGOCIO del proyecto viven en ``references/reglas/reglas_registro.yaml``
y las lee ``context_map/domain/reglas/reglas.py``; no se mezclan.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Invariante:
    """Regla fija de estabilidad y la forma de comprobarla.

    Attributes:
        nombre (str): Identificador legible de la regla.
        chequeo (str): Nombre del chequeo del ``doctor`` que la mide.
        severidad (str): Estado que delata el incumplimiento ("FAIL" o "WARN").
        motivo (str): Por qué la regla existe y qué se rompe si se ignora.
        reparacion (str): Comando o acción concreta para volver al estado válido.
    """

    nombre: str
    chequeo: str
    severidad: str
    motivo: str
    reparacion: str


#: Catálogo único de invariantes del motor. El orden es el de ejecución.
INVARIANTES: tuple[Invariante, ...] = (
    Invariante(
        nombre="interprete_del_proyecto",
        chequeo="interpreter",
        severidad="WARN",
        motivo=(
            "Las dependencias reales (pydantic, mcp, pymupdf) viven en el venv. "
            "Ejecutar con otro Python hace que el doctor mienta y que el suite "
            "se recolecte a medias."
        ),
        reparacion='.venv/Scripts/python.exe -m context_map.cli doctor .',
    ),
    Invariante(
        nombre="dependencias_mcp_importables",
        chequeo="mcp_deps",
        severidad="FAIL",
        motivo=(
            "FastMCP crea el modelo de salida con create_model(result=<tipo>) y "
            "pydantic < 2.13 lo rechaza: sin esto, todas las tools MCP dejan de "
            "existir sin aviso."
        ),
        reparacion='.venv/Scripts/python.exe -m pip install -e ".[mcp]"',
    ),
    Invariante(
        nombre="vault_unico_por_proyecto",
        chequeo="vault_default",
        severidad="WARN",
        motivo=(
            "Dos vaults en el mismo proyecto hacen que el agente lea memoria "
            "distinta según el orden del directorio."
        ),
        reparacion="ctxmap doctor --fix .",
    ),
    Invariante(
        nombre="notas_manuales_intactas",
        chequeo="manual_notes_preservation",
        severidad="WARN",
        motivo=(
            "Una nota manual sin 'preserve: true' puede ser sobrescrita por el "
            "siguiente build: se pierde historia escrita por una persona."
        ),
        reparacion="ctxmap doctor --fix .",
    ),
    Invariante(
        nombre="topologia_de_arbol",
        chequeo="topologia",
        severidad="WARN",
        motivo=(
            "El gráfico de Obsidian solo es legible si cada nota cuelga de un "
            "único padre; un enlace roto o una nota huérfana rompe la navegación."
        ),
        reparacion="ctxmap build --clean --brief .",
    ),
    Invariante(
        nombre="indice_fts5_al_dia",
        chequeo="vault_index",
        severidad="WARN",
        motivo=(
            "El índice FTS5 es derivado del vault: si se queda atrás, la "
            "búsqueda devuelve pasado en lugar de presente."
        ),
        reparacion="ctxmap build .",
    ),
    Invariante(
        nombre="historial_acotado",
        chequeo="history",
        severidad="WARN",
        motivo="Un historial sin poda infla el contexto hasta hacerlo inútil.",
        reparacion="ctxmap history prune .",
    ),
    Invariante(
        nombre="contexto_fresco",
        chequeo="context_freshness",
        severidad="WARN",
        motivo=(
            "Un brief viejo es peor que no tener brief: el agente decide con "
            "estado que ya no existe."
        ),
        reparacion="ctxmap refresh .",
    ),
    Invariante(
        nombre="etiquetas_del_vault",
        chequeo="vault_tags",
        severidad="WARN",
        motivo=(
            "Una etiqueta mal escrita no rompe nada visible: la nota desaparece "
            "del grafo y de la búsqueda en silencio. Si no se mide, se acumula."
        ),
        reparacion="corregir `tags:` en el frontmatter de la nota señalada",
    ),
    Invariante(
        nombre="commits_validos",
        chequeo="commits_convencionales",
        severidad="WARN",
        motivo=(
            "Un historial sin forma no se puede leer ni filtrar: el tipo del "
            "commit es la única señal de qué cambió y por qué."
        ),
        reparacion="usar `tipo(alcance): asunto` en el próximo commit",
    ),
    Invariante(
        nombre="changelog_al_dia",
        chequeo="changelog_commit",
        severidad="WARN",
        motivo=(
            "Un cambio de código sin entrada en el CHANGELOG es un cambio que "
            "la próxima versión explicará mal."
        ),
        reparacion="registrar el cambio en `CHANGELOG.md` y commitearlo junto",
    ),
    Invariante(
        nombre="diario_del_dia",
        chequeo="diario_del_dia",
        severidad="WARN",
        motivo=(
            "El diario es lo único que conserva el porqué de una sesión: el "
            "diff dice qué cambió, nunca qué se descartó ni por qué."
        ),
        reparacion="escribir `7.0-MANUAL/Diario/<hoy>.md` en el vault",
    ),
    Invariante(
        nombre="sin_secretos",
        chequeo="secretos_versionados",
        severidad="WARN",
        motivo=(
            "Un secreto versionado queda en el historial para siempre; borrar "
            "el commit no lo elimina."
        ),
        reparacion="rotar el secreto y sacarlo del historial de git",
    ),
    Invariante(
        nombre="version_anunciada",
        chequeo="version_documentada",
        severidad="WARN",
        motivo=(
            "Una versión que no está en el CHANGELOG no tiene historia: nadie sabe qué cambió."
        ),
        reparacion="anunciar la versión en `CHANGELOG.md`",
    ),
    Invariante(
        nombre="sin_derivados_versionados",
        chequeo="derivados_fuera_de_git",
        severidad="WARN",
        motivo=(
            "El vault se regenera y el estado se pierde: versionarlos llena el índice de ruido que miente."
        ),
        reparacion="sacar `.context-map/` del índice y añadirlo a `.gitignore`",
    ),
    Invariante(
        nombre="raiz_sin_sueltos",
        chequeo="raiz_limpia",
        severidad="WARN",
        motivo=(
            "Un archivo suelto en la raíz es un archivo que nadie encuentra después."
        ),
        reparacion="moverlo a su capa o declararlo en la norma (`AGENTS.md` §1.1)",
    ),
    Invariante(
        nombre="capas_sin_retroceso",
        chequeo="capas_respetadas",
        severidad="WARN",
        motivo=(
            "Un import que sube de capa convierte la arquitectura en un dibujo; el tope congela la deuda y prohíbe la nueva."
        ),
        reparacion="resolver la dependencia hacia dentro o bajarla por inyección",
    ),
    Invariante(
        nombre="dominio_con_test",
        chequeo="modulos_con_test",
        severidad="WARN",
        motivo=(
            "Un submódulo de dominio sin test es código que se puede romper en silencio."
        ),
        reparacion="escribir el test del submódulo en `context_map/__tests__/`",
    ),
    Invariante(
        nombre="codigo_documentado",
        chequeo="docstrings_y_tipos",
        severidad="WARN",
        motivo=(
            "Sin docstring ni tipos, el siguiente que lea el módulo tiene que ejecutarlo para entenderlo."
        ),
        reparacion="docstring de módulo y anotaciones completas en la firma",
    ),
    Invariante(
        nombre="documentacion_en_espanol",
        chequeo="idioma_de_la_documentacion",
        severidad="WARN",
        motivo=(
            "Un documento en otro idioma parte la memoria del proyecto en dos."
        ),
        reparacion="traducir el documento o marcarlo como traducción (`*_EN.md`)",
    ),
    Invariante(
        nombre="dominio_explicado",
        chequeo="dominio_documentado",
        severidad="WARN",
        motivo=(
            "Si la lógica nuclear solo vive en el código, cada cambio empieza releyéndolo entero."
        ),
        reparacion="redactar `7.0-MANUAL/DOMINIO.md` en el vault",
    ),
    Invariante(
        nombre="fuentes_al_dia",
        chequeo="fuentes_procesadas",
        severidad="WARN",
        motivo=(
            "Una fuente sin procesar es contexto que el agente no tiene y cree tener."
        ),
        reparacion="ejecutar `ctxmap refresh .`",
    ),
    Invariante(
        nombre="lecciones_reutilizables",
        chequeo="lecciones_completas",
        severidad="WARN",
        motivo=(
            "Una lección sin «cómo se resolvió» no se puede volver a aplicar: es un recuerdo, no una lección."
        ),
        reparacion="completar las cinco secciones de la lección",
    ),
    Invariante(
        nombre="notas_redactadas",
        chequeo="notas_sin_plantilla",
        severidad="WARN",
        motivo=(
            "Una nota con marcadores de plantilla ocupa el grafo sin decir nada."
        ),
        reparacion="redactar la nota o borrarla si no aporta",
    ),
    Invariante(
        nombre="vault_con_peso_acotado",
        chequeo="vault_acotado",
        severidad="WARN",
        motivo=(
            "Un vault sin tope acaba costando más de leer que el problema que resuelve."
        ),
        reparacion="podar lo que ya no se usa o `build` por secciones",
    ),
)


def reglas_por_chequeo() -> dict[str, Invariante]:
    """Indexa los invariantes por el nombre del chequeo que los mide.

    Returns:
        dict[str, Invariante]: Mapa ``chequeo -> invariante``.
    """
    return {inv.chequeo: inv for inv in INVARIANTES}


def incumplidas(report) -> list[Invariante]:
    """Devuelve los invariantes incumplidos por un reporte del doctor.

    Args:
        report: ``DoctorReport`` con los chequeos ya ejecutados.

    Returns:
        list[Invariante]: Invariantes cuyo chequeo terminó en FAIL (si la
            severidad es "FAIL") o en FAIL/WARN (si es "WARN").
    """
    por_chequeo = reglas_por_chequeo()
    estados = {c.name: c.status for c in report.checks}
    rotos: list[Invariante] = []
    for chequeo, inv in por_chequeo.items():
        estado = estados.get(chequeo)
        if estado is None:
            continue
        if estado == "FAIL" or (inv.severidad == "WARN" and estado == "WARN"):
            rotos.append(inv)
    return rotos

"""Contrato de los wikilinks del vault.

Regresión del bug que dejaba huérfanos los batches de ideas completadas: el
índice escribía ``[[01-GENERAL-01-01.md|[f51c772] feat: …]]`` y el corchete del
alias cerraba el enlace antes de tiempo, así que el validador de topología (y el
Graph View de Obsidian) perdían la arista padre → hijo.
"""

from __future__ import annotations

import os
import re

import pytest

from context_map.presentation.vault.topologia import analizar_topologia, texto_enlazable
from context_map.presentation.vault.wikilink import (
    alias_seguro,
    destino_seguro,
    enlace,
)

LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


class TestAliasSeguro:
    """El alias es texto de presentación y nunca debe romper el enlace."""

    def test_neutraliza_corchetes_de_un_titulo_de_commit(self) -> None:
        assert alias_seguro("[f51c772] feat: v1.2.0") == "(f51c772) feat: v1.2.0"

    def test_neutraliza_el_separador_de_alias(self) -> None:
        assert "|" not in alias_seguro("riesgo | mitigación")

    def test_neutraliza_almohadilla_y_acento_caret(self) -> None:
        limpio = alias_seguro("#encabezado ^bloque")
        assert "#" not in limpio
        assert "^" not in limpio

    def test_colapsa_saltos_de_linea_y_espacios(self) -> None:
        assert alias_seguro("linea uno\nlinea   dos\t") == "linea uno linea dos"

    def test_acepta_none_y_vacio(self) -> None:
        assert alias_seguro(None) == ""
        assert alias_seguro("") == ""

    def test_respeta_el_limite(self) -> None:
        assert len(alias_seguro("x" * 120, 50)) == 50


class TestDestinoSeguro:
    """El destino apunta a la nota: sin extensión y con separador '/'."""

    def test_quita_la_extension_md(self) -> None:
        assert destino_seguro("01-GENERAL-01-01.md") == "01-GENERAL-01-01"

    def test_normaliza_separadores_de_windows(self) -> None:
        assert destino_seguro("2.0-IDEAS\\2.1\\nota.md") == "2.0-IDEAS/2.1/nota"

    def test_quita_barras_sobrantes(self) -> None:
        assert destino_seguro("/nota/") == "nota"


class TestEnlace:
    """El enlace generado debe ser parseable por el validador de topología."""

    def test_enlace_con_alias_es_parseable(self) -> None:
        link = enlace("01-GENERAL-01-01.md", "[f51c772] feat: algo")
        assert link == "[[01-GENERAL-01-01|(f51c772) feat: algo]]"
        assert LINK_RE.findall(link) == ["01-GENERAL-01-01|(f51c772) feat: algo"]

    def test_enlace_sin_alias(self) -> None:
        assert enlace("nota.md") == "[[nota]]"

    def test_enlace_en_tabla_escapa_el_separador(self) -> None:
        link = enlace("nota.md", "alias", tabla=True)
        assert link == "[[nota\\|alias]]"

    def test_alias_con_corchete_no_trunca_el_destino(self) -> None:
        """Antes el regex casaba solo hasta el primer ']' del alias."""
        link = enlace("nota", "uno [dos] tres")
        destino = LINK_RE.findall(link)[0].split("|")[0]
        assert destino == "nota"


@pytest.mark.parametrize(
    "titulo",
    [
        "[f51c772] feat: v1.2.0 — dedup de nodos",
        "fix: [[plantilla]] rota | con pipe",
        "docs: #seccion y ^bloque",
    ],
)
def test_titulos_hostiles_generan_enlaces_de_un_solo_match(titulo: str) -> None:
    """Un título hostil produce exactamente un enlace, no un fragmento suelto."""
    link = enlace("nota-destino.md", titulo)
    assert len(LINK_RE.findall(link)) == 1


def test_el_indice_de_batches_genera_el_padre(tmp_path) -> None:
    """Un índice de concepto debe enlazar su batch de forma resoluble.

    Reproduce el caso real ``GENERAL-Completas.md`` → ``01-GENERAL-01-01.md``
    con un título que empieza por corchete.
    """
    from context_map.core.models import Node
    from context_map.presentation.vault.consolidated.notas_ideas import (
        _nombre_batch_idea,
    )

    node = Node(
        id="n1",
        type="IDEA",
        title="[f51c772] feat: v1.2.0 — dedup de nodos",
        status="completado",
        summary="",
        evidence=[],
    )
    slug = _nombre_batch_idea(0, 1, "GENERAL")
    link = enlace(slug, node.title)

    coincidencias = LINK_RE.findall(link)
    assert coincidencias, "el índice debe producir un wikilink parseable"
    assert coincidencias[0].split("|")[0] == "01-GENERAL-01-01"
    assert os.sep not in coincidencias[0].split("|")[0]


class TestValidadorIgnoraCodigo:
    """Un wikilink documentado dentro de código no es una arista del grafo."""

    def _vault_minimo(self, tmp_path, nota_extra: str):
        """Crea un vault de dos notas: índice padre y nota hija."""
        vault = tmp_path / "vault-Test"
        vault.mkdir()
        (vault / "00-INDICE.md").write_text("[[hija]]\n", encoding="utf-8")
        (vault / "hija.md").write_text(nota_extra, encoding="utf-8")
        return vault

    def test_enlace_en_span_de_codigo_no_es_roto(self, tmp_path) -> None:
        from context_map.presentation.vault.topologia import analizar_topologia

        vault = self._vault_minimo(
            tmp_path, "Ejemplos: `[[...]]` y `[[Categoría:X]]` dentro de código.\n"
        )
        res = analizar_topologia(str(vault))
        assert res.enlaces_rotos == []

    def test_enlace_en_bloque_de_codigo_no_es_roto(self, tmp_path) -> None:
        from context_map.presentation.vault.topologia import analizar_topologia

        vault = self._vault_minimo(
            tmp_path, "```\n[[destino-inexistente]]\n[[otro mas]]\n```\n"
        )
        res = analizar_topologia(str(vault))
        assert res.enlaces_rotos == []

    def test_enlace_real_fuera_de_codigo_si_se_reporta(self, tmp_path) -> None:
        from context_map.presentation.vault.topologia import analizar_topologia

        vault = self._vault_minimo(tmp_path, "Texto normal [[fantasma]].\n")
        res = analizar_topologia(str(vault))
        assert len(res.enlaces_rotos) == 1

    def test_texto_enlazable_conserva_el_resto(self) -> None:
        from context_map.presentation.vault.topologia import texto_enlazable

        limpio = texto_enlazable("antes `[[x]]` despues [[real]]")
        assert "[[real]]" in limpio
        assert "[[x]]" not in limpio


class TestBytesNulos:
    """Una nota con codificación mixta no puede tumbar el validador.

    Caso real: 6 notas de un vault ajeno contenían ``\x00`` sueltos (UTF-8 con
    restos de UTF-16). Un NUL entre dígitos se leía como marca de protección
    inventada y ``texto_enlazable`` lanzaba ``IndexError``; el doctor entero
    caía con él y el proyecto parecía «colgado».
    """

    def test_nul_entre_digitos_no_rompe(self) -> None:
        assert texto_enlazable("a\x001\x00b") == "a1b"

    def test_nul_con_digitos_largos_no_rompe(self) -> None:
        assert texto_enlazable("dato 12\x0034\x00 fin") == "dato 1234 fin"

    def test_nul_no_oculta_un_wikilink_real(self) -> None:
        contenido = "antes \x00 [[padre]] después \x002\x00"
        assert "[[padre]]" in texto_enlazable(contenido)

    def test_analizar_topologia_sobrevive_a_una_nota_corrupta(self, tmp_path) -> None:
        vault = tmp_path / "vault-Demo"
        (vault / "1.0-PROPOSITO").mkdir(parents=True)
        (vault / "00-INDICE.md").write_text(
            "---\ntags: [\"indice\"]\n---\n\n# Índice\n", encoding="utf-8"
        )
        (vault / "1.0-PROPOSITO" / "nota.md").write_bytes(
            "---\ntype: proposito\ntags: [\"proposito\"]\n---\n\n"
            "# Nota\n\n[[00-INDICE]]\n\nbasura \x0012\x00 aquí\n".encode("utf-8")
        )
        resultado = analizar_topologia(str(vault))
        assert resultado.archivos >= 2
        assert not any("IndexError" in e for e in resultado.errores)

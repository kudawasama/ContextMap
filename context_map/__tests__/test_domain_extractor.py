"""Pruebas unitarias para el módulo context_map.domain.normalization.domain_extractor."""

from context_map.domain.normalization.domain_extractor import DomainConceptExtractor


def test_domain_concept_extractor() -> None:
    """Verifica la extracción de términos de negocio dominantes."""
    extractor = DomainConceptExtractor()
    extractor.registrar_texto("FacturacionElectronicaService")
    extractor.registrar_texto("procesar_facturacion")
    extractor.registrar_texto("FacturacionDetalle")

    conceptos = extractor.obtener_conceptos_dominantes(top_n=2)
    assert len(conceptos) > 0
    assert "FACTURACION" in conceptos[0]

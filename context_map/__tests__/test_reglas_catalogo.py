"""El catálogo de reglas se parsea a nodos REGLA (R10, 2026-08-14).

Verifica que ContextMap reconoce el catálogo de reglas de negocio del
proyecto (convención Gobernanza: ``references/reglas/reglas_registro.yaml``):
lo parsea a nodos ``REGLA``, el scan genera eventos REGLA y el brief
incluye la sección "Reglas de Negocio".
"""

from __future__ import annotations

from context_map.domain.reglas.reglas import (
    nodos_regla_desde_catalogo,
    parsear_catalogo,
    resumen_catalogo,
)

YAML_EJEMPLO = """
version: 1.0
proyecto: "MiProyecto"
reglas:
  - id: REG-ING-001
    nombre: "DB activa"
    categoria: REG-ING
    categoria_nombre: "Ingesta DTE"
    prioridad: critica
    estado: implementada
    norma: "REG-ING-001_db_activa.md"
  - id: REG-ATR-001
    nombre: "Atribución CC"
    categoria: REG-ATR
    categoria_nombre: "Atribución CC"
    prioridad: critica
    estado: implementada
    norma: "REG-ATR-001_4_niveles.md"
"""


def _escribir_yaml(tmp_path, contenido: str = YAML_EJEMPLO) -> str:
    """Escribe un reglas_registro.yaml en tmp_path y devuelve su ruta.

    Args:
        tmp_path: Fixture de pytest.
        contenido (str): Contenido YAML.

    Returns:
        str: Ruta del archivo YAML.
    """
    ruta = tmp_path / "reglas_registro.yaml"
    ruta.write_text(contenido, encoding="utf-8")
    return str(ruta)


def test_parsea_yaml_de_reglas(tmp_path):
    """El parser lee el catálogo y devuelve las reglas con sus campos."""
    ruta = _escribir_yaml(tmp_path)
    reglas = parsear_catalogo(ruta)
    assert len(reglas) == 2
    assert reglas[0]["id"] == "REG-ING-001"
    assert reglas[0]["categoria_nombre"] == "Ingesta DTE"
    assert reglas[1]["id"] == "REG-ATR-001"


def test_sin_catalogo_devuelve_vacio(tmp_path):
    """Un archivo inexistente devuelve lista vacía (tolerante)."""
    assert parsear_catalogo(str(tmp_path / "no-existe.yaml")) == []


def test_nodos_regla_desde_catalogo(tmp_path):
    """Cada regla del catálogo se convierte en un nodo tipo REGLA."""
    ruta = _escribir_yaml(tmp_path)
    nodos = nodos_regla_desde_catalogo(ruta, "MiProyecto")
    assert len(nodos) == 2
    n = nodos[0]
    assert n.type == "REGLA"
    assert "REG-ING-001" in n.title
    assert "DB activa" in n.title
    assert "critica" in n.tags
    assert n.source == "reglas"


def test_nodos_regla_son_estables(tmp_path):
    """Mismo catálogo → mismos nodos (idempotente para el dedup)."""
    ruta = _escribir_yaml(tmp_path)
    nodos1 = nodos_regla_desde_catalogo(ruta, "MiProyecto")
    nodos2 = nodos_regla_desde_catalogo(ruta, "MiProyecto")
    assert [(n.id, n.title) for n in nodos1] == [(n.id, n.title) for n in nodos2]


def test_resumen_catalogo_por_categoria(tmp_path):
    """El resumen agrupa por categoría y cuenta el total."""
    ruta = _escribir_yaml(tmp_path)
    resumen = resumen_catalogo(ruta)
    assert resumen["total"] == 2
    assert resumen["categorias"]["REG-ING"] == 1
    assert resumen["categorias"]["REG-ATR"] == 1


def test_resumen_sin_catalogo(tmp_path):
    """Sin catálogo, el resumen es vacío y no rompe."""
    resumen = resumen_catalogo(str(tmp_path / "no-existe.yaml"))
    assert resumen["total"] == 0
    assert resumen["categorias"] == {}


def test_scan_genera_eventos_regla(tmp_path):
    """El scan detecta el catálogo en references/reglas/ y crea eventos REGLA."""
    reglas_dir = tmp_path / "references" / "reglas"
    reglas_dir.mkdir(parents=True)
    (reglas_dir / "reglas_registro.yaml").write_text(YAML_EJEMPLO, encoding="utf-8")

    from context_map.domain.scanning.scanner import escanear_y_generar_eventos

    eventos = escanear_y_generar_eventos(str(tmp_path))
    reglas = [e for e in eventos if e.type == "REGLA"]
    assert len(reglas) == 2
    assert reglas[0].text.startswith("REG-ING-001")


def test_scan_sin_catalogo_no_genera_reglas(tmp_path):
    """Sin catálogo, el scan no produce eventos REGLA."""
    from context_map.domain.scanning.scanner import escanear_y_generar_eventos

    eventos = escanear_y_generar_eventos(str(tmp_path))
    assert not any(e.type == "REGLA" for e in eventos)


def test_brief_incluye_seccion_reglas(tmp_path):
    """El brief incluye la sección Reglas de Negocio cuando hay catálogo."""
    reglas_dir = tmp_path / "references" / "reglas"
    reglas_dir.mkdir(parents=True)
    (reglas_dir / "reglas_registro.yaml").write_text(YAML_EJEMPLO, encoding="utf-8")

    from context_map.presentation.briefs.brief import _reglas_negocio

    seccion = _reglas_negocio(str(tmp_path))
    assert "Reglas de Negocio" in seccion
    assert "2 reglas" in seccion
    assert "REG-ING 1" in seccion


def test_brief_sin_catalogo_vacio(tmp_path):
    """Sin catálogo, la sección del brief es vacía."""
    from context_map.presentation.briefs.brief import _reglas_negocio

    assert _reglas_negocio(str(tmp_path)) == ""


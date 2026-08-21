"""Pruebas unitarias para el módulo context_map.domain.analyzers.cyclomatic."""

from context_map.domain.analyzers.cyclomatic import calcular_complejidad_ciclomatica


def test_calcular_complejidad_funcion_simple() -> None:
    """Verifica que una función lineal simple tenga complejidad 1."""
    codigo = """def funcion_simple():
    print("Hola mundo")
    return True
"""
    metricas = calcular_complejidad_ciclomatica(codigo)
    assert len(metricas) == 1
    assert metricas[0].nombre == "funcion_simple"
    assert metricas[0].complejidad == 1
    assert not metricas[0].es_alta_complejidad


def test_calcular_complejidad_funcion_compleja() -> None:
    """Verifica que condicionales y bucles incrementen la complejidad correctamente."""
    codigo = """def funcion_compleja(a, b, c):
    total = 0
    if a > 0 and b > 0:
        total += 1
    elif a < 0 or c > 0:
        total -= 1
    for i in range(10):
        if i % 2 == 0:
            total += i
        while total < 50:
            total += 5
    try:
        if total == 100:
            return 1
    except Exception:
        pass
    return total
"""
    metricas = calcular_complejidad_ciclomatica(codigo, umbral_alto=5)
    assert len(metricas) == 1
    assert metricas[0].nombre == "funcion_compleja"
    assert metricas[0].complejidad >= 8
    assert metricas[0].es_alta_complejidad

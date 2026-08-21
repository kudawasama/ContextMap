"""Pruebas unitarias para el módulo context_map.domain.scanning.cache."""

from pathlib import Path

from context_map.domain.scanning.cache import ScanCacheManager


def test_scan_cache_manager(tmp_path: Path) -> None:
    """Verifica el cálculo de hash SHA-256 y la detección de cambios en la caché."""
    test_file = tmp_path / "ejemplo.py"
    test_file.write_text("print('version 1')", encoding="utf-8")

    manager = ScanCacheManager(tmp_path)

    # 1. Archivo nuevo debe detectarse como modificado
    assert manager.esta_modificado(test_file)

    # 2. Guardar entrada y verificar que ya no se marque como modificado
    manager.actualizar_entrada(test_file, {"lineas": 1})
    manager.guardar_cache()

    manager_nuevo = ScanCacheManager(tmp_path)
    assert not manager_nuevo.esta_modificado(test_file)
    meta = manager_nuevo.obtener_metadatos(test_file)
    assert meta is not None
    assert meta.get("lineas") == 1

    # 3. Modificar el archivo y verificar que la caché detecte la modificación
    test_file.write_text("print('version 2 modificada')", encoding="utf-8")
    assert manager_nuevo.esta_modificado(test_file)

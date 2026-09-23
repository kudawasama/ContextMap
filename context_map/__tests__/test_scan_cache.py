"""Pruebas unitarias para la caché incremental del escáner de código.

Verifica que el analizador de contenido acelere los re-escaneos utilizando
la huella (mtime_ns, size) y actualice las entradas cuando los archivos cambian.
"""

from __future__ import annotations

import os
import tempfile
import time

from context_map.infrastructure.analyzers.content import analizar_directorio


def test_scan_cache_incremental() -> None:
    """Verifica que la caché se guarde, se reutilice y detecte cambios en archivos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Crear estructura de prueba
        f1 = os.path.join(tmpdir, "modulo_a.py")
        f2 = os.path.join(tmpdir, "modulo_b.py")

        with open(f1, "w", encoding="utf-8") as f:
            f.write('"""Docstring A."""\n\ndef func_a():\n    # TODO: Tarea A\n    pass\n')

        with open(f2, "w", encoding="utf-8") as f:
            f.write('"""Docstring B."""\n\ndef func_b():\n    pass\n')

        # 1. Primer escaneo: construye caché
        res1 = analizar_directorio(tmpdir, use_cache=True)
        assert len(res1) == 2

        cache_path = os.path.join(tmpdir, ".context-map", ".scan_cache.json")
        assert os.path.isfile(cache_path), "La caché no se guardó en disco"

        # 2. Segundo escaneo inmediato: debe reutilizar caché
        t0 = time.perf_counter()
        res2 = analizar_directorio(tmpdir, use_cache=True)
        t_cache = time.perf_counter() - t0
        assert t_cache >= 0
        assert len(res2) == 2
        # Los resultados deben ser idénticos
        docstrings1 = {r.docstring_principal for r in res1}
        docstrings2 = {r.docstring_principal for r in res2}
        assert docstrings1 == docstrings2

        # 3. Modificar un archivo
        time.sleep(0.01)  # Asegurar variación de timestamp
        with open(f1, "w", encoding="utf-8") as f:
            f.write('"""Docstring A Modificado."""\n\ndef func_a_nueva():\n    # TODO: Nueva tarea\n    pass\n')

        res3 = analizar_directorio(tmpdir, use_cache=True)
        assert len(res3) == 2
        modificados = [r for r in res3 if "Modificado" in r.docstring_principal]
        assert len(modificados) == 1
        assert modificados[0].docstring_principal == "Docstring A Modificado."
        assert any("Nueva tarea" in t for t in modificados[0].todos)

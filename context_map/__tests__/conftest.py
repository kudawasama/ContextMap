"""Configuración compartida de pytest.

Aísla la base de datos personal de ContextMap durante los tests: cualquier
``do_sync`` (build/scan/refresh) que se ejecute en la suite consolida en una
BD temporal, jamás en la BD personal real del usuario (F: / ~/.context-map).
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Generator

import pytest


@pytest.fixture(autouse=True)
def _aislar_bd_personal(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Redirige CTXMAP_PERSONAL_DB a una ruta temporal por test.

    Args:
        monkeypatch: Fixture de pytest para parchear variables de entorno.

    Yields:
        None: cede el control al test con la variable ya parcheada.
    """
    fd, ruta_tmp = tempfile.mkstemp(prefix="ctxmap_test_personal_", suffix=".db")
    os.close(fd)
    monkeypatch.setenv("CTXMAP_PERSONAL_DB", ruta_tmp)
    yield
    with contextlib.suppress(OSError):
        os.remove(ruta_tmp)

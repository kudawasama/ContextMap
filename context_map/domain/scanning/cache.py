"""Módulo de caché incremental con Hash SHA-256 para ContextMap.

Guarda los hashes SHA-256 de los archivos analizados en `.context-map/cache.json`
para omitir el re-procesamiento AST de archivos sin cambios entre ejecuciones.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ScanCacheManager:
    """Gestor de caché en disco para escaneos incrementales por Hash SHA-256."""

    def __init__(self, project_dir: Path) -> None:
        """Inicializa el gestor de caché para un directorio de proyecto.

        Args:
            project_dir: Ruta raíz del proyecto.
        """
        self.project_dir = Path(project_dir).resolve()
        self.cache_dir = self.project_dir / ".context-map"
        self.cache_file = self.cache_dir / "cache.json"
        self._cache_data: Dict[str, Dict[str, Any]] = {}
        self._cargar_cache()

    def _cargar_cache(self) -> None:
        """Carga los datos de caché desde `.context-map/cache.json` si existe."""
        if self.cache_file.is_file():
            try:
                contenido = self.cache_file.read_text(encoding="utf-8")
                self._cache_data = json.loads(contenido)
            except Exception:
                self._cache_data = {}
        else:
            self._cache_data = {}

    def guardar_cache(self) -> None:
        """Persiste los datos de caché actualizados en disco."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._cache_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def calcular_hash_archivo(file_path: Path) -> str:
        """Calcula la suma de verificación SHA-256 de un archivo.

        Args:
            file_path: Ruta del archivo a evaluar.

        Returns:
            String con el hash SHA-256 en hexadecimal.
        """
        if not file_path.is_file():
            return ""
        try:
            hasher = hashlib.sha256()
            hasher.update(file_path.read_bytes())
            return hasher.hexdigest()
        except Exception:
            return ""

    def esta_modificado(self, file_path: Path) -> bool:
        """Verifica si un archivo ha sido modificado comparando su hash SHA-256 actual con la caché.

        Args:
            file_path: Ruta del archivo.

        Returns:
            True si el archivo fue modificado o no existe en la caché; False en caso contrario.
        """
        rel_path = str(file_path.resolve().relative_to(self.project_dir))
        hash_actual = self.calcular_hash_archivo(file_path)

        if not hash_actual:
            return True

        cached_entry = self._cache_data.get(rel_path)
        if not cached_entry:
            return True

        return cached_entry.get("sha256") != hash_actual

    def actualizar_entrada(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Actualiza la entrada de un archivo en la caché con su hash actual y metadatos opcionales.

        Args:
            file_path: Ruta del archivo.
            metadata: Diccionario opcional de datos del escaneo.
        """
        try:
            rel_path = str(file_path.resolve().relative_to(self.project_dir))
            hash_actual = self.calcular_hash_archivo(file_path)
            entry: Dict[str, Any] = {"sha256": hash_actual}
            if metadata:
                entry.update(metadata)
            self._cache_data[rel_path] = entry
        except Exception:
            pass

    def obtener_metadatos(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Recupera los metadatos cacheados de un archivo si no ha sido modificado.

        Args:
            file_path: Ruta del archivo.

        Returns:
            Diccionario de metadatos o None.
        """
        if self.esta_modificado(file_path):
            return None
        rel_path = str(file_path.resolve().relative_to(self.project_dir))
        return self._cache_data.get(rel_path)

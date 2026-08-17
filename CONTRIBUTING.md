# 🤝 Guía de Contribución a ContextMap

¡Gracias por tu interés en contribuir a **ContextMap**! Valoramos y agradecemos todo tipo de contribuciones, desde reportes de errores y mejoras en la documentación hasta nuevas funcionalidades y refactorizaciones.

---

## 📐 Principios de Desarrollo del Proyecto

Cualquier contribución al repositorio debe seguir sin excepción las reglas estipuladas en [`AGENTS.md`](AGENTS.md):

1. **Idioma**: Toda la documentación, comentarios en código, docstrings y mensajes de commit deben estar redactados en **Español Técnico Profesional**.
2. **Estilo de Docstrings**: Uso estricto del formato **Google Style** (PEP 257) en todas las funciones, clases y módulos.
3. **Type Hinting**: Sugerencias de tipo estrictas en Python (`list[str]`, `Optional[Dict]`, `Tuple[int, str]`).
4. **Clean Architecture**: Adhesión al Principio de Responsabilidad Única (SRP). Desacoplamiento claro entre `core/`, `domain/`, `application/`, `infrastructure/` y `presentation/`.
5. **Topología en Árbol de Obsidian**: Ninguna nota o script generado puede romper la topología en árbol estricto de la bóveda (1 enlace padre `⬅` por nota, 0 nodos fantasma, 0 enlaces rotos).

---

## 🛠️ Configuración del Entorno de Desarrollo

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/kudawasama/ContextMap.git
   cd ContextMap
   ```

2. **Crear e instalar en modo editable:**
   ```bash
   # Con uv (Recomendado):
   uv venv
   source .venv/bin/activate  # En Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"

   # O con pip standard:
   pip install -e .
   pip install pytest ruff
   ```

3. **Ejecutar la batería de pruebas:**
   ```bash
   python -m pytest
   ```

4. **Verificar readiness y frescura del contexto:**
   ```bash
   python -m context_map.cli refresh .
   python -m context_map.cli check .
   ```

---

## 🚀 Protocolo para Enviar un Pull Request (PR)

1. Crea una rama descriptiva para tu cambio (`feat/mi-nueva-funcion`, `fix/correccion-bug`).
2. Asegúrate de que **todos los 160+ tests unitarios pasen al 100% en verde**.
3. Re-genera el vault y el brief usando el código local:
   ```bash
   python -m context_map.cli refresh .
   ```
4. Envía tu Pull Request a la rama `master` utilizando mensajes de commit formateados con **Conventional Commits** en español (ej. `feat: ...`, `fix: ...`, `docs: ...`).

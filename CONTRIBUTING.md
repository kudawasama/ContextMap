# 🤝 Contributing to ContextMap

Thank you for your interest in contributing to **ContextMap**! We welcome all contributions, from bug reports and documentation improvements to new features and refactoring.

---

## 🌐 Languages / Idiomas
- [ 🇬🇧 **English (Current)** ](#-development-principles)
- [ 🇪🇸 **Español** ](#-guía-de-contribución-en-español)

---

## 📐 Development Principles

All contributions to this repository must follow the strict rules defined in [`AGENTS.md`](AGENTS.md):

1. **Language & Docstrings**: Code documentation, inline comments, docstrings (Google Style / PEP 257), and commit messages must be technical and descriptive.
2. **Strict Typing**: Explicit Python type hinting (`list[str]`, `Optional[Dict]`, `Tuple[int, str]`).
3. **Clean Architecture**: Adherence to the Single Responsibility Principle (SRP). Clear decoupling between `core/`, `domain/`, `application/`, `infrastructure/`, and `presentation/`.
4. **Obsidian Tree Topology**: No generated note or script may break the strict tree graph topology of the vault (1 parent `⬅` link per note, zero ghost nodes, zero broken links).

---

## 🛠️ Development Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kudawasama/ContextMap.git
   cd ContextMap
   ```

2. **Create environment and install in editable mode:**
   ```bash
   # With uv (Recommended):
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   uv pip install -e ".[dev]"

   # Or standard pip:
   pip install -e .
   pip install pytest ruff
   ```

3. **Run the test suite:**
   ```bash
   python -m pytest
   ```

4. **Verify readiness and context freshness:**
   ```bash
   python -m context_map.cli refresh .
   python -m context_map.cli check .
   ```

---

## 🚀 Submitting a Pull Request (PR)

1. Create a descriptive feature branch (`feat/my-new-feature`, `fix/fix-bug`).
2. Ensure **all 160+ unit tests pass 100% green**.
3. Re-generate the vault and brief using local code:
   ```bash
   python -m context_map.cli refresh .
   ```
4. Submit your Pull Request to the `master` branch using **Conventional Commits** (e.g., `feat: ...`, `fix: ...`, `docs: ...`).

---
---

## 🇪🇸 Guía de Contribución en Español

### 📐 Principios de Desarrollo del Proyecto

Cualquier contribución al repositorio debe seguir sin excepción las reglas estipuladas en [`AGENTS.md`](AGENTS.md):

1. **Idioma**: Toda la documentación, comentarios en código, docstrings y mensajes de commit deben estar redactados en **Español Técnico Profesional**.
2. **Estilo de Docstrings**: Uso estricto del formato **Google Style** (PEP 257) en todas las funciones, clases y módulos.
3. **Type Hinting**: Sugerencias de tipo estrictas en Python (`list[str]`, `Optional[Dict]`, `Tuple[int, str]`).
4. **Clean Architecture**: Adhesión al Principio de Responsabilidad Única (SRP). Desacoplamiento claro entre `core/`, `domain/`, `application/`, `infrastructure/` y `presentation/`.
5. **Topología en Árbol de Obsidian**: Ninguna nota o script generado puede romper la topología en árbol estricto de la bóveda (1 enlace padre `⬅` por nota, 0 nodos fantasma, 0 enlaces rotos).

---

### 🛠️ Configuración del Entorno de Desarrollo

```bash
git clone https://github.com/kudawasama/ContextMap.git
cd ContextMap
pip install -e .
python -m pytest
```

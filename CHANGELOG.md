# Changelog — Context Map

Todas las notas de versión y cambios destacables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.1.0] - 2026-07-30

### 🚀 Añadido
- **Comando Orquestador All-in-One (`ctxmap auto [target]`)**: Orquestación automática en 1 solo paso (`scan` + `import-git` + `build --clean --brief`).
- **Jerarquía de Detección de Nombre de Repositorio GitHub (1ª Instancia)**: Resolución automática del nombre del Vault basado en el remoto de GitHub.
- **Analizador de Complejidad Ciclomática McCabe**: Ingesta sintáctica AST de puntos de decisión en funciones y módulos.
- **Git Pre-Commit Hook (`ctxmap hook install`)**: Sincronización silenciosa en segundo plano antes de cada commit.

### 🧹 Simplificado y Corregido
- **Unificación de Importadores**: Consolidación de `import-antigravity2` dentro de `import-antigravity`.
- **Depreciación del comando `watch`**: Reemplazado a favor del Pre-Commit Hook desatendido.
- **Consolidación de Vault Único**: Eliminación de duplicados `.context-map/vault` para generar un único directorio de Vault por proyecto.
- **Tolerancia Multi-Disco en Windows**: Solución al fallo `ValueError: relpath` entre distintas unidades de disco (ej. `C:` y `G:`).

---

## [1.0.0] - 2026-07-29

### 🚀 Añadido
- **Gobernanza Automática para Agentes (`AGENTS.md`)**: Generación automática de normas arquitectónicas en proyectos escaneados.
- **Vista de Grafo Obsidian en 3 Niveles**: Estructura en estrella limpia (`00-INDICE.md` -> Secciones `X.0` -> Sub-secciones `X.Y`).
- **Clasificación Semántica de Estado**: Distinción entre código implementado (`completado`), roadmap (`activo`) y tareas/TODOs (`pendiente`).
- **Filtrado NUL (`\x00`)**: Sanitización estricta de nombres de archivo contra caracteres de control en Windows.
- **Sincronización Multi-Vault**: Actualización en tiempo real de todas las carpetas `vault*` asociadas.
- **Integración con Antigravity IDE**: Importador automático de sesiones de chat Gemini/Antigravity.

### 🔧 Corregido
- Sanitización de rutas con espacios y soporte nativo para rutas de red/Google Drive.
- Prevención de ciclos redundantes en enlaces wiki de Obsidian (`[[nota]]`).

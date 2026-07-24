# Plan de Implementación — Context Map Generator

## Versión actual: v0.2.0

### Funcionalidades existentes
- CLI con comandos: init, build, sync, watch
- Vault Obsidian con wiki-links y tags YAML
- Sync incremental (sin reescribir estado)
- Parser heurístico de eventos
- Snapshot con nombres descriptivos

---

## Fase 1: Escaneo Automático del Proyecto
**Prioridad: Alta | Estimación: 2-3 días**

### Objetivo
Que ctxmap pueda analizar un proyecto y generar contexto automáticamente sin intervención manual.

### Tareas

#### 1.1 Analizador de estructura
- [ ] Leer árbol de archivos del proyecto
- [ ] Clasificar archivos por tipo (Python, JS, config, docs, etc.)
- [ ] Detectar entrypoints (main.py, app.py, index.js)
- [ ] Identificar archivos importantes (README, CHANGELOG, LICENSE)

#### 1.2 Analizador de contenido
- [ ] Leer archivos Python y extraer docstrings
- [ ] Detectar imports y dependencias
- [ ] Identificar clases y funciones principales
- [ ] Extraer comentarios TODO/FIXME/HACK

#### 1.3 Generador de contexto técnico
- [ ] Crear nodo BASE con info del proyecto (nombre, versión, deps)
- [ ] Generar IDEA por cada módulo importante
- [ ] Detectar RIESGOS (archivos grandes, complejidad)
- [ ] Crear HITO con estructura actual

#### 1.4 Integración con sync
- [ ] El escaneo se ejecuta como parte de `ctxmap sync`
- [ ] No duplicar nodos ya existentes
- [ ] Actualizar nodos si cambian archivos clave

### Archivos a crear/modify
```
context_map/
├── scanner.py          # Nuevo: analizador de proyecto
├── analyzers/
│   ├── __init__.py
│   ├── structure.py    # Nuevo: análisis de archivos
│   ├── content.py      # Nuevo: análisis de contenido
│   └── python.py       # Nuevo: parser Python
└── cli.py              # Modificar: agregar flag --scan
```

---

## Fase 2: Integración con Sesiones de Hermes
**Prioridad: Alta | Estimación: 2-3 días**

### Objetivo
Que ctxmap pueda leer el historial de conversaciones de Hermes y extraer contexto automáticamente.

### Tareas

#### 2.1 Lector de sesiones
- [ ] Acceder a la base de datos de sesiones de Hermes
- [ ] Leer mensajes de usuario y asistente
- [ ] Filtrar por sesión o rango de fechas
- [ ] Extraer tool calls y resultados

#### 2.2 Clasificador de conversaciones
- [ ] Detectar decisiones tomadas
- [ ] Identificar ideas mencionadas
- [ ] Extraer riesgos o problemas
- [ ] Capturar contexto emocional (entusiasmo, frustración)

#### 2.3 Exportador a eventos
- [ ] Convertir mensajes a formato Event
- [ ] Clasificar automáticamente por tipo
- [ ] Evitar duplicados con hash
- [ ] Generar events.jsonl desde sesiones

#### 2.4 Comando `ctxmap import-sessions`
- [ ] Nuevo comando para importar sesiones
- [ ] Filtros: --session-id, --since, --until
- [ ] Preview antes de importar
- [ ] Reporte de lo importado

### Archivos a crear/modify
```
context_map/
├── integrations/
│   ├── __init__.py
│   ├── hermes.py       # Nuevo: lector de sesiones
│   └── classifier.py   # Nuevo: clasificador de chat
└── cli.py              # Modificar: agregar import-sessions
```

---

## Fase 3: Lector de Historial Git
**Prioridad: Media | Estimación: 1-2 días**

### Objetivo
Extraer contexto del historial de commits y cambios del proyecto.

### Tareas

#### 3.1 Lector de commits
- [ ] Leer log de git (últimos N commits)
- [ ] Extraer mensaje, autor, fecha
- [ ] Detectar archivos modificados
- [ ] Identificar patrones (feat, fix, chore)

#### 3.2 Generador de nodos desde git
- [ ] Crear HITO por cada release tag
- [ ] Crear CAMBIO por commits significativos
- [ ] Crear CORRECCION por fixes
- [ ] Conectar con nodos existentes

#### 3.3 Detección de milestones
- [ ] Detectar tags de versión
- [ ] Identificar ramas principales
- [ ] Crear resumen de cambios por versión

#### 3.4 Comando `ctxmap import-git`
- [ ] Nuevo comando para importar de git
- [ ] Filtros: --since, --author, --grep
- [ ] Límite de commits a procesar

### Archivos a crear/modify
```
context_map/
├── integrations/
│   └── git.py          # Nuevo: lector de git
└── cli.py              # Modificar: agregar import-git
```

---

## Fase 4: Diagramas Mermaid
**Prioridad: Media | Estimación: 1 día**

### Objetivo
Generar diagramas de dependencias y relaciones en formato Mermaid.

### Tareas

#### 4.1 Generador de graphviz
- [ ] Convertir nodos y aristas a Mermaid
- [ ] Estilos por tipo de nodo
- [ ] Colores diferentes por categoría

#### 4.2 Integración con vault
- [ ] Agregar archivo `00-GRAPH.md` con diagrama
- [ ] Incluir en el MOC principal
- [ ] Soporte para diferentes vistas (por tipo, por conexiones)

#### 4.3 Opciones de renderizado
- [ ] Flag --mermaid para incluir en build
- [ ] Flag --mermaid-only para solo diagrama
- [ ] Formato PNG opcional (con mermaid-cli)

### Archivos a crear/modify
```
context_map/
├── writer.py           # Modificar: agregar mermaid
└── cli.py              # Modificar: agregar flags
```

---

## Fase 5: Score de Readiness
**Prioridad: Baja | Estimación: 1 día**

### Objetivo
Calcular qué tan "listo" está el proyecto para que un agente trabaje en él.

### Tareas

#### 5.1 Analizador de señales
- [ ] Verificar si existe README
- [ ] Verificar si hay tests
- [ ] Verificar si hay CI/CD
- [ ] Verificar si hay documentación
- [ ] Verificar si hay instrucciones para agentes

#### 5.2 Calculadora de score
- [ ] Asignar peso a cada señal
- [ ] Calcular score total (0-100)
- [ ] Generar veredicto (ready / not-ready / partial)

#### 5.3 Reporte de gaps
- [ ] Identificar qué falta
- [ ] Sugerir acciones para mejorar
- [ ] Priorizar por impacto

#### 5.4 Comando `ctxmap check`
- [ ] Nuevo comando para verificar readiness
- [ ] Salida: score + gaps + sugerencias
- [ ] Formato JSON para CI/CD

### Archivos a crear/modify
```
context_map/
├── checker.py          # Nuevo: analizador de readiness
└── cli.py              # Modificar: agregar check
```

---

## Fase 6: Exportador de Chats Externos
**Prioridad: Baja | Estimación: 2 días**

### Objetivo
Importar conversaciones de Telegram, Discord, Slack, etc.

### Tareas

#### 6.1 Formateadores por plataforma
- [ ] Telegram: parser de exportación HTML/JSON
- [ ] Discord: parser de exportación JSON
- [ ] Slack: parser de exportación JSON
- [ ] WhatsApp: parser de exportación TXT

#### 6.2 Clasificador contextual
- [ ] Detectar usuario vs bot
- [ ] Identificar decisiones vs discusión
- [ ] Extraer código compartido
- [ ] Capturar acuerdos y conclusiones

#### 6.3 Comando `ctxmap import-chat`
- [ ] Nuevo comando para importar chats
- [ ] Auto-detectar formato
- [ ] Preview antes de importar
- [ ] Stats de lo importado

### Archivos a crear/modify
```
context_map/
├── integrations/
│   ├── telegram.py     # Nuevo
│   ├── discord.py      # Nuevo
│   ├── slack.py        # Nuevo
│   └── whatsapp.py     # Nuevo
└── cli.py              # Modificar: agregar import-chat
```

---

## Fase 7: Resúmenes Semanales
**Prioridad: Baja | Estimación: 1 día**

### Objetivo
Generar resúmenes automáticos de actividad semanal.

### Tareas

#### 7.1 Recolector de actividad
- [ ] Contar eventos nuevos por semana
- [ ] Identificar cambios principales
- [ ] Resumir decisiones tomadas

#### 7.2 Generador de reporte
- [ ] Markdown con stats de la semana
- [ ] Top 5 eventos más importantes
- [ ] Próximos pasos sugeridos

#### 7.3 Comando `ctxmap weekly`
- [ ] Nuevo comando para generar resumen
- [ ] Filtros: --week, --month
- [ ] Salida a archivo o stdout

### Archivos a crear/modify
```
context_map/
├── reporter.py         # Nuevo: generador de reportes
└── cli.py              # Modificar: agregar weekly
```

---

## Fase 8: Dashboard Web (Opcional)
**Prioridad: Opcional | Estimación: 3-4 días**

### Objetivo
Interfaz web para visualizar y gestionar el mapa.

### Tareas

#### 8.1 Servidor local
- [ ] FastAPI ligero
- [ ] Ruta para ver vault
- [ ] Ruta para agregar eventos
- [ ] Ruta para sync

#### 8.2 Frontend
- [ ] HTML/CSS/JS vanilla
- [ ] Graph view con D3.js o vis.js
- [ ] Lista de notas
- [ ] Formulario para agregar eventos

#### 8.3 Comando `ctxmap serve`
- [ ] Nuevo comando para iniciar servidor
- [ ] Puerto configurable
- [ ] Auto-abrir navegador

### Archivos a crear
```
context_map/
├── web/
│   ├── __init__.py
│   ├── server.py       # Nuevo: FastAPI
│   ├── static/
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── templates/
└── cli.py              # Modificar: agregar serve
```

---

## Orden de Implementación

```
Fase 1 (Escaneo)          → 2-3 días
    ↓
Fase 2 (Hermes)           → 2-3 días
    ↓
Fase 3 (Git)              → 1-2 días
    ↓
Fase 4 (Mermaid)          → 1 día
    ↓
Fase 5 (Readiness)        → 1 día
    ↓
Fase 6 (Chats externos)   → 2 días
    ↓
Fase 7 (Resúmenes)        → 1 día
    ↓
Fase 8 (Dashboard)        → 3-4 días (opcional)
```

**Total estimado: 13-17 días** (sin Fase 8)

---

## Criterios de Aceptación

### Para cada fase:
1. [ ] Código con type hints
2. [ ] Docstrings en español
3. [ ] Tests básicos
4. [ ] Documentación actualizada
5. [ ] Commits atómicos

### Para la release v1.0:
- [ ] Fases 1-5 completadas
- [ ] Tests cubriendo funcionalidad principal
- [ ] README actualizado con todas las features
- [ ] Ejemplos de uso para cada comando
- [ ] CHANGELOG completo

---

## Notas

- Cada fase es independiente y se puede merge por separado
- Las fases 1-3 son las más importantes para MVP
- Las fases 6-8 son nice-to-have
- El dashboard (Fase 8) es opcional y puede hacerse después

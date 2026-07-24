# Plan de Implementación — Context Map Generator

## Versión actual: v0.3.0

### Funcionalidades completadas

- ✅ CLI con comandos: init, build, sync, watch
- ✅ Vault Obsidian con wiki-links y tags YAML
- ✅ Sync incremental (sin reescribir estado)
- ✅ Parser heurístico de eventos
- ✅ Snapshot con nombres descriptivos
- ✅ Escaneo automático de proyecto (Fase 1)
- ✅ Integración con git history (Fase 3)
- ✅ Diagramas Mermaid (Fase 4)
- ✅ Score de readiness (Fase 5)

### Fases completadas

#### Fase 1: Escaneo Automático ✅
- scanner.py: escáner principal
- analyzers/structure.py: análisis de archivos
- analyzers/content.py: análisis de contenido Python
- Comando: `ctxmap scan .`

#### Fase 3: Integración con Git ✅
- integrations/git.py: lector de historial git
- Comando: `ctxmap import-git .`
- Clasificación automática de commits

#### Fase 4: Diagramas Mermaid ✅
- writer.py: función render_mermaid()
- Comando: `ctxmap build --mermaid`
- Genera 00-GRAPH.md

#### Fase 5: Score de Readiness ✅
- checker.py: analizador de readiness
- Comando: `ctxmap check .`
- Score 0-100 con gaps y sugerencias

---

## Fases Pendientes

### Fase 2: Integración con Sesiones de Hermes
**Prioridad: Alta | Estimación: 2-3 días**

#### Objetivo
Que ctxmap pueda leer el historial de conversaciones de Hermes y extraer contexto automáticamente.

#### Tareas

##### 2.1 Lector de sesiones
- [ ] Acceder a la base de datos de sesiones de Hermes
- [ ] Leer mensajes de usuario y asistente
- [ ] Filtrar por sesión o rango de fechas
- [ ] Extraer tool calls y resultados

##### 2.2 Clasificador de conversaciones
- [ ] Detectar decisiones tomadas
- [ ] Identificar ideas mencionadas
- [ ] Extraer riesgos o problemas
- [ ] Capturar contexto emocional (entusiasmo, frustración)

##### 2.3 Exportador a eventos
- [ ] Convertir mensajes a formato Event
- [ ] Clasificar automáticamente por tipo
- [ ] Evitar duplicados con hash
- [ ] Generar events.jsonl desde sesiones

##### 2.4 Comando `ctxmap import-sessions`
- [ ] Nuevo comando para importar sesiones
- [ ] Filtros: --session-id, --since, --until
- [ ] Preview antes de importar
- [ ] Reporte de lo importado

#### Archivos a crear/modify
```
context_map/
├── integrations/
│   ├── hermes.py       # Nuevo: lector de sesiones
│   └── classifier.py   # Nuevo: clasificador de chat
└── cli.py              # Modificar: agregar import-sessions
```

---

### Fase 6: Exportador de Chats Externos
**Prioridad: Baja | Estimación: 2 días**

#### Objetivo
Importar conversaciones de Telegram, Discord, Slack, etc.

#### Tareas

##### 6.1 Formateadores por plataforma
- [ ] Telegram: parser de exportación HTML/JSON
- [ ] Discord: parser de exportación JSON
- [ ] Slack: parser de exportación JSON
- [ ] WhatsApp: parser de exportación TXT

##### 6.2 Clasificador contextual
- [ ] Detectar usuario vs bot
- [ ] Identificar decisiones vs discusión
- [ ] Extraer código compartido
- [ ] Capturar acuerdos y conclusiones

##### 6.3 Comando `ctxmap import-chat`
- [ ] Nuevo comando para importar chats
- [ ] Auto-detectar formato
- [ ] Preview antes de importar
- [ ] Stats de lo importado

#### Archivos a crear/modify
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

### Fase 7: Resúmenes Semanales
**Prioridad: Baja | Estimación: 1 día**

#### Objetivo
Generar resúmenes automáticos de actividad semanal.

#### Tareas

##### 7.1 Recolector de actividad
- [ ] Contar eventos nuevos por semana
- [ ] Identificar cambios principales
- [ ] Resumir decisiones tomadas

##### 7.2 Generador de reporte
- [ ] Markdown con stats de la semana
- [ ] Top 5 eventos más importantes
- [ ] Próximos pasos sugeridos

##### 7.3 Comando `ctxmap weekly`
- [ ] Nuevo comando para generar resumen
- [ ] Filtros: --week, --month
- [ ] Salida a archivo o stdout

#### Archivos a crear/modify
```
context_map/
├── reporter.py         # Nuevo: generador de reportes
└── cli.py              # Modificar: agregar weekly
```

---

### Fase 8: Dashboard Web (Opcional)
**Prioridad: Opcional | Estimación: 3-4 días**

#### Objetivo
Interfaz web para visualizar y gestionar el mapa.

#### Tareas

##### 8.1 Servidor local
- [ ] FastAPI ligero
- [ ] Ruta para ver vault
- [ ] Ruta para agregar eventos
- [ ] Ruta para sync

##### 8.2 Frontend
- [ ] HTML/CSS/JS vanilla
- [ ] Graph view con D3.js o vis.js
- [ ] Lista de notas
- [ ] Formulario para agregar eventos

##### 8.3 Comando `ctxmap serve`
- [ ] Nuevo comando para iniciar servidor
- [ ] Puerto configurable
- [ ] Auto-abrir navegador

#### Archivos a crear
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
Fase 1 (Escaneo)          ✅ Completada
Fase 3 (Git)              ✅ Completada
Fase 4 (Mermaid)          ✅ Completada
Fase 5 (Readiness)        ✅ Completada
    ↓
Fase 2 (Hermes)           → 2-3 días
    ↓
Fase 6 (Chats externos)   → 2 días
    ↓
Fase 7 (Resúmenes)        → 1 día
    ↓
Fase 8 (Dashboard)        → 3-4 días (opcional)
```

**Completado: 4/8 fases**
**Pendiente: 4 fases (2, 6, 7, 8)**
**Estimación restante: 8-10 días**

---

## Criterios de Aceptación

### Para cada fase:
1. [ ] Código con type hints
2. [ ] Docstrings en español
3. [ ] Tests básicos
4. [ ] Documentación actualizada
5. [ ] Commits atómicos

### Para la release v1.0:
- [ ] Fases 1-5 completadas ✅
- [ ] Fase 2 (Hermes) completada
- [ ] Tests cubriendo funcionalidad principal
- [ ] README actualizado con todas las features
- [ ] Ejemplos de uso para cada comando
- [ ] CHANGELOG completo

#!/usr/bin/env bash
# ============================================================
# install.sh — Instalador de Context Map Generator
# ============================================================
# Ejecutar desde la carpeta del proyecto objetivo:
#   bash install.sh
#
# Que hace:
#   1. Crea .context-map/ con toda la estructura
#   2. Instala ctxmap como comando global
#   3. Deja el sistema listo para usar
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONTEXT_DIR=".context-map"

echo "=== Context Map Generator ==="
echo "Instalando en: $(pwd)"
echo ""

# --- Paso 1: Crear estructura de carpetas ---
echo "[1/3] Creando estructura..."
mkdir -p "$CONTEXT_DIR/state"
mkdir -p "$CONTEXT_DIR/maps/HISTORY"
mkdir -p "$CONTEXT_DIR/vault"
mkdir -p "$CONTEXT_DIR/chats"
mkdir -p "$CONTEXT_DIR/raw"
echo "  OK: .context-map/"

# --- Paso 2: Inicializar archivos ---
echo "[2/3] Inicializando archivos..."
if [ ! -f "$CONTEXT_DIR/state/graph.jsonl" ]; then
    echo "" > "$CONTEXT_DIR/state/graph.jsonl"
fi
if [ ! -f "$CONTEXT_DIR/state/edges.jsonl" ]; then
    echo "" > "$CONTEXT_DIR/state/edges.jsonl"
fi
if [ ! -f "$CONTEXT_DIR/state/processed_events.txt" ]; then
    echo "" > "$CONTEXT_DIR/state/processed_events.txt"
fi
echo "  OK: Archivos de estado"

# --- Paso 3: Instalar paquete ---
echo "[3/3] Instalando ctxmap..."
if pip install -e "$SCRIPT_DIR" --quiet 2>/dev/null; then
    echo "  OK: ctxmap instalado via pip"
elif pip3 install -e "$SCRIPT_DIR" --quiet 2>/dev/null; then
    echo "  OK: ctxmap instalado via pip3"
else
    echo "  WARN: No se pudo instalar globalmente"
    echo "  Usa: python -m context_map.cli --help"
fi

# --- Resumen ---
echo ""
echo "=== INSTALACION COMPLETA ==="
echo ""
echo "Uso:"
echo "  ctxmap init                    # Crear estructura"
echo "  ctxmap build --project \"Nombre\" # Generar vault"
echo "  ctxmap sync --project \"Nombre\" # Sync incremental"
echo ""
echo "Para agregar eventos, edita:"
echo "  .context-map/raw/events.jsonl"
echo ""

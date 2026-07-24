# ============================================================
# install.ps1 — Instalador de Context Map Generator (Windows)
# ============================================================
# Ejecutar desde la carpeta del proyecto objetivo:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# ============================================================

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ContextDir = ".context-map"

Write-Host "=== Context Map Generator ===" -ForegroundColor Cyan
Write-Host "Instalando en: $(Get-Location)"
Write-Host ""

# --- Paso 1: Crear estructura ---
Write-Host "[1/3] Creando estructura..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "$ContextDir\state" | Out-Null
New-Item -ItemType Directory -Force -Path "$ContextDir\maps\HISTORY" | Out-Null
New-Item -ItemType Directory -Force -Path "$ContextDir\vault" | Out-Null
New-Item -ItemType Directory -Force -Path "$ContextDir\chats" | Out-Null
New-Item -ItemType Directory -Force -Path "$ContextDir\raw" | Out-Null
Write-Host "  OK: .context-map\" -ForegroundColor Green

# --- Paso 2: Inicializar archivos ---
Write-Host "[2/3] Inicializando archivos..." -ForegroundColor Yellow
$graphFile = "$ContextDir\state\graph.jsonl"
$edgesFile = "$ContextDir\state\edges.jsonl"
$processedFile = "$ContextDir\state\processed_events.txt"

if (-not (Test-Path $graphFile)) { "" | Set-Content $graphFile }
if (-not (Test-Path $edgesFile)) { "" | Set-Content $edgesFile }
if (-not (Test-Path $processedFile)) { "" | Set-Content $processedFile }
Write-Host "  OK: Archivos de estado" -ForegroundColor Green

# --- Paso 3: Instalar paquete ---
Write-Host "[3/3] Instalando ctxmap..." -ForegroundColor Yellow
try {
    pip install -e $ScriptDir --quiet 2>$null
    Write-Host "  OK: ctxmap instalado via pip" -ForegroundColor Green
} catch {
    Write-Host "  WARN: No se pudo instalar globalmente" -ForegroundColor DarkYellow
    Write-Host "  Usa: python -m context_map.cli --help"
}

# --- Resumen ---
Write-Host ""
Write-Host "=== INSTALACION COMPLETA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Uso:"
Write-Host "  ctxmap init                    # Crear estructura"
Write-Host "  ctxmap build --project `"Nombre`" # Generar vault"
Write-Host "  ctxmap sync --project `"Nombre`" # Sync incremental"
Write-Host ""
Write-Host "Para agregar eventos, edita:"
Write-Host "  .context-map\raw\events.jsonl"
Write-Host ""

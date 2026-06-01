# Script para resetear completamente el entorno de desarrollo
# ADVERTENCIA: Esto eliminará TODOS los datos (base de datos, Redis, uploads)
# Uso: .\scripts\dev-reset.ps1

Write-Host "⚠️  ADVERTENCIA: Esto eliminará TODOS los datos del entorno de desarrollo" -ForegroundColor Red
Write-Host "   - Base de datos PostgreSQL" -ForegroundColor Yellow
Write-Host "   - Caché Redis" -ForegroundColor Yellow
Write-Host "   - Archivos subidos (uploads)" -ForegroundColor Yellow
Write-Host ""

$confirmation = Read-Host "¿Estás seguro? Escribe 'SI' para confirmar"

if ($confirmation -ne "SI") {
    Write-Host "❌ Operación cancelada" -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "🗑️  Deteniendo servicios y eliminando volúmenes..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml down -v

Write-Host ""
Write-Host "🗑️  Eliminando archivos subidos..." -ForegroundColor Cyan
if (Test-Path "uploads") {
    Remove-Item -Recurse -Force "uploads\*"
    Write-Host "✅ Archivos eliminados" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Iniciando servicios limpios..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml up -d

Write-Host ""
Write-Host "⏳ Esperando a que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "🔄 Ejecutando migraciones..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

Write-Host ""
Write-Host "✅ Entorno reseteado correctamente!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Ahora puedes crear el super admin con:" -ForegroundColor Yellow
Write-Host "   docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d taller_db -f /app/scripts/crear_super_admin.sql" -ForegroundColor White
Write-Host ""

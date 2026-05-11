# Script para ejecutar migraciones de base de datos
# Uso: .\scripts\dev-migrate.ps1

Write-Host "🔄 Ejecutando migraciones de base de datos..." -ForegroundColor Cyan
Write-Host ""

# Ejecutar migraciones con Alembic
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Migraciones ejecutadas correctamente" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Error al ejecutar migraciones" -ForegroundColor Red
    exit 1
}

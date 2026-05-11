# Script para detener el entorno de desarrollo con Docker
# Uso: .\scripts\dev-stop.ps1

Write-Host "🛑 Deteniendo entorno de desarrollo..." -ForegroundColor Cyan
Write-Host ""

docker-compose -f docker-compose.dev.yml down

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Servicios detenidos correctamente" -ForegroundColor Green
    Write-Host ""
    Write-Host "💡 Para eliminar también los volúmenes (base de datos), usa:" -ForegroundColor Yellow
    Write-Host "   docker-compose -f docker-compose.dev.yml down -v" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Error al detener servicios" -ForegroundColor Red
    exit 1
}

# Script para ver logs del entorno de desarrollo
# Uso: .\scripts\dev-logs.ps1 [servicio]
# Ejemplos:
#   .\scripts\dev-logs.ps1           # Ver todos los logs
#   .\scripts\dev-logs.ps1 backend   # Ver solo logs del backend
#   .\scripts\dev-logs.ps1 db        # Ver solo logs de la base de datos

param(
    [string]$Service = ""
)

Write-Host "📋 Mostrando logs..." -ForegroundColor Cyan
Write-Host "   Presiona Ctrl+C para salir" -ForegroundColor Yellow
Write-Host ""

if ($Service) {
    docker-compose -f docker-compose.dev.yml logs -f $Service
} else {
    docker-compose -f docker-compose.dev.yml logs -f
}

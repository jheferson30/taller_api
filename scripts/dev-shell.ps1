# Script para abrir shell en un contenedor
# Uso: .\scripts\dev-shell.ps1 [servicio]
# Ejemplos:
#   .\scripts\dev-shell.ps1 backend   # Shell en el backend
#   .\scripts\dev-shell.ps1 db        # Shell en PostgreSQL

param(
    [string]$Service = "backend"
)

Write-Host "🐚 Abriendo shell en $Service..." -ForegroundColor Cyan
Write-Host ""

if ($Service -eq "db") {
    # Para PostgreSQL, abrir psql directamente
    docker-compose -f docker-compose.dev.yml exec db psql -U postgres -d taller_db
} else {
    # Para otros servicios, abrir bash
    docker-compose -f docker-compose.dev.yml exec $Service /bin/sh
}

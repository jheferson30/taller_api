# Script para iniciar el entorno de desarrollo con Docker
# Uso: .\scripts\dev-start.ps1

Write-Host "🚀 Iniciando entorno de desarrollo con Docker..." -ForegroundColor Cyan
Write-Host ""

# Verificar que Docker está corriendo
$dockerRunning = docker info 2>&1 | Select-String "Server Version"
if (-not $dockerRunning) {
    Write-Host "❌ Docker no está corriendo. Por favor inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker está corriendo" -ForegroundColor Green

# Verificar que existe .env
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  No existe archivo .env, copiando desde .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Archivo .env creado. Por favor revisa y ajusta las variables." -ForegroundColor Green
    Write-Host ""
}

# Construir imágenes si es necesario
Write-Host "🔨 Construyendo imágenes Docker..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al construir imágenes" -ForegroundColor Red
    exit 1
}

# Iniciar servicios
Write-Host ""
Write-Host "🚀 Iniciando servicios..." -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error al iniciar servicios" -ForegroundColor Red
    exit 1
}

# Esperar a que los servicios estén listos
Write-Host ""
Write-Host "⏳ Esperando a que los servicios estén listos..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Verificar estado de los servicios
Write-Host ""
Write-Host "📊 Estado de los servicios:" -ForegroundColor Cyan
docker-compose -f docker-compose.dev.yml ps

Write-Host ""
Write-Host "✅ Entorno de desarrollo iniciado correctamente!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 URLs disponibles:" -ForegroundColor Cyan
Write-Host "   Backend API:  http://localhost:8000" -ForegroundColor White
Write-Host "   Frontend:     http://localhost:5173" -ForegroundColor White
Write-Host "   PostgreSQL:   localhost:5432" -ForegroundColor White
Write-Host "   Redis:        localhost:6379" -ForegroundColor White
Write-Host ""
Write-Host "📝 Comandos útiles:" -ForegroundColor Cyan
Write-Host "   Ver logs:           docker-compose -f docker-compose.dev.yml logs -f" -ForegroundColor White
Write-Host "   Ver logs backend:   docker-compose -f docker-compose.dev.yml logs -f backend" -ForegroundColor White
Write-Host "   Detener servicios:  docker-compose -f docker-compose.dev.yml down" -ForegroundColor White
Write-Host "   Reiniciar backend:  docker-compose -f docker-compose.dev.yml restart backend" -ForegroundColor White
Write-Host ""

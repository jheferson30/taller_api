#!/bin/bash

# Script de Deployment para Taller API
# Este script automatiza el proceso de deployment a producción

set -e  # Salir si cualquier comando falla

echo "=========================================="
echo "  Taller API - Deployment a Producción"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables de configuración
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
DB_NAME="${DB_NAME:-taller_db}"
DB_USER="${DB_USER:-postgres}"
MIGRATION_FILE="db/migracion_jwt_auth_2026_03_28.sql"

# Función para imprimir mensajes
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Función para verificar si un comando existe
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Verificar dependencias
print_info "Verificando dependencias..."

if ! command_exists psql; then
    print_error "psql no está instalado. Instala PostgreSQL client."
    exit 1
fi

if ! command_exists python; then
    print_error "python no está instalado."
    exit 1
fi

if ! command_exists pip; then
    print_error "pip no está instalado."
    exit 1
fi

print_info "Todas las dependencias están instaladas."
echo ""

# Paso 1: Verificar configuración
print_info "Paso 1/8: Verificando configuración..."

if [ ! -f ".env" ]; then
    print_error "Archivo .env no encontrado. Copia .env.example y configura las variables."
    exit 1
fi

# Verificar que JWT_SECRET_KEY no sea el valor por defecto
if grep -q "CAMBIAR_EN_PRODUCCION" .env; then
    print_error "JWT_SECRET_KEY tiene el valor por defecto. Genera una clave segura:"
    echo "  python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    exit 1
fi

# Verificar que ENVIRONMENT sea production
if ! grep -q "ENVIRONMENT=production" .env; then
    print_warning "ENVIRONMENT no está configurado como 'production' en .env"
    read -p "¿Continuar de todos modos? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_info "Configuración verificada."
echo ""

# Paso 2: Backup de base de datos
print_info "Paso 2/8: Creando backup de base de datos..."

mkdir -p "$BACKUP_DIR"

if pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"; then
    print_info "Backup creado: $BACKUP_FILE"
else
    print_error "Error al crear backup de base de datos."
    exit 1
fi

echo ""

# Paso 3: Ejecutar tests
print_info "Paso 3/8: Ejecutando tests..."

if pytest tests/ -v --tb=short -x; then
    print_info "Todos los tests pasaron."
else
    print_error "Tests fallaron. Deployment abortado."
    exit 1
fi

echo ""

# Paso 4: Análisis de seguridad
print_info "Paso 4/8: Ejecutando análisis de seguridad..."

if command_exists bandit; then
    if bandit -r app/ -ll; then
        print_info "Análisis de seguridad completado sin problemas críticos."
    else
        print_warning "Se encontraron problemas de seguridad. Revisa el reporte."
        read -p "¿Continuar de todos modos? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
else
    print_warning "bandit no está instalado. Saltando análisis de seguridad."
fi

echo ""

# Paso 5: Ejecutar migración de base de datos
print_info "Paso 5/8: Ejecutando migración de base de datos..."

if [ ! -f "$MIGRATION_FILE" ]; then
    print_error "Archivo de migración no encontrado: $MIGRATION_FILE"
    exit 1
fi

if psql -U "$DB_USER" -d "$DB_NAME" -f "$MIGRATION_FILE"; then
    print_info "Migración de base de datos completada."
else
    print_error "Error al ejecutar migración de base de datos."
    print_info "Puedes restaurar el backup con:"
    echo "  psql -U $DB_USER -d $DB_NAME < $BACKUP_FILE"
    exit 1
fi

echo ""

# Paso 6: Migrar contraseñas existentes
print_info "Paso 6/8: Migrando contraseñas existentes..."

if [ -f "scripts/migrate_passwords.py" ]; then
    if python scripts/migrate_passwords.py; then
        print_info "Migración de contraseñas completada."
    else
        print_warning "Error al migrar contraseñas. Puede que no haya contraseñas legacy."
    fi
else
    print_warning "Script de migración de contraseñas no encontrado. Saltando."
fi

echo ""

# Paso 7: Instalar/actualizar dependencias
print_info "Paso 7/8: Instalando dependencias..."

if pip install -r requirements.txt; then
    print_info "Dependencias instaladas."
else
    print_error "Error al instalar dependencias."
    exit 1
fi

echo ""

# Paso 8: Health check
print_info "Paso 8/8: Verificando health check..."

print_info "Iniciando servidor temporalmente para verificar..."

# Iniciar servidor en background
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
SERVER_PID=$!

# Esperar a que el servidor inicie
sleep 5

# Verificar health check
if curl -f http://localhost:8000/health >/dev/null 2>&1; then
    print_info "Health check exitoso."
else
    print_warning "Health check falló. Verifica la configuración."
fi

# Detener servidor temporal
kill $SERVER_PID 2>/dev/null || true

echo ""
echo "=========================================="
echo -e "${GREEN}  Deployment Completado Exitosamente${NC}"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Iniciar el servidor en producción:"
echo "   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000"
echo ""
echo "2. Configurar reverse proxy (Nginx/Apache)"
echo ""
echo "3. Configurar tareas periódicas (cron jobs)"
echo "   Ver README.md para detalles"
echo ""
echo "4. Monitorear logs de auditoría:"
echo "   SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 100;"
echo ""
echo "Backup guardado en: $BACKUP_FILE"
echo ""

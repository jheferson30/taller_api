#!/bin/bash

# Script de Rollback para Taller API
# Este script revierte el deployment en caso de problemas

set -e  # Salir si cualquier comando falla

echo "=========================================="
echo "  Taller API - Rollback de Deployment"
echo "=========================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables de configuración
BACKUP_DIR="backups"
DB_NAME="${DB_NAME:-taller_db}"
DB_USER="${DB_USER:-postgres}"

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

# Verificar que estamos en el directorio correcto
if [ ! -f "app/main.py" ]; then
    print_error "Este script debe ejecutarse desde el directorio raíz del proyecto."
    exit 1
fi

# Paso 1: Confirmar rollback
print_warning "Este script revertirá el deployment a la versión anterior."
print_warning "Esto incluye:"
echo "  - Revertir código a commit anterior"
echo "  - Habilitar modo legacy de autenticación"
echo "  - Opcionalmente revertir base de datos"
echo ""
read -p "¿Estás seguro de que quieres continuar? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_info "Rollback cancelado."
    exit 0
fi

echo ""

# Paso 2: Detener servidor
print_info "Paso 1/5: Deteniendo servidor..."

if pgrep -f "uvicorn app.main:app" > /dev/null; then
    pkill -f "uvicorn app.main:app"
    print_info "Servidor detenido."
else
    print_warning "No se encontró servidor corriendo."
fi

if pgrep -f "gunicorn app.main:app" > /dev/null; then
    pkill -f "gunicorn app.main:app"
    print_info "Servidor Gunicorn detenido."
fi

sleep 2
echo ""

# Paso 3: Revertir código
print_info "Paso 2/5: Revirtiendo código..."

# Verificar si hay cambios sin commit
if ! git diff-index --quiet HEAD --; then
    print_warning "Hay cambios sin commit. Guardando en stash..."
    git stash save "rollback_stash_$(date +%Y%m%d_%H%M%S)"
fi

# Mostrar últimos commits
echo "Últimos 5 commits:"
git log --oneline -5

echo ""
read -p "Ingresa el hash del commit al que quieres revertir (o presiona Enter para revertir 1 commit): " COMMIT_HASH

if [ -z "$COMMIT_HASH" ]; then
    # Revertir 1 commit
    print_info "Revirtiendo al commit anterior..."
    git reset --hard HEAD~1
else
    # Revertir al commit especificado
    print_info "Revirtiendo al commit $COMMIT_HASH..."
    git reset --hard "$COMMIT_HASH"
fi

print_info "Código revertido."
echo ""

# Paso 4: Habilitar modo legacy
print_info "Paso 3/5: Habilitando modo legacy de autenticación..."

if [ -f ".env" ]; then
    # Verificar si ENABLE_LEGACY_AUTH existe
    if grep -q "ENABLE_LEGACY_AUTH" .env; then
        # Actualizar valor
        sed -i 's/ENABLE_LEGACY_AUTH=.*/ENABLE_LEGACY_AUTH=true/' .env
        print_info "Modo legacy habilitado en .env"
    else
        # Agregar variable
        echo "" >> .env
        echo "# Modo legacy habilitado por rollback" >> .env
        echo "ENABLE_LEGACY_AUTH=true" >> .env
        print_info "Variable ENABLE_LEGACY_AUTH agregada a .env"
    fi
else
    print_error "Archivo .env no encontrado."
    exit 1
fi

echo ""

# Paso 5: Revertir base de datos (opcional)
print_info "Paso 4/5: Revertir base de datos..."

print_warning "IMPORTANTE: Solo revierte la base de datos si la migración causó problemas."
print_warning "Los usuarios que ya migraron a bcrypt NO podrán hacer login con el backup antiguo."
echo ""
read -p "¿Quieres revertir la base de datos? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Listar backups disponibles
    if [ -d "$BACKUP_DIR" ] && [ "$(ls -A $BACKUP_DIR)" ]; then
        echo "Backups disponibles:"
        ls -lh "$BACKUP_DIR"
        echo ""
        read -p "Ingresa el nombre del archivo de backup (ej: backup_20260331_120000.sql): " BACKUP_NAME
        
        BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
        
        if [ -f "$BACKUP_PATH" ]; then
            print_info "Restaurando backup: $BACKUP_PATH"
            
            if psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_PATH"; then
                print_info "Base de datos restaurada exitosamente."
            else
                print_error "Error al restaurar base de datos."
                exit 1
            fi
        else
            print_error "Archivo de backup no encontrado: $BACKUP_PATH"
            exit 1
        fi
    else
        print_error "No hay backups disponibles en $BACKUP_DIR"
        exit 1
    fi
else
    print_info "Saltando restauración de base de datos."
fi

echo ""

# Paso 6: Reinstalar dependencias
print_info "Paso 5/5: Reinstalando dependencias..."

if pip install -r requirements.txt; then
    print_info "Dependencias instaladas."
else
    print_error "Error al instalar dependencias."
    exit 1
fi

echo ""

# Resumen
echo "=========================================="
echo -e "${GREEN}  Rollback Completado${NC}"
echo "=========================================="
echo ""
echo "Acciones realizadas:"
echo "  ✓ Servidor detenido"
echo "  ✓ Código revertido"
echo "  ✓ Modo legacy habilitado"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  ✓ Base de datos restaurada"
fi
echo "  ✓ Dependencias reinstaladas"
echo ""
echo "Próximos pasos:"
echo "1. Iniciar el servidor:"
echo "   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "2. Verificar que el sistema funciona correctamente"
echo ""
echo "3. Investigar la causa del problema antes de reintentar deployment"
echo ""

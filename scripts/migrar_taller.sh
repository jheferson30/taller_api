#!/bin/bash
#
# Script simplificado para migrar un taller mono-tenant a multi-tenant
#
# Uso:
#   ./scripts/migrar_taller.sh
#

set -e

echo "=========================================="
echo "🔄 MIGRACIÓN MONO-TENANT → MULTI-TENANT"
echo "=========================================="
echo ""

# Solicitar información del taller origen
read -p "📍 Host de la BD origen (ej: 192.168.1.100): " SOURCE_HOST
read -p "🔢 Puerto de la BD origen (default: 5432): " SOURCE_PORT
SOURCE_PORT=${SOURCE_PORT:-5432}
read -p "👤 Usuario de la BD origen (default: postgres): " SOURCE_USER
SOURCE_USER=${SOURCE_USER:-postgres}
read -sp "🔐 Contraseña de la BD origen: " SOURCE_PASS
echo ""
read -p "💾 Nombre de la BD origen (default: taller_db): " SOURCE_DB
SOURCE_DB=${SOURCE_DB:-taller_db}

echo ""
echo "=========================================="
echo "📋 INFORMACIÓN DEL TALLER"
echo "=========================================="
echo ""

read -p "🏢 Nombre del taller: " TALLER_NOMBRE
read -p "📧 Email del taller: " TALLER_EMAIL
read -p "📱 Teléfono del taller (opcional): " TALLER_TELEFONO

echo ""
echo "=========================================="
echo "✅ RESUMEN"
echo "=========================================="
echo "Origen: $SOURCE_USER@$SOURCE_HOST:$SOURCE_PORT/$SOURCE_DB"
echo "Destino: Multi-tenant (Docker)"
echo "Taller: $TALLER_NOMBRE"
echo "Email: $TALLER_EMAIL"
echo "Teléfono: ${TALLER_TELEFONO:-N/A}"
echo "=========================================="
echo ""

read -p "¿Continuar con la migración? (s/n): " CONFIRMAR
if [ "$CONFIRMAR" != "s" ]; then
    echo "❌ Migración cancelada"
    exit 0
fi

echo ""
echo "🚀 Iniciando migración..."
echo ""

# Construir DSN de origen
SOURCE_DSN="postgresql://${SOURCE_USER}:${SOURCE_PASS}@${SOURCE_HOST}:${SOURCE_PORT}/${SOURCE_DB}"

# DSN de destino (Docker) — usa variables de entorno o valores por defecto del docker-compose
TARGET_DB_USER="${TARGET_DB_USER:-postgres}"
TARGET_DB_PASS="${DATABASE_PASSWORD:-${DB_PASSWORD:-postgres}}"
TARGET_DB_HOST="${TARGET_DB_HOST:-localhost}"
TARGET_DB_PORT="${TARGET_DB_PORT:-5432}"
TARGET_DB_NAME="${TARGET_DB_NAME:-taller_db}"
TARGET_DSN="postgresql://${TARGET_DB_USER}:${TARGET_DB_PASS}@${TARGET_DB_HOST}:${TARGET_DB_PORT}/${TARGET_DB_NAME}"

# Ejecutar script de migración dentro del contenedor
docker-compose -f docker-compose.dev.yml exec -T backend python /app/scripts/migrar_mono_a_multi_tenant.py \
    --source-db "$SOURCE_DSN" \
    --target-db "$TARGET_DSN" \
    --taller-nombre "$TALLER_NOMBRE" \
    --taller-email "$TALLER_EMAIL" \
    ${TALLER_TELEFONO:+--taller-telefono "$TALLER_TELEFONO"}

echo ""
echo "=========================================="
echo "✅ MIGRACIÓN COMPLETADA"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Verificar los datos migrados"
echo "2. Probar el login con usuarios del taller"
echo "3. Migrar archivos (fotos, PDFs) manualmente"
echo "4. Notificar a los usuarios del cambio"
echo ""
echo "Ver guía completa: GUIA_MIGRACION_MULTI_TENANT.md"
echo ""

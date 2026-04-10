#!/bin/bash
# Script para aplicar índices compuestos a la base de datos
# Requirements: 2.14

set -e

echo "Aplicando índices compuestos a la base de datos..."

# Leer variables de entorno
DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-taller_db}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}

# Ejecutar migración SQL
psql -U "$DB_USER" -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -f db/migrations/add_composite_indexes.sql

echo "✓ Índices compuestos aplicados exitosamente"

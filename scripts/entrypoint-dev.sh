#!/bin/bash
set -e

echo "🚀 Iniciando backend en modo desarrollo..."

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando base de datos..."
until python -c "
import os, psycopg2
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL').replace('+psycopg2', ''))
    conn.close()
    print('✅ Base de datos lista')
except Exception as e:
    print(f'⏳ BD no disponible: {e}')
    exit(1)
" 2>/dev/null; do
    sleep 2
done

# Ejecutar migraciones de Alembic
echo "🔄 Ejecutando migraciones..."
alembic upgrade head
echo "✅ Migraciones completadas"

# Crear roles y usuario admin si no existen
echo "👤 Verificando usuario admin y roles..."
python scripts/seed_admin.py
echo "✅ Seed completado"

# Iniciar servidor con hot reload para desarrollo
echo "🌐 Iniciando servidor con hot reload..."
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --reload-dir /app/app \
    --log-level info

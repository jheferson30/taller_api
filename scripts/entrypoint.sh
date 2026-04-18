#!/bin/bash
set -e

echo "🚀 Iniciando MecaApp..."

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

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones..."
alembic upgrade head
echo "✅ Migraciones completadas"

# Crear roles y usuario admin si no existen
echo "👤 Verificando usuario admin y roles..."
python scripts/seed_admin.py
echo "✅ Seed completado"

# Iniciar la aplicación
echo "🌐 Iniciando servidor..."
exec gunicorn app.main:app \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -

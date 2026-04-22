#!/bin/bash
set -e

echo "🚀 Iniciando MecaApp..."

# Función para sincronizar logo
sync_logo() {
    echo "🖼️  Sincronizando logo..."
    # Buscar el logo más reciente en uploads/logo/
    LATEST_LOGO=$(find uploads/logo/ -name "logo_*.png" -type f -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    
    if [ -n "$LATEST_LOGO" ] && [ -f "$LATEST_LOGO" ]; then
        echo "📋 Copiando logo: $LATEST_LOGO -> frontend/public/assets/logo.png"
        cp "$LATEST_LOGO" frontend/public/assets/logo.png
        echo "✅ Logo sincronizado"
    else
        echo "ℹ️  No se encontró logo personalizado, usando logo por defecto"
    fi
}

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

# Inicializar schema de base de datos (crear tablas si no existen)
echo "🔨 Inicializando schema de base de datos..."
python scripts/init_database.py
echo "✅ Schema inicializado"

# Ejecutar migraciones de Alembic
echo "🔄 Ejecutando migraciones..."
alembic upgrade head
echo "✅ Migraciones completadas"

# Crear roles y usuario admin si no existen
echo "👤 Verificando usuario admin y roles..."
python scripts/seed_admin.py
echo "✅ Seed completado"

# Sincronizar logo
sync_logo

# Iniciar la aplicación
echo "🌐 Iniciando servidor..."
exec gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 180 \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -

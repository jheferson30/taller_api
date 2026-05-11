#!/usr/bin/env python3
"""
Entrypoint para desarrollo con hot reload.

Este script:
1. Espera a que PostgreSQL esté disponible
2. Ejecuta migraciones de Alembic
3. Crea roles y usuario admin (seeding)
4. Inicia el servidor con hot reload
"""
import os
import sys
import time
import subprocess
import psycopg2

print("🚀 Iniciando backend en modo desarrollo...")

# Esperar a que PostgreSQL esté listo
print("⏳ Esperando base de datos...")
max_retries = 30
retry_count = 0

while retry_count < max_retries:
    try:
        conn_str = os.getenv('DATABASE_URL').replace('+psycopg2', '')
        conn = psycopg2.connect(conn_str)
        conn.close()
        print("✅ Base de datos lista")
        break
    except Exception as e:
        retry_count += 1
        if retry_count >= max_retries:
            print(f"❌ No se pudo conectar a la base de datos después de {max_retries} intentos")
            sys.exit(1)
        print(f"⏳ BD no disponible (intento {retry_count}/{max_retries}): {e}")
        time.sleep(2)

# Ejecutar migraciones de Alembic
print("🔄 Ejecutando migraciones...")
result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
if result.returncode != 0:
    print(f"❌ Error en migraciones:\n{result.stderr}")
    sys.exit(1)
print("✅ Migraciones completadas")

# Crear roles y usuario admin si no existen (opcional - no falla si hay error)
print("👤 Verificando usuario admin y roles...")
result = subprocess.run(["python", "scripts/seed_admin.py"], capture_output=True, text=True)
if result.returncode == 0:
    print(result.stdout)
    print("✅ Seed completado")
else:
    print(f"⚠️  Advertencia: No se pudo completar el seeding")
    print(f"   El sistema continuará sin datos iniciales")
    if result.stderr:
        print(f"   Error: {result.stderr[:200]}")  # Solo primeros 200 caracteres

# Iniciar servidor con hot reload para desarrollo
print("🌐 Iniciando servidor con hot reload...")
os.execvp("uvicorn", [
    "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "8000",
    "--reload",
    "--reload-dir", "/app/app",
    "--log-level", "info"
])

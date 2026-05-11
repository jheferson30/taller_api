#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import psycopg2

print("🚀 Iniciando MecaApp...")

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

# Iniciar la aplicación
print("🌐 Iniciando servidor...")
os.execvp("gunicorn", [
    "gunicorn",
    "app.main:app",
    "--workers", "4",
    "--worker-class", "uvicorn.workers.UvicornWorker",
    "--bind", "0.0.0.0:8000",
    "--timeout", "180",
    "--graceful-timeout", "30",
    "--access-logfile", "-",
    "--error-logfile", "-"
])

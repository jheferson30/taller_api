#!/usr/bin/env python3
"""
Entrypoint de producción — Taller API v3

Secuencia de arranque:
1. Esperar a que PostgreSQL esté listo
2. Ejecutar migraciones Alembic
3. Crear roles del sistema (idempotente)
4. Iniciar Gunicorn
"""
import os
import sys
import time
import subprocess

import psycopg2

print("🚀 Iniciando Taller API v3...")
print(f"   Entorno: {os.getenv('ENVIRONMENT', 'development')}")

# ── 1. Esperar PostgreSQL ─────────────────────────────────────────────────────
print("⏳ Esperando base de datos...")
max_retries = 30

for intento in range(1, max_retries + 1):
    try:
        conn_str = os.getenv("DATABASE_URL", "").replace("+psycopg2", "")
        conn = psycopg2.connect(conn_str)
        conn.close()
        print("✅ Base de datos lista")
        break
    except Exception as e:
        if intento >= max_retries:
            print(f"❌ No se pudo conectar a la BD después de {max_retries} intentos: {e}")
            sys.exit(1)
        print(f"   BD no disponible (intento {intento}/{max_retries}): {e}")
        time.sleep(3)

# ── 2. Migraciones Alembic ────────────────────────────────────────────────────
print("🔄 Ejecutando migraciones...")
result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
if result.returncode != 0:
    print(f"❌ Error en migraciones:\n{result.stderr}")
    sys.exit(1)
print("✅ Migraciones completadas")

# ── 3. Crear roles del sistema ────────────────────────────────────────────────
print("🔐 Verificando roles del sistema...")
try:
    result = subprocess.run(
        ["python", "scripts/seed_admin.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"⚠️  Advertencia en seed_admin: {result.stderr}")
    else:
        print("✅ Roles verificados")
        if result.stdout:
            print(result.stdout.strip())
except Exception as e:
    print(f"⚠️  No se pudo ejecutar seed_admin: {e}")

# ── 4. Iniciar Gunicorn ───────────────────────────────────────────────────────
print("🌐 Iniciando servidor Gunicorn...")
os.execvp("gunicorn", [
    "gunicorn",
    "app.main:app",
    "--workers", "4",
    "--worker-class", "uvicorn.workers.UvicornWorker",
    "--bind", "0.0.0.0:8000",
    "--timeout", "180",
    "--graceful-timeout", "30",
    "--access-logfile", "-",
    "--error-logfile", "-",
])

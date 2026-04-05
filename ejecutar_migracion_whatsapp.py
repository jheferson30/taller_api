"""
Script para ejecutar la migración de WhatsApp
"""
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

# Leer la migración
with open("db/migracion_whatsapp_2026.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Conectar y ejecutar
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:123456@localhost:5432/taller_db?client_encoding=utf8"
)
# Limpiar el URL para psycopg2 (remover el +psycopg2 si existe)
DATABASE_URL = DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://")

try:
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Parte 1: Agregar columnas a configuracion_taller
    print("Agregando columnas a configuracion_taller...")
    try:
        cursor.execute("""
            ALTER TABLE configuracion_taller
              ADD COLUMN IF NOT EXISTS whatsapp_token     TEXT,
              ADD COLUMN IF NOT EXISTS whatsapp_phone_id  VARCHAR(50),
              ADD COLUMN IF NOT EXISTS whatsapp_enabled   BOOLEAN NOT NULL DEFAULT FALSE;
        """)
        conn.commit()
        print("✓ Columnas agregadas:")
        print("  • whatsapp_token")
        print("  • whatsapp_phone_id")
        print("  • whatsapp_enabled")
    except Exception as e:
        print(f"⚠ Error agregando columnas: {e}")
        conn.rollback()
    
    # Parte 2: Crear tabla log_notificacion
    print("\nCreando tabla log_notificacion...")
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS log_notificacion (
                id               SERIAL PRIMARY KEY,
                ticket_id        INTEGER REFERENCES tickets(id) ON DELETE SET NULL,
                telefono_destino VARCHAR(30),
                tipo_evento      VARCHAR(20) NOT NULL,
                mensaje_enviado  TEXT,
                resultado        VARCHAR(10) NOT NULL,
                error_detalle    TEXT,
                created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        conn.commit()
        print("✓ Tabla log_notificacion creada")
    except Exception as e:
        print(f"⚠ Error creando tabla: {e}")
        conn.rollback()
    
    # Parte 3: Crear índices
    print("\nCreando índices...")
    try:
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_log_notificacion_ticket_id ON log_notificacion(ticket_id);
            CREATE INDEX IF NOT EXISTS idx_log_notificacion_created_at ON log_notificacion(created_at DESC);
        """)
        conn.commit()
        print("✓ Índices creados")
    except Exception as e:
        print(f"⚠ Error creando índices: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()
    print("\n✓ Migración completada")
    
except Exception as e:
    print(f"ERROR de conexión: {e}")
    exit(1)

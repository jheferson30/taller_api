#!/usr/bin/env python3
"""
Script para aplicar índices compuestos a la base de datos usando Python
"""
import os
from sqlalchemy import create_engine, text

# Leer DATABASE_URL del entorno
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:123456@localhost:5432/taller_db?client_encoding=utf8'
)

print("Aplicando índices compuestos a la base de datos...")
print(f"Conectando a: {DATABASE_URL.split('@')[1]}")  # Ocultar credenciales

# Crear engine
engine = create_engine(DATABASE_URL)

# Leer archivo SQL
with open('db/migrations/add_composite_indexes.sql', 'r', encoding='utf-8') as f:
    sql = f.read()

# Ejecutar migración
try:
    with engine.connect() as conn:
        # Ejecutar cada statement por separado
        statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
        for statement in statements:
            if statement:
                print(f"Ejecutando: {statement[:50]}...")
                conn.execute(text(statement))
        conn.commit()
    print("✓ Índices compuestos aplicados exitosamente")
except Exception as e:
    print(f"✗ Error al aplicar índices: {e}")
    raise

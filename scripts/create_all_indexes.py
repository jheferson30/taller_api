#!/usr/bin/env python3
"""Create all composite indexes"""
import os

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:123456@localhost:5432/taller_db?client_encoding=utf8",
)

engine = create_engine(DATABASE_URL)

indexes = [
    "CREATE INDEX IF NOT EXISTS idx_tickets_estado_fecha ON tickets(estado, fecha_ingreso DESC)",
    "CREATE INDEX IF NOT EXISTS idx_tickets_placa ON tickets(placa)",
    "CREATE INDEX IF NOT EXISTS idx_audit_log_user_action_date ON audit_log(user_id, action, timestamp DESC)",
    "CREATE INDEX IF NOT EXISTS idx_token_blacklist_jti_exp ON token_blacklist(jti, expires_at)",
    "CREATE INDEX IF NOT EXISTS idx_vehiculos_placa ON vehiculos(placa)",
]

for idx_sql in indexes:
    print(f"Creating: {idx_sql[:60]}...")
    try:
        with engine.connect() as conn:
            conn.execute(text(idx_sql))
            conn.commit()
        print("  ✓ Created")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n✓ All indexes processed")

#!/usr/bin/env python3
"""Check database indexes"""
import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:123456@localhost:5432/taller_db?client_encoding=utf8'
)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = 'tickets' 
        ORDER BY indexname
    """))
    
    print("\nÍndices en la tabla 'tickets':")
    print("=" * 80)
    for row in result:
        print(f"\n{row[0]}:")
        print(f"  {row[1]}")
    print("=" * 80)

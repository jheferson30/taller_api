"""
Script de inicialización de base de datos.
Crea todas las tablas definidas en los modelos SQLAlchemy.

Uso:
    python scripts/init_database.py
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import inspect

from app.configuracion.base_datos import Base, engine


def init_database():
    """Crea todas las tablas si no existen."""

    # Importar todos los modelos para que SQLAlchemy los registre

    # Verificar qué tablas ya existen
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    print(f"📊 Tablas existentes: {len(existing_tables)}")
    if existing_tables:
        print(f"   {', '.join(existing_tables[:5])}{'...' if len(existing_tables) > 5 else ''}")

    # Crear todas las tablas que no existen
    print("🔨 Creando tablas desde modelos SQLAlchemy...")
    Base.metadata.create_all(bind=engine)

    # Verificar tablas después de la creación
    inspector = inspect(engine)
    final_tables = inspector.get_table_names()

    print(f"✅ Total de tablas en la base de datos: {len(final_tables)}")
    print(f"   Tablas creadas: {len(final_tables) - len(existing_tables)}")

    if len(final_tables) > len(existing_tables):
        new_tables = set(final_tables) - set(existing_tables)
        print(f"   Nuevas tablas: {', '.join(sorted(new_tables))}")
    else:
        print("   Todas las tablas ya existían")


if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ Error al inicializar base de datos: {e}")
        sys.exit(1)

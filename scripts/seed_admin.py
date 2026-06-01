#!/usr/bin/env python3
"""
Script de seeding — crea roles del sistema si no existen.

Idempotente: puede ejecutarse múltiples veces sin errores.
En producción solo crea roles — el SUPER_ADMIN se crea con crear_super_admin.sql.

Uso:
    python scripts/seed_admin.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# Importar todos los modelos para que SQLAlchemy resuelva las relaciones
import app.modelos.taller  # noqa: F401
import app.modelos.configuracion_taller  # noqa: F401
import app.modelos.mecanico  # noqa: F401
import app.modelos.vehiculo  # noqa: F401
import app.modelos.ticket  # noqa: F401
import app.modelos.audit_log  # noqa: F401
import app.modelos.notificacion  # noqa: F401

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modelos.role import Role
from app.modelos.user import User
from app.seguridad.password_hasher import PasswordHasher


def get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/taller_db",
    )


def seed_roles(session) -> int:
    """Crea los roles base del sistema si no existen."""
    roles_base = [
        {"name": "ADMIN",          "description": "Administrador con acceso completo al taller"},
        {"name": "MECANICO",       "description": "Mecánico con acceso a tickets y procesos"},
        {"name": "RECEPCIONISTA",  "description": "Recepcionista con acceso a creación de tickets"},
        {"name": "SOLO_LECTURA",   "description": "Usuario con acceso de solo lectura"},
        {"name": "SUPER_ADMIN",    "description": "Administrador de la plataforma SaaS"},
    ]

    creados = 0
    for datos in roles_base:
        existe = session.query(Role).filter(Role.name == datos["name"]).first()
        if not existe:
            session.add(Role(**datos))
            creados += 1
            print(f"   ✅ Rol creado: {datos['name']}")
        else:
            print(f"   ℹ️  Rol ya existe: {datos['name']}")

    if creados:
        session.commit()

    return creados


def seed_admin_user(session) -> int:
    """
    Crea usuario admin de desarrollo si no existe.
    En producción se omite — el SUPER_ADMIN se crea con crear_super_admin.sql.
    """
    if os.getenv("ENVIRONMENT", "development") == "production":
        print("   ℹ️  Producción: omitiendo usuario admin genérico")
        return 0

    if session.query(User).filter(User.username == "admin").first():
        print("   ℹ️  Usuario admin ya existe")
        return 0

    rol_admin = session.query(Role).filter(Role.name == "ADMIN").first()
    if not rol_admin:
        print("   ❌ Rol ADMIN no encontrado")
        return 0

    password = os.getenv("ADMIN_PASSWORD", "admin123")
    hasher = PasswordHasher()

    admin = User(
        username="admin",
        password_hash=hasher.hash_password(password),
        email="admin@taller.local",
        is_active=True,
    )
    admin.roles.append(rol_admin)
    session.add(admin)
    session.commit()

    print(f"   ✅ Usuario admin creado (password: {password})")
    if password == "admin123":
        print("   ⚠️  Cambia la contraseña por defecto antes de usar en producción")

    return 1


def main():
    print("🌱 Seeding de base de datos...\n")

    try:
        engine = create_engine(get_database_url())
        session = sessionmaker(bind=engine)()
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        sys.exit(1)

    try:
        print("📋 Roles del sistema:")
        seed_roles(session)

        print("\n👤 Usuario administrador:")
        seed_admin_user(session)

        print("\n✅ Seeding completado")
    except Exception as e:
        print(f"\n❌ Error en seeding: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Script de seeding para crear usuario admin y roles iniciales.

Este script es idempotente - puede ejecutarse múltiples veces sin causar errores.
Solo crea recursos si no existen.

Uso:
    python scripts/seed_admin.py
"""
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path para importar módulos de la app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modelos.role import Role
from app.modelos.user import User
from app.seguridad.password_hasher import PasswordHasher


def get_database_url():
    """Obtiene la URL de la base de datos desde variables de entorno."""
    return os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/taller_db")


def seed_roles(session):
    """
    Crea los roles básicos del sistema si no existen.
    
    Roles:
    - ADMIN: Acceso completo al sistema
    - MECANICO: Gestión de tickets y procesos
    - RECEPCIONISTA: Crear tickets y consultar información
    - SOLO_LECTURA: Solo consultas
    """
    roles_base = [
        {
            "nombre": "ADMIN",
            "descripcion": "Administrador con acceso completo al sistema",
        },
        {
            "nombre": "MECANICO",
            "descripcion": "Mecánico con acceso a gestión de tickets y procesos",
        },
        {
            "nombre": "RECEPCIONISTA",
            "descripcion": "Recepcionista con acceso a creación de tickets y consultas",
        },
        {
            "nombre": "SOLO_LECTURA",
            "descripcion": "Usuario con acceso de solo lectura",
        },
    ]
    
    roles_creados = 0
    for rol_data in roles_base:
        rol_existente = session.query(Role).filter(Role.nombre == rol_data["nombre"]).first()
        if not rol_existente:
            rol = Role(**rol_data)
            session.add(rol)
            roles_creados += 1
            print(f"✅ Rol creado: {rol_data['nombre']}")
        else:
            print(f"ℹ️  Rol ya existe: {rol_data['nombre']}")
    
    if roles_creados > 0:
        session.commit()
        print(f"\n✅ {roles_creados} roles creados exitosamente")
    else:
        print("\nℹ️  Todos los roles ya existían")
    
    return roles_creados


def seed_admin_user(session):
    """
    Crea el usuario admin por defecto si no existe.
    
    Credenciales por defecto:
    - Username: admin
    - Password: admin123 (debe cambiarse en producción)
    - Rol: ADMIN
    """
    # Verificar si ya existe un usuario admin
    admin_existente = session.query(User).filter(User.username == "admin").first()
    
    if admin_existente:
        print("ℹ️  Usuario admin ya existe")
        return 0
    
    # Obtener el rol ADMIN
    rol_admin = session.query(Role).filter(Role.nombre == "ADMIN").first()
    if not rol_admin:
        print("❌ Error: Rol ADMIN no encontrado. Ejecuta seed_roles primero.")
        return 0
    
    # Obtener contraseña desde variable de entorno o usar default
    password = os.getenv("ADMIN_PASSWORD", "admin123")
    
    # Hashear contraseña
    hasher = PasswordHasher()
    password_hash = hasher.hash_password(password)
    
    # Crear usuario admin
    admin = User(
        username="admin",
        password_hash=password_hash,
        email="admin@taller.local",
        nombre_completo="Administrador del Sistema",
        activo=True,
    )
    
    # Asignar rol ADMIN
    admin.roles.append(rol_admin)
    
    session.add(admin)
    session.commit()
    
    print(f"✅ Usuario admin creado exitosamente")
    print(f"   Username: admin")
    print(f"   Password: {password}")
    if password == "admin123":
        print("   ⚠️  ADVERTENCIA: Cambia la contraseña por defecto en producción")
    
    return 1


def main():
    """
    Función principal que ejecuta el seeding completo.
    """
    print("🌱 Iniciando seeding de base de datos...\n")
    
    # Crear engine y sesión
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        sys.exit(1)
    
    try:
        # 1. Crear roles
        print("📋 Creando roles del sistema...")
        seed_roles(session)
        
        print("\n" + "="*60 + "\n")
        
        # 2. Crear usuario admin
        print("👤 Creando usuario administrador...")
        seed_admin_user(session)
        
        print("\n" + "="*60)
        print("✅ Seeding completado exitosamente\n")
        
    except Exception as e:
        print(f"\n❌ Error durante el seeding: {e}")
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()

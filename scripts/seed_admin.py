"""
Script de inicialización: crea usuario admin por defecto si no existe.

Uso:
    python scripts/seed_admin.py

Variables de entorno requeridas:
    DATABASE_URL - URL de conexión a PostgreSQL

Variables opcionales:
    ADMIN_USERNAME  - Nombre de usuario admin (default: admin)
    ADMIN_PASSWORD  - Contraseña admin (default: Admin1234!)
    ADMIN_EMAIL     - Email admin (default: admin@taller.local)

IMPORTANTE: Cambiar la contraseña después del primer login.
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

import bcrypt
from sqlalchemy import text

from app.configuracion.base_datos import engine


def seed_admin():
    username = os.getenv("ADMIN_USERNAME", "admin")
    password = os.getenv("ADMIN_PASSWORD", "Admin1234!")
    email = os.getenv("ADMIN_EMAIL", "admin@taller.local")

    with engine.connect() as conn:
        # Verificar si ya existe un usuario admin
        result = conn.execute(
            text("SELECT id FROM users WHERE username = :username"),
            {"username": username},
        )
        existing = result.fetchone()

        if existing:
            print(f"✅ Usuario '{username}' ya existe (id={existing[0]}). No se creó nada.")
            return

        # Crear hash de contraseña
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        # Insertar usuario
        result = conn.execute(
            text(
                "INSERT INTO users (username, email, password_hash, is_active, is_migrated) "
                "VALUES (:username, :email, :password_hash, true, false) RETURNING id"
            ),
            {"username": username, "email": email, "password_hash": password_hash},
        )
        user_id = result.fetchone()[0]

        # Verificar si existe el rol ADMIN, si no crearlo
        result = conn.execute(text("SELECT id FROM roles WHERE name = 'ADMIN'"))
        role = result.fetchone()

        if not role:
            result = conn.execute(
                text(
                    "INSERT INTO roles (name, description) "
                    "VALUES ('ADMIN', 'Administrador del sistema') RETURNING id"
                )
            )
            role_id = result.fetchone()[0]
            print("✅ Rol ADMIN creado.")
        else:
            role_id = role[0]

        # Asignar rol ADMIN al usuario
        conn.execute(
            text("INSERT INTO user_roles (user_id, role_id) VALUES (:user_id, :role_id)"),
            {"user_id": user_id, "role_id": role_id},
        )

        conn.commit()

        print("✅ Usuario admin creado exitosamente:")
        print(f"   Usuario:    {username}")
        print(f"   Contraseña: {password}")
        print(f"   Email:      {email}")
        print("")
        print("⚠️  IMPORTANTE: Cambia la contraseña después del primer login.")


if __name__ == "__main__":
    seed_admin()

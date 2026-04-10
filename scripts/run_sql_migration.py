#!/usr/bin/env python3
"""
Script para ejecutar la migración SQL de autenticación JWT.

Este script ejecuta el archivo db/migracion_jwt_auth_2026_03_28.sql
que crea las tablas necesarias para el sistema de autenticación JWT.

Uso:
    python scripts/run_sql_migration.py
"""

import os
import sys

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from app.configuracion.base_datos import engine


def run_migration():
    """Ejecuta el script de migración SQL."""

    print("\n" + "=" * 70)
    print("EJECUTANDO MIGRACIÓN SQL: Sistema de Autenticación JWT")
    print("=" * 70)
    print("\nEste script creará las siguientes tablas:")
    print("  - users")
    print("  - roles (con roles por defecto)")
    print("  - user_roles")
    print("  - audit_log")
    print("  - token_blacklist")
    print("  - password_reset_tokens")
    print("\nTambién agregará índice a movimientos_caja.fecha_creacion\n")

    # Confirmar ejecución
    response = input("¿Desea continuar con la migración? (s/n): ")
    if response.lower() not in ["s", "si", "yes", "y"]:
        print("\n❌ Migración cancelada por el usuario")
        return

    # Leer archivo SQL
    sql_file = os.path.join(
        os.path.dirname(__file__), "..", "db", "migracion_jwt_auth_2026_03_28.sql"
    )

    try:
        with open(sql_file, encoding="utf-8") as f:
            sql_script = f.read()

        print("\n🔄 Ejecutando migración SQL...")
        print("─" * 70)

        # Ejecutar script SQL
        with engine.connect() as connection:
            # Ejecutar el script completo
            connection.execute(text(sql_script))
            connection.commit()

        print("\n✅ Migración SQL completada exitosamente")
        print("\nTablas creadas:")
        print("  ✓ users")
        print("  ✓ roles (ADMIN, MECANICO, RECEPCIONISTA, SOLO_LECTURA)")
        print("  ✓ user_roles")
        print("  ✓ audit_log")
        print("  ✓ token_blacklist")
        print("  ✓ password_reset_tokens")
        print("\nÍndice agregado:")
        print("  ✓ idx_movimientos_caja_fecha_creacion")
        print("\n" + "=" * 70)
        print("\nAhora puede ejecutar el script de migración de contraseñas:")
        print("  python scripts/migrate_passwords.py")
        print("=" * 70 + "\n")

    except FileNotFoundError:
        print(f"\n❌ ERROR: No se encontró el archivo SQL: {sql_file}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR al ejecutar migración: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    run_migration()

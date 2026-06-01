#!/usr/bin/env python3
"""
Script de migración de contraseñas desde configuracion_seguridad a users.

Este script migra las contraseñas SHA256 existentes en la tabla
configuracion_seguridad a la nueva tabla users con el sistema JWT.

Las contraseñas se copian directamente (sin re-hashear) y se marcan
con is_migrated=False para que en el próximo login se conviertan
automáticamente a bcrypt.

Uso:
    python scripts/migrate_passwords.py

Requisitos:
    - Base de datos debe tener las tablas users, roles, user_roles, audit_log
    - Debe existir el rol ADMIN en la tabla roles
    - Variable de entorno DATABASE_URL configurada (o usar default)
"""

import os
import sys
from datetime import datetime
from typing import Any

# Agregar el directorio raíz al path para importar módulos de app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session

from app.configuracion.base_datos import SessionLocal

# Importar modelos directamente desde sus archivos
from app.modelos.audit_log import AuditLog
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad
from app.modelos.role import Role
from app.modelos.user import User


class MigrationReport:
    """Reporte de migración de contraseñas."""

    def __init__(self):
        self.total_processed = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.users_created: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []
        self.start_time = datetime.now()
        self.end_time = None

    def add_success(self, username: str, clave: str):
        """Registra una migración exitosa."""
        self.successful += 1
        self.users_created.append(
            {"username": username, "clave_origen": clave, "timestamp": datetime.now().isoformat()}
        )

    def add_error(self, clave: str, error: str):
        """Registra un error de migración."""
        self.failed += 1
        self.errors.append(
            {"clave": clave, "error": error, "timestamp": datetime.now().isoformat()}
        )

    def add_skipped(self, clave: str, reason: str):
        """Registra una migración omitida."""
        self.skipped += 1
        self.errors.append(
            {"clave": clave, "reason": reason, "timestamp": datetime.now().isoformat()}
        )

    def finalize(self):
        """Finaliza el reporte."""
        self.end_time = datetime.now()

    def get_duration(self) -> float:
        """Retorna la duración de la migración en segundos."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def print_report(self):
        """Imprime el reporte en consola."""
        print("\n" + "=" * 70)
        print("REPORTE DE MIGRACIÓN DE CONTRASEÑAS")
        print("=" * 70)
        print(f"\nFecha: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duración: {self.get_duration():.2f} segundos")
        print(f"\nTotal procesados: {self.total_processed}")
        print(f"Exitosos: {self.successful}")
        print(f"Fallidos: {self.failed}")
        print(f"Omitidos: {self.skipped}")

        if self.users_created:
            print(f"\n{'─'*70}")
            print("USUARIOS CREADOS:")
            print(f"{'─'*70}")
            for user in self.users_created:
                print(f"  ✓ {user['username']} (origen: {user['clave_origen']})")

        if self.errors:
            print(f"\n{'─'*70}")
            print("ERRORES:")
            print(f"{'─'*70}")
            for error in self.errors:
                print(
                    f"  ✗ {error.get('clave', 'N/A')}: {error.get('error', error.get('reason', 'Unknown'))}"
                )

        print("\n" + "=" * 70)

    def save_to_file(self, filename: str = "migration_report.txt"):
        """Guarda el reporte en un archivo."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("REPORTE DE MIGRACIÓN DE CONTRASEÑAS\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Fecha: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duración: {self.get_duration():.2f} segundos\n\n")
            f.write(f"Total procesados: {self.total_processed}\n")
            f.write(f"Exitosos: {self.successful}\n")
            f.write(f"Fallidos: {self.failed}\n")
            f.write(f"Omitidos: {self.skipped}\n\n")

            if self.users_created:
                f.write("─" * 70 + "\n")
                f.write("USUARIOS CREADOS:\n")
                f.write("─" * 70 + "\n")
                for user in self.users_created:
                    f.write(f"  ✓ {user['username']} (origen: {user['clave_origen']})\n")
                f.write("\n")

            if self.errors:
                f.write("─" * 70 + "\n")
                f.write("ERRORES:\n")
                f.write("─" * 70 + "\n")
                for error in self.errors:
                    f.write(
                        f"  ✗ {error.get('clave', 'N/A')}: {error.get('error', error.get('reason', 'Unknown'))}\n"
                    )
                f.write("\n")

            f.write("=" * 70 + "\n")


def get_username_from_clave(clave: str) -> str:
    """
    Genera un username a partir de la clave de configuracion_seguridad.

    Ejemplos:
        economia_password -> economia
        admin_password -> admin
        mecanico_password -> mecanico

    Args:
        clave: Clave de configuracion_seguridad

    Returns:
        Username generado
    """
    # Remover sufijos comunes
    username = clave.replace("_password", "").replace("_palabra_clave", "")
    return username


def migrate_passwords(db: Session) -> MigrationReport:
    """
    Migra contraseñas desde configuracion_seguridad a users.

    Proceso:
    1. Lee todos los registros de configuracion_seguridad
    2. Para cada registro:
       - Genera username basado en la clave
       - Crea usuario con hash SHA256 temporal (sin re-hashear)
       - Marca is_migrated=False
       - Asigna rol ADMIN por defecto
       - Registra en audit_log
    3. Genera reporte de migración

    Args:
        db: Sesión de base de datos

    Returns:
        Reporte de migración
    """
    report = MigrationReport()

    print("\n🔄 Iniciando migración de contraseñas...")
    print("─" * 70)

    # Verificar que existe el rol ADMIN
    admin_role = db.query(Role).filter(Role.name == "ADMIN").first()
    if not admin_role:
        print("❌ ERROR: No existe el rol ADMIN en la base de datos")
        print("   Por favor ejecute primero la migración SQL que crea los roles")
        report.add_error("SYSTEM", "Rol ADMIN no encontrado en la base de datos")
        report.finalize()
        return report

    # Leer todos los registros de configuracion_seguridad
    configs = db.query(ConfiguracionSeguridad).all()
    report.total_processed = len(configs)

    print(f"📋 Encontrados {len(configs)} registros en configuracion_seguridad\n")

    for config in configs:
        try:
            # Generar username desde la clave
            username = get_username_from_clave(config.clave)

            # Verificar si el usuario ya existe
            existing_user = db.query(User).filter(User.username == username).first()
            if existing_user:
                print(f"⏭️  Omitiendo {username}: usuario ya existe")
                report.add_skipped(config.clave, f"Usuario {username} ya existe")
                continue

            # Generar email basado en username
            email = f"{username}@taller.local"

            # Verificar si el email ya existe
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                # Agregar timestamp al email para hacerlo único
                email = f"{username}_{int(datetime.now().timestamp())}@taller.local"

            # Crear usuario con hash SHA256 temporal (copiar directamente, sin re-hashear)
            new_user = User(
                username=username,
                email=email,
                password_hash=config.valor_hash,  # Copiar hash SHA256 directamente
                is_active=True,
                is_migrated=False,  # Marcar para migración automática en próximo login
            )

            db.add(new_user)
            db.flush()  # Obtener el ID del usuario

            # Asignar rol ADMIN por defecto
            new_user.roles.append(admin_role)

            # Registrar migración en audit_log
            audit_entry = AuditLog(
                user_id=None,  # Migración automática, no hay usuario que la ejecuta
                action="PASSWORD_MIGRATED",
                resource_type="user",
                resource_id=new_user.id,
                ip_address="127.0.0.1",  # Script local
                user_agent="migration_script",
                details={
                    "username": username,
                    "clave_origen": config.clave,
                    "migration_date": datetime.now().isoformat(),
                    "is_migrated": False,
                    "role": "ADMIN",
                },
            )
            db.add(audit_entry)

            db.commit()

            print(f"✓ Migrado: {username} (origen: {config.clave})")
            report.add_success(username, config.clave)

        except Exception as e:
            db.rollback()
            error_msg = str(e)
            print(f"✗ Error migrando {config.clave}: {error_msg}")
            report.add_error(config.clave, error_msg)

    report.finalize()
    return report


def main():
    """Función principal del script."""
    print("\n" + "=" * 70)
    print("SCRIPT DE MIGRACIÓN DE CONTRASEÑAS")
    print("=" * 70)
    print("\nEste script migra contraseñas desde configuracion_seguridad a users")
    print("Las contraseñas se marcan con is_migrated=False para conversión automática")
    print("a bcrypt en el próximo login.\n")

    # Confirmar ejecución
    response = input("¿Desea continuar con la migración? (s/n): ")
    if response.lower() not in ["s", "si", "yes", "y"]:
        print("\n❌ Migración cancelada por el usuario")
        return

    # Crear sesión de base de datos
    db = SessionLocal()

    try:
        # Ejecutar migración
        report = migrate_passwords(db)

        # Imprimir reporte
        report.print_report()

        # Guardar reporte en archivo
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report.save_to_file(report_filename)
        print(f"\n📄 Reporte guardado en: {report_filename}")

        # Mensaje final
        if report.failed > 0:
            print("\n⚠️  Migración completada con errores")
            print("   Por favor revise el reporte para más detalles")
            sys.exit(1)
        else:
            print("\n✅ Migración completada exitosamente")
            print(f"   {report.successful} usuarios migrados")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {str(e)}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

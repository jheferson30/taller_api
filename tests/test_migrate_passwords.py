"""
Tests para el script de migración de contraseñas.

Valida que el script migrate_passwords.py funcione correctamente:
- Lectura de configuracion_seguridad
- Creación de usuarios con hash SHA256 temporal
- Marcado de is_migrated=False
- Asignación de rol ADMIN
- Registro en audit_log
"""

import os

# Importar funciones del script
import sys

import pytest
from sqlalchemy.orm import Session

from app.configuracion.base_datos import Base, engine

# Importar modelos directamente desde sus archivos
from app.modelos.audit_log import AuditLog
from app.modelos.configuracion_seguridad import ConfiguracionSeguridad
from app.modelos.role import Role
from app.modelos.user import User

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.migrate_passwords import MigrationReport, get_username_from_clave, migrate_passwords


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos para testing."""
    Base.metadata.create_all(bind=engine)
    from app.configuracion.base_datos import SessionLocal

    db = SessionLocal()

    # Limpiar tablas relevantes
    db.query(AuditLog).delete()
    db.query(User).delete()
    db.query(ConfiguracionSeguridad).delete()
    db.query(Role).delete()
    db.commit()

    # Crear rol ADMIN
    admin_role = Role(name="ADMIN", description="Administrador del sistema")
    db.add(admin_role)
    db.commit()

    yield db

    # Cleanup
    db.query(AuditLog).delete()
    db.query(User).delete()
    db.query(ConfiguracionSeguridad).delete()
    db.query(Role).delete()
    db.commit()
    db.close()


def test_get_username_from_clave():
    """
    Test: Generación de username desde clave.

    Valida: Requirements 2.1
    """
    assert get_username_from_clave("economia_password") == "economia"
    assert get_username_from_clave("admin_password") == "admin"
    assert get_username_from_clave("mecanico_password") == "mecanico"
    assert get_username_from_clave("test_palabra_clave") == "test"


def test_migrate_passwords_success(db_session: Session):
    """
    Test: Migración exitosa de contraseñas.

    Verifica que:
    - Se crean usuarios desde configuracion_seguridad
    - Los hashes SHA256 se copian directamente (sin re-hashear)
    - is_migrated=False
    - Se asigna rol ADMIN
    - Se registra en audit_log

    Valida: Requirements 2.1, 2.2, 2.3, 2.5
    """
    # Crear registros de prueba en configuracion_seguridad
    config1 = ConfiguracionSeguridad(
        clave="economia_password",
        valor_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # SHA256 de "password"
    )
    config2 = ConfiguracionSeguridad(
        clave="admin_password",
        valor_hash="6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090",  # SHA256 de "admin123"
    )
    db_session.add(config1)
    db_session.add(config2)
    db_session.commit()

    # Ejecutar migración
    report = migrate_passwords(db_session)

    # Verificar reporte
    assert report.total_processed == 2
    assert report.successful == 2
    assert report.failed == 0
    assert report.skipped == 0
    assert len(report.users_created) == 2

    # Verificar usuarios creados
    economia_user = db_session.query(User).filter(User.username == "economia").first()
    assert economia_user is not None
    assert economia_user.email == "economia@taller.local"
    assert (
        economia_user.password_hash
        == "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    )
    assert economia_user.is_migrated is False
    assert economia_user.is_active is True
    assert len(economia_user.roles) == 1
    assert economia_user.roles[0].name == "ADMIN"

    admin_user = db_session.query(User).filter(User.username == "admin").first()
    assert admin_user is not None
    assert admin_user.email == "admin@taller.local"
    assert (
        admin_user.password_hash
        == "6ca13d52ca70c883e0f0bb101e425a89e8624de51db2d2392593af6a84118090"
    )
    assert admin_user.is_migrated is False
    assert admin_user.is_active is True
    assert len(admin_user.roles) == 1
    assert admin_user.roles[0].name == "ADMIN"

    # Verificar registros de auditoría
    audit_logs = db_session.query(AuditLog).filter(AuditLog.action == "PASSWORD_MIGRATED").all()
    assert len(audit_logs) == 2

    for log in audit_logs:
        assert log.user_id is None  # Migración automática
        assert log.action == "PASSWORD_MIGRATED"
        assert log.resource_type == "user"
        assert log.resource_id is not None
        assert log.ip_address == "127.0.0.1"
        assert log.user_agent == "migration_script"
        assert log.details is not None
        assert "username" in log.details
        assert "clave_origen" in log.details
        assert log.details["is_migrated"] is False
        assert log.details["role"] == "ADMIN"


def test_migrate_passwords_skip_existing_user(db_session: Session):
    """
    Test: Omitir usuarios que ya existen.

    Verifica que si un usuario ya existe, se omite la migración.

    Valida: Requirements 2.1
    """
    # Crear usuario existente
    admin_role = db_session.query(Role).filter(Role.name == "ADMIN").first()
    existing_user = User(
        username="economia",
        email="economia@taller.local",
        password_hash="existing_hash",
        is_active=True,
        is_migrated=True,
    )
    existing_user.roles.append(admin_role)
    db_session.add(existing_user)
    db_session.commit()

    # Crear registro en configuracion_seguridad con mismo username
    config = ConfiguracionSeguridad(
        clave="economia_password",
        valor_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    )
    db_session.add(config)
    db_session.commit()

    # Ejecutar migración
    report = migrate_passwords(db_session)

    # Verificar que se omitió
    assert report.total_processed == 1
    assert report.successful == 0
    assert report.failed == 0
    assert report.skipped == 1

    # Verificar que el usuario existente no cambió
    user = db_session.query(User).filter(User.username == "economia").first()
    assert user.password_hash == "existing_hash"
    assert user.is_migrated is True


def test_migrate_passwords_no_admin_role(db_session: Session):
    """
    Test: Error si no existe rol ADMIN.

    Verifica que el script falla correctamente si no existe el rol ADMIN.

    Valida: Requirements 2.3
    """
    # Eliminar rol ADMIN
    db_session.query(Role).delete()
    db_session.commit()

    # Crear registro en configuracion_seguridad
    config = ConfiguracionSeguridad(
        clave="economia_password",
        valor_hash="5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",
    )
    db_session.add(config)
    db_session.commit()

    # Ejecutar migración
    report = migrate_passwords(db_session)

    # Verificar que falló antes de procesar registros
    # El script detecta la falta del rol ADMIN y sale inmediatamente
    assert report.total_processed == 0  # No llegó a contar registros
    assert report.successful == 0
    assert report.failed == 1
    assert len(report.errors) == 1
    assert "ADMIN" in report.errors[0]["error"]


def test_migrate_passwords_empty_table(db_session: Session):
    """
    Test: Migración con tabla vacía.

    Verifica que el script maneja correctamente una tabla vacía.

    Valida: Requirements 2.1
    """
    # No crear registros en configuracion_seguridad

    # Ejecutar migración
    report = migrate_passwords(db_session)

    # Verificar reporte
    assert report.total_processed == 0
    assert report.successful == 0
    assert report.failed == 0
    assert report.skipped == 0


def test_migration_report_methods():
    """
    Test: Métodos de MigrationReport.

    Verifica que el reporte funciona correctamente.

    Valida: Requirements 2.5
    """
    report = MigrationReport()

    # Agregar éxitos
    report.add_success("user1", "clave1")
    report.add_success("user2", "clave2")

    # Agregar errores
    report.add_error("clave3", "Error de prueba")

    # Agregar omitidos
    report.add_skipped("clave4", "Usuario ya existe")

    # Finalizar
    report.finalize()

    # Verificar contadores
    assert report.successful == 2
    assert report.failed == 1
    assert report.skipped == 1
    assert len(report.users_created) == 2
    assert len(report.errors) == 2

    # Verificar duración
    assert report.get_duration() >= 0

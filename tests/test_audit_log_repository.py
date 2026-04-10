"""
Tests para AuditLogRepository.

Valida que el repositorio de auditoría funcione correctamente
y que los registros sean inmutables (no update/delete).
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.audit_log import AuditLog
from app.repositorios.audit_log_repository import AuditLogRepository

# Configuración de base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Fixture que provee una sesión de base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def audit_repo(db):
    """Fixture que provee una instancia de AuditLogRepository."""
    return AuditLogRepository(db)


def test_create_audit_log(audit_repo):
    """Test: Crear un registro de auditoría."""
    # Arrange
    audit_log = AuditLog(
        user_id=1,
        action="LOGIN",
        resource_type="user",
        resource_id=1,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0",
        details={"method": "password"},
    )

    # Act
    created = audit_repo.create(audit_log)

    # Assert
    assert created.id is not None
    assert created.user_id == 1
    assert created.action == "LOGIN"
    assert created.resource_type == "user"
    assert created.resource_id == 1
    assert created.ip_address == "192.168.1.1"
    assert created.user_agent == "Mozilla/5.0"
    assert created.details == {"method": "password"}
    assert created.timestamp is not None


def test_create_audit_log_without_user(audit_repo):
    """Test: Crear un registro de auditoría sin usuario (evento anónimo)."""
    # Arrange
    audit_log = AuditLog(
        user_id=None,
        action="LOGIN_FAILED",
        resource_type=None,
        resource_id=None,
        ip_address="192.168.1.100",
        user_agent="curl/7.68.0",
        details={"username": "unknown"},
    )

    # Act
    created = audit_repo.create(audit_log)

    # Assert
    assert created.id is not None
    assert created.user_id is None
    assert created.action == "LOGIN_FAILED"
    assert created.ip_address == "192.168.1.100"


def test_get_by_user(audit_repo):
    """Test: Obtener logs de auditoría por usuario."""
    # Arrange - Crear varios logs para el usuario
    user_id = 1
    for i in range(5):
        audit_log = AuditLog(user_id=user_id, action=f"ACTION_{i}", ip_address="192.168.1.1")
        audit_repo.create(audit_log)

    # Crear logs para otro usuario
    for i in range(3):
        audit_log = AuditLog(user_id=999, action=f"OTHER_ACTION_{i}", ip_address="192.168.1.2")
        audit_repo.create(audit_log)

    # Act
    user_logs = audit_repo.get_by_user(user_id)

    # Assert
    assert len(user_logs) == 5
    assert all(log.user_id == user_id for log in user_logs)
    # Verificar orden descendente por timestamp
    timestamps = [log.timestamp for log in user_logs]
    assert timestamps == sorted(timestamps, reverse=True)


def test_get_by_user_with_pagination(audit_repo):
    """Test: Obtener logs de auditoría por usuario con paginación."""
    # Arrange - Crear 10 logs
    user_id = 1
    for i in range(10):
        audit_log = AuditLog(user_id=user_id, action=f"ACTION_{i}", ip_address="192.168.1.1")
        audit_repo.create(audit_log)

    # Act - Primera página (3 registros)
    page1 = audit_repo.get_by_user(user_id, skip=0, limit=3)
    # Segunda página (3 registros)
    page2 = audit_repo.get_by_user(user_id, skip=3, limit=3)

    # Assert
    assert len(page1) == 3
    assert len(page2) == 3
    # Verificar que no hay duplicados entre páginas
    page1_ids = {log.id for log in page1}
    page2_ids = {log.id for log in page2}
    assert page1_ids.isdisjoint(page2_ids)


def test_get_by_action(audit_repo):
    """Test: Obtener logs de auditoría por tipo de acción."""
    # Arrange - Crear logs con diferentes acciones
    for i in range(3):
        audit_repo.create(AuditLog(user_id=1, action="LOGIN", ip_address="192.168.1.1"))

    for i in range(2):
        audit_repo.create(AuditLog(user_id=1, action="LOGOUT", ip_address="192.168.1.1"))

    # Act
    login_logs = audit_repo.get_by_action("LOGIN")
    logout_logs = audit_repo.get_by_action("LOGOUT")

    # Assert
    assert len(login_logs) == 3
    assert all(log.action == "LOGIN" for log in login_logs)
    assert len(logout_logs) == 2
    assert all(log.action == "LOGOUT" for log in logout_logs)


def test_get_by_action_with_pagination(audit_repo):
    """Test: Obtener logs de auditoría por acción con paginación."""
    # Arrange - Crear 10 logs con la misma acción
    for i in range(10):
        audit_repo.create(AuditLog(user_id=1, action="CREATE", ip_address="192.168.1.1"))

    # Act
    page1 = audit_repo.get_by_action("CREATE", skip=0, limit=4)
    page2 = audit_repo.get_by_action("CREATE", skip=4, limit=4)

    # Assert
    assert len(page1) == 4
    assert len(page2) == 4


def test_get_by_date_range(audit_repo, db):
    """Test: Obtener logs de auditoría por rango de fechas."""
    # Arrange - Crear logs con diferentes timestamps
    now = datetime.now(UTC)

    # Logs de hace 5 días
    from sqlalchemy import text

    old_log = AuditLog(user_id=1, action="OLD_ACTION", ip_address="192.168.1.1")
    db.add(old_log)
    db.flush()
    # Simular timestamp antiguo
    db.execute(
        text(
            f"UPDATE audit_log SET timestamp = '{(now - timedelta(days=5)).isoformat()}' WHERE id = {old_log.id}"
        )
    )
    db.commit()

    # Logs recientes (últimas 24 horas)
    for i in range(3):
        audit_repo.create(AuditLog(user_id=1, action="RECENT_ACTION", ip_address="192.168.1.1"))

    # Act - Buscar logs de las últimas 48 horas
    start_date = now - timedelta(days=2)
    end_date = now + timedelta(hours=1)
    recent_logs = audit_repo.get_by_date_range(start_date, end_date)

    # Assert
    assert len(recent_logs) == 3
    assert all(log.action == "RECENT_ACTION" for log in recent_logs)


def test_get_by_date_range_with_pagination(audit_repo):
    """Test: Obtener logs de auditoría por rango de fechas con paginación."""
    # Arrange - Crear 10 logs
    for i in range(10):
        audit_repo.create(AuditLog(user_id=1, action="ACTION", ip_address="192.168.1.1"))

    # Act
    now = datetime.now(UTC)
    start_date = now - timedelta(hours=1)
    end_date = now + timedelta(hours=1)

    page1 = audit_repo.get_by_date_range(start_date, end_date, skip=0, limit=5)
    page2 = audit_repo.get_by_date_range(start_date, end_date, skip=5, limit=5)

    # Assert
    assert len(page1) == 5
    assert len(page2) == 5


def test_audit_log_immutability_no_update_method(audit_repo):
    """Test: Verificar que no existe método update() en el repositorio."""
    # Assert
    assert not hasattr(
        audit_repo, "update"
    ), "AuditLogRepository NO debe tener método update() - los registros son inmutables"


def test_audit_log_immutability_no_delete_method(audit_repo):
    """Test: Verificar que no existe método delete() en el repositorio."""
    # Assert
    assert not hasattr(
        audit_repo, "delete"
    ), "AuditLogRepository NO debe tener método delete() - los registros son inmutables"


def test_timestamp_is_set_automatically(audit_repo):
    """Test: Verificar que el timestamp se establece automáticamente."""
    # Arrange
    audit_log = AuditLog(user_id=1, action="TEST", ip_address="192.168.1.1")

    # Act
    created = audit_repo.create(audit_log)

    # Assert
    assert created.timestamp is not None
    # El timestamp debe ser un datetime válido
    assert isinstance(created.timestamp, datetime)
    # Verificar que el timestamp es reciente (creado hace menos de 5 segundos)
    now = datetime.now(UTC)
    # Hacer el timestamp aware si es naive para la comparación
    ts = created.timestamp if created.timestamp.tzinfo else created.timestamp.replace(tzinfo=UTC)
    time_diff = (now - ts).total_seconds()
    assert 0 <= time_diff <= 5, f"Timestamp difference is {time_diff} seconds"


def test_get_by_user_empty_result(audit_repo):
    """Test: Obtener logs de un usuario que no tiene registros."""
    # Act
    logs = audit_repo.get_by_user(user_id=999)

    # Assert
    assert logs == []


def test_get_by_action_empty_result(audit_repo):
    """Test: Obtener logs de una acción que no existe."""
    # Act
    logs = audit_repo.get_by_action("NONEXISTENT_ACTION")

    # Assert
    assert logs == []


def test_get_by_date_range_empty_result(audit_repo):
    """Test: Obtener logs en un rango de fechas sin registros."""
    # Act
    start_date = datetime.now(UTC) - timedelta(days=10)
    end_date = datetime.now(UTC) - timedelta(days=9)
    logs = audit_repo.get_by_date_range(start_date, end_date)

    # Assert
    assert logs == []


def test_create_with_all_fields(audit_repo):
    """Test: Crear un registro de auditoría con todos los campos opcionales."""
    # Arrange
    audit_log = AuditLog(
        user_id=1,
        action="TICKET_CREATE",
        resource_type="ticket",
        resource_id=123,
        ip_address="192.168.1.1",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        details={"ticket_number": "T-2026-001", "total": 5000, "status": "EN_PROCESO"},
    )

    # Act
    created = audit_repo.create(audit_log)

    # Assert
    assert created.user_id == 1
    assert created.action == "TICKET_CREATE"
    assert created.resource_type == "ticket"
    assert created.resource_id == 123
    assert created.ip_address == "192.168.1.1"
    assert created.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    assert created.details["ticket_number"] == "T-2026-001"
    assert created.details["total"] == 5000
    assert created.details["status"] == "EN_PROCESO"

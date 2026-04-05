"""
Tests para TokenBlacklistRepository.

Valida las operaciones del repositorio de tokens en lista negra.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.token_blacklist import TokenBlacklist
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.audit_log import AuditLog
from app.modelos.password_reset_token import PasswordResetToken
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository


# Configuración de base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Fixture que provee una sesión de base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Crear un usuario de prueba para las foreign keys
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$hashedpassword",
        is_active=True
    )
    db.add(user)
    db.commit()
    
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def token_blacklist_repo(db):
    """Fixture que provee una instancia de TokenBlacklistRepository."""
    return TokenBlacklistRepository(db)


def test_add_to_blacklist(token_blacklist_repo, db):
    """Test: Agregar un token a la lista negra."""
    # Arrange
    jti = "550e8400-e29b-41d4-a716-446655440000"
    token_type = "refresh"
    user_id = 1
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    reason = "logout"
    
    # Act
    result = token_blacklist_repo.add_to_blacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=expires_at,
        reason=reason
    )
    
    # Assert
    assert result.id is not None
    assert result.jti == jti
    assert result.token_type == token_type
    assert result.user_id == user_id
    # SQLite no maneja timezone-aware datetimes, comparar sin timezone
    result_expires = result.expires_at.replace(tzinfo=timezone.utc) if result.expires_at.tzinfo is None else result.expires_at
    assert abs((result_expires - expires_at).total_seconds()) < 1
    assert result.reason == reason
    assert result.blacklisted_at is not None


def test_add_to_blacklist_without_reason(token_blacklist_repo, db):
    """Test: Agregar un token a la lista negra sin especificar razón."""
    # Arrange
    jti = "550e8400-e29b-41d4-a716-446655440001"
    token_type = "access"
    user_id = 1
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    # Act
    result = token_blacklist_repo.add_to_blacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        expires_at=expires_at
    )
    
    # Assert
    assert result.id is not None
    assert result.jti == jti
    assert result.reason is None


def test_is_blacklisted_returns_true_for_blacklisted_token(token_blacklist_repo, db):
    """Test: is_blacklisted retorna True para un token en lista negra."""
    # Arrange
    jti = "550e8400-e29b-41d4-a716-446655440002"
    token_blacklist_repo.add_to_blacklist(
        jti=jti,
        token_type="refresh",
        user_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="logout"
    )
    
    # Act
    result = token_blacklist_repo.is_blacklisted(jti)
    
    # Assert
    assert result is True


def test_is_blacklisted_returns_false_for_valid_token(token_blacklist_repo):
    """Test: is_blacklisted retorna False para un token no en lista negra."""
    # Arrange
    jti = "550e8400-e29b-41d4-a716-446655440003"
    
    # Act
    result = token_blacklist_repo.is_blacklisted(jti)
    
    # Assert
    assert result is False


def test_cleanup_expired_removes_expired_tokens(token_blacklist_repo, db):
    """Test: cleanup_expired elimina tokens expirados."""
    # Arrange - Crear tokens expirados
    # Usar datetime sin timezone para compatibilidad con SQLite
    now = datetime.now()
    
    expired_jti_1 = "expired-token-1"
    expired_jti_2 = "expired-token-2"
    
    token_blacklist_repo.add_to_blacklist(
        jti=expired_jti_1,
        token_type="refresh",
        user_id=1,
        expires_at=now - timedelta(days=1),  # Expirado hace 1 día
        reason="logout"
    )
    
    token_blacklist_repo.add_to_blacklist(
        jti=expired_jti_2,
        token_type="refresh",
        user_id=1,
        expires_at=now - timedelta(hours=1),  # Expirado hace 1 hora
        reason="logout"
    )
    
    # Crear token válido (no expirado)
    valid_jti = "valid-token"
    token_blacklist_repo.add_to_blacklist(
        jti=valid_jti,
        token_type="refresh",
        user_id=1,
        expires_at=now + timedelta(days=7),  # Expira en 7 días
        reason="logout"
    )
    
    # Act
    deleted_count = token_blacklist_repo.cleanup_expired()
    
    # Assert
    assert deleted_count == 2
    
    # Verificar que los tokens expirados fueron eliminados
    assert token_blacklist_repo.is_blacklisted(expired_jti_1) is False
    assert token_blacklist_repo.is_blacklisted(expired_jti_2) is False
    
    # Verificar que el token válido sigue en la lista negra
    assert token_blacklist_repo.is_blacklisted(valid_jti) is True


def test_cleanup_expired_returns_zero_when_no_expired_tokens(token_blacklist_repo, db):
    """Test: cleanup_expired retorna 0 cuando no hay tokens expirados."""
    # Arrange - Crear solo tokens válidos
    token_blacklist_repo.add_to_blacklist(
        jti="valid-token-1",
        token_type="refresh",
        user_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="logout"
    )
    
    token_blacklist_repo.add_to_blacklist(
        jti="valid-token-2",
        token_type="refresh",
        user_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=5),
        reason="logout"
    )
    
    # Act
    deleted_count = token_blacklist_repo.cleanup_expired()
    
    # Assert
    assert deleted_count == 0
    
    # Verificar que los tokens siguen en la lista negra
    assert token_blacklist_repo.is_blacklisted("valid-token-1") is True
    assert token_blacklist_repo.is_blacklisted("valid-token-2") is True


def test_jti_uniqueness(token_blacklist_repo, db):
    """Test: No se pueden agregar tokens con el mismo jti."""
    # Arrange
    jti = "duplicate-jti"
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    # Act - Agregar primer token
    token_blacklist_repo.add_to_blacklist(
        jti=jti,
        token_type="refresh",
        user_id=1,
        expires_at=expires_at,
        reason="logout"
    )
    
    # Act & Assert - Intentar agregar token duplicado
    with pytest.raises(Exception):  # SQLAlchemy lanzará IntegrityError
        token_blacklist_repo.add_to_blacklist(
            jti=jti,
            token_type="refresh",
            user_id=1,
            expires_at=expires_at,
            reason="user_deactivated"
        )


def test_add_multiple_tokens_for_same_user(token_blacklist_repo, db):
    """Test: Se pueden agregar múltiples tokens para el mismo usuario."""
    # Arrange
    user_id = 1
    
    # Act - Agregar 3 tokens diferentes para el mismo usuario
    jti_1 = "token-1"
    jti_2 = "token-2"
    jti_3 = "token-3"
    
    token_blacklist_repo.add_to_blacklist(
        jti=jti_1,
        token_type="refresh",
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="logout"
    )
    
    token_blacklist_repo.add_to_blacklist(
        jti=jti_2,
        token_type="refresh",
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="logout"
    )
    
    token_blacklist_repo.add_to_blacklist(
        jti=jti_3,
        token_type="access",
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
        reason="user_deactivated"
    )
    
    # Assert - Todos los tokens deben estar en lista negra
    assert token_blacklist_repo.is_blacklisted(jti_1) is True
    assert token_blacklist_repo.is_blacklisted(jti_2) is True
    assert token_blacklist_repo.is_blacklisted(jti_3) is True


def test_blacklisted_at_is_set_automatically(token_blacklist_repo, db):
    """Test: El campo blacklisted_at se establece automáticamente."""
    # Arrange
    jti = "auto-timestamp-token"
    
    # Act
    result = token_blacklist_repo.add_to_blacklist(
        jti=jti,
        token_type="refresh",
        user_id=1,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="logout"
    )
    
    # Assert
    assert result.blacklisted_at is not None
    assert isinstance(result.blacklisted_at, datetime)
    
    # Verificar que el timestamp es reciente (creado hace menos de 5 segundos)
    now = datetime.now(timezone.utc)
    ts = result.blacklisted_at if result.blacklisted_at.tzinfo else result.blacklisted_at.replace(tzinfo=timezone.utc)
    time_diff = (now - ts).total_seconds()
    assert 0 <= time_diff <= 5, f"Timestamp difference is {time_diff} seconds"


def test_cleanup_expired_with_mixed_expiration_times(token_blacklist_repo, db):
    """Test: cleanup_expired maneja correctamente tokens con diferentes tiempos de expiración."""
    # Arrange
    # Usar datetime sin timezone para compatibilidad con SQLite
    now = datetime.now()
    
    # Token expirado hace mucho tiempo
    token_blacklist_repo.add_to_blacklist(
        jti="very-old-token",
        token_type="refresh",
        user_id=1,
        expires_at=now - timedelta(days=30),
        reason="logout"
    )
    
    # Token expirado recientemente (hace 1 hora para evitar race conditions)
    token_blacklist_repo.add_to_blacklist(
        jti="recently-expired-token",
        token_type="refresh",
        user_id=1,
        expires_at=now - timedelta(hours=1),
        reason="logout"
    )
    
    # Token que expira pronto (en 1 hora)
    token_blacklist_repo.add_to_blacklist(
        jti="expiring-soon-token",
        token_type="refresh",
        user_id=1,
        expires_at=now + timedelta(hours=1),
        reason="logout"
    )
    
    # Token que expira en el futuro lejano
    token_blacklist_repo.add_to_blacklist(
        jti="future-token",
        token_type="refresh",
        user_id=1,
        expires_at=now + timedelta(days=7),
        reason="logout"
    )
    
    # Act
    deleted_count = token_blacklist_repo.cleanup_expired()
    
    # Assert
    assert deleted_count == 2  # Solo los 2 tokens expirados
    
    # Verificar que los tokens expirados fueron eliminados
    assert token_blacklist_repo.is_blacklisted("very-old-token") is False
    assert token_blacklist_repo.is_blacklisted("recently-expired-token") is False
    
    # Verificar que los tokens válidos siguen en la lista negra
    assert token_blacklist_repo.is_blacklisted("expiring-soon-token") is True
    assert token_blacklist_repo.is_blacklisted("future-token") is True

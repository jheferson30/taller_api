"""
Tests para PasswordResetTokenRepository.

Valida las operaciones del repositorio de tokens de recuperación de contraseña.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.password_reset_token import PasswordResetToken
from app.modelos.user import User
from app.repositorios.password_reset_repository import PasswordResetTokenRepository

# Configuración de base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    """Fixture que provee una sesión de base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Crear usuarios de prueba para las foreign keys
    user1 = User(
        username="testuser1",
        email="test1@example.com",
        password_hash="$2b$12$hashedpassword",
        is_active=True,
    )
    user2 = User(
        username="testuser2",
        email="test2@example.com",
        password_hash="$2b$12$hashedpassword",
        is_active=True,
    )
    db.add(user1)
    db.add(user2)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def password_reset_repo(db):
    """Fixture que provee una instancia de PasswordResetTokenRepository."""
    return PasswordResetTokenRepository(db)


def test_create_token(password_reset_repo, db):
    """Test: Crear un token de recuperación de contraseña."""
    # Arrange
    token = PasswordResetToken(
        user_id=1,
        token="abc123def456",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )

    # Act
    result = password_reset_repo.create(token)

    # Assert
    assert result.id is not None
    assert result.user_id == 1
    assert result.token == "abc123def456"
    assert result.used is False
    assert result.created_at is not None


def test_get_by_token(password_reset_repo, db):
    """Test: Obtener un token por su valor."""
    # Arrange
    token = PasswordResetToken(
        user_id=1, token="findme123", expires_at=datetime.now(UTC) + timedelta(hours=1), used=False
    )
    password_reset_repo.create(token)

    # Act
    result = password_reset_repo.get_by_token("findme123")

    # Assert
    assert result is not None
    assert result.token == "findme123"
    assert result.user_id == 1


def test_get_by_token_returns_none_for_nonexistent_token(password_reset_repo):
    """Test: get_by_token retorna None para un token inexistente."""
    # Act
    result = password_reset_repo.get_by_token("nonexistent")

    # Assert
    assert result is None


def test_get_by_user_id(password_reset_repo, db):
    """Test: Obtener todos los tokens de un usuario."""
    # Arrange
    user_id = 1

    token1 = PasswordResetToken(
        user_id=user_id,
        token="token1",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )
    token2 = PasswordResetToken(
        user_id=user_id,
        token="token2",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=True,
    )
    token3 = PasswordResetToken(
        user_id=2,  # Diferente usuario
        token="token3",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )

    password_reset_repo.create(token1)
    password_reset_repo.create(token2)
    password_reset_repo.create(token3)

    # Act
    result = password_reset_repo.get_by_user_id(user_id)

    # Assert
    assert len(result) == 2
    assert all(t.user_id == user_id for t in result)
    tokens = [t.token for t in result]
    assert "token1" in tokens
    assert "token2" in tokens
    assert "token3" not in tokens


def test_get_by_user_id_returns_empty_list_for_user_without_tokens(password_reset_repo):
    """Test: get_by_user_id retorna lista vacía para usuario sin tokens."""
    # Act
    result = password_reset_repo.get_by_user_id(999)

    # Assert
    assert result == []


def test_mark_as_used(password_reset_repo, db):
    """Test: Marcar un token como usado."""
    # Arrange
    token = PasswordResetToken(
        user_id=1, token="markme", expires_at=datetime.now(UTC) + timedelta(hours=1), used=False
    )
    created_token = password_reset_repo.create(token)

    # Act
    result = password_reset_repo.mark_as_used(created_token)

    # Assert
    assert result.used is True

    # Verificar que el cambio persiste en la base de datos
    db_token = password_reset_repo.get_by_token("markme")
    assert db_token.used is True


def test_invalidate_user_tokens(password_reset_repo, db):
    """Test: Invalidar todos los tokens de un usuario."""
    # Arrange
    user_id = 1

    # Crear tokens no usados
    token1 = PasswordResetToken(
        user_id=user_id,
        token="token1",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )
    token2 = PasswordResetToken(
        user_id=user_id,
        token="token2",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )

    # Crear token ya usado (no debe ser afectado)
    token3 = PasswordResetToken(
        user_id=user_id,
        token="token3",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=True,
    )

    # Crear token de otro usuario (no debe ser afectado)
    token4 = PasswordResetToken(
        user_id=2, token="token4", expires_at=datetime.now(UTC) + timedelta(hours=1), used=False
    )

    password_reset_repo.create(token1)
    password_reset_repo.create(token2)
    password_reset_repo.create(token3)
    password_reset_repo.create(token4)

    # Act
    count = password_reset_repo.invalidate_user_tokens(user_id)

    # Assert
    assert count == 2  # Solo token1 y token2

    # Verificar que los tokens fueron marcados como usados
    assert password_reset_repo.get_by_token("token1").used is True
    assert password_reset_repo.get_by_token("token2").used is True

    # Verificar que token3 sigue usado (no cambió)
    assert password_reset_repo.get_by_token("token3").used is True

    # Verificar que token4 de otro usuario no fue afectado
    assert password_reset_repo.get_by_token("token4").used is False


def test_invalidate_user_tokens_returns_zero_when_no_unused_tokens(password_reset_repo, db):
    """Test: invalidate_user_tokens retorna 0 cuando no hay tokens sin usar."""
    # Arrange
    user_id = 1

    # Crear solo tokens ya usados
    token1 = PasswordResetToken(
        user_id=user_id, token="used1", expires_at=datetime.now(UTC) + timedelta(hours=1), used=True
    )
    token2 = PasswordResetToken(
        user_id=user_id, token="used2", expires_at=datetime.now(UTC) + timedelta(hours=1), used=True
    )

    password_reset_repo.create(token1)
    password_reset_repo.create(token2)

    # Act
    count = password_reset_repo.invalidate_user_tokens(user_id)

    # Assert
    assert count == 0


def test_cleanup_expired(password_reset_repo, db):
    """Test: Eliminar tokens expirados."""
    # Arrange
    now = datetime.now()

    # Token expirado hace 1 día
    expired_token1 = PasswordResetToken(
        user_id=1, token="expired1", expires_at=now - timedelta(days=1), used=False
    )

    # Token expirado hace 1 hora
    expired_token2 = PasswordResetToken(
        user_id=1, token="expired2", expires_at=now - timedelta(hours=1), used=True
    )

    # Token válido (expira en 1 hora)
    valid_token = PasswordResetToken(
        user_id=1, token="valid", expires_at=now + timedelta(hours=1), used=False
    )

    password_reset_repo.create(expired_token1)
    password_reset_repo.create(expired_token2)
    password_reset_repo.create(valid_token)

    # Act
    count = password_reset_repo.cleanup_expired()

    # Assert
    assert count == 2

    # Verificar que los tokens expirados fueron eliminados
    assert password_reset_repo.get_by_token("expired1") is None
    assert password_reset_repo.get_by_token("expired2") is None

    # Verificar que el token válido sigue existiendo
    assert password_reset_repo.get_by_token("valid") is not None


def test_cleanup_expired_returns_zero_when_no_expired_tokens(password_reset_repo, db):
    """Test: cleanup_expired retorna 0 cuando no hay tokens expirados."""
    # Arrange
    now = datetime.now()

    token1 = PasswordResetToken(
        user_id=1, token="valid1", expires_at=now + timedelta(hours=1), used=False
    )
    token2 = PasswordResetToken(
        user_id=1, token="valid2", expires_at=now + timedelta(days=1), used=False
    )

    password_reset_repo.create(token1)
    password_reset_repo.create(token2)

    # Act
    count = password_reset_repo.cleanup_expired()

    # Assert
    assert count == 0

    # Verificar que los tokens siguen existiendo
    assert password_reset_repo.get_by_token("valid1") is not None
    assert password_reset_repo.get_by_token("valid2") is not None


def test_token_uniqueness(password_reset_repo, db):
    """Test: No se pueden crear tokens con el mismo valor."""
    # Arrange
    token_value = "duplicate"

    token1 = PasswordResetToken(
        user_id=1, token=token_value, expires_at=datetime.now(UTC) + timedelta(hours=1), used=False
    )
    password_reset_repo.create(token1)

    # Act & Assert
    token2 = PasswordResetToken(
        user_id=2,  # Diferente usuario
        token=token_value,  # Mismo token
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )

    with pytest.raises(Exception):  # SQLAlchemy lanzará IntegrityError
        password_reset_repo.create(token2)


def test_created_at_is_set_automatically(password_reset_repo, db):
    """Test: El campo created_at se establece automáticamente."""
    # Arrange
    token = PasswordResetToken(
        user_id=1, token="autotime", expires_at=datetime.now(UTC) + timedelta(hours=1), used=False
    )

    # Act
    result = password_reset_repo.create(token)

    # Assert
    assert result.created_at is not None
    assert isinstance(result.created_at, datetime)

    # Verificar que el timestamp es reciente (creado hace menos de 5 segundos)
    now = datetime.now(UTC)
    ts = result.created_at if result.created_at.tzinfo else result.created_at.replace(tzinfo=UTC)
    time_diff = (now - ts).total_seconds()
    assert 0 <= time_diff <= 5, f"Timestamp difference is {time_diff} seconds"


def test_multiple_tokens_for_same_user(password_reset_repo, db):
    """Test: Un usuario puede tener múltiples tokens de recuperación."""
    # Arrange
    user_id = 1

    token1 = PasswordResetToken(
        user_id=user_id,
        token="multi1",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )
    token2 = PasswordResetToken(
        user_id=user_id,
        token="multi2",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=False,
    )
    token3 = PasswordResetToken(
        user_id=user_id,
        token="multi3",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        used=True,
    )

    # Act
    password_reset_repo.create(token1)
    password_reset_repo.create(token2)
    password_reset_repo.create(token3)

    # Assert
    tokens = password_reset_repo.get_by_user_id(user_id)
    assert len(tokens) == 3


def test_cleanup_expired_with_mixed_expiration_times(password_reset_repo, db):
    """Test: cleanup_expired maneja correctamente tokens con diferentes tiempos de expiración."""
    # Arrange
    now = datetime.now()

    # Token expirado hace mucho tiempo
    password_reset_repo.create(
        PasswordResetToken(
            user_id=1, token="very-old", expires_at=now - timedelta(days=30), used=False
        )
    )

    # Token expirado recientemente
    password_reset_repo.create(
        PasswordResetToken(
            user_id=1, token="recently-expired", expires_at=now - timedelta(hours=2), used=False
        )
    )

    # Token que expira pronto
    password_reset_repo.create(
        PasswordResetToken(
            user_id=1, token="expiring-soon", expires_at=now + timedelta(minutes=30), used=False
        )
    )

    # Token que expira en el futuro
    password_reset_repo.create(
        PasswordResetToken(
            user_id=1, token="future", expires_at=now + timedelta(hours=1), used=False
        )
    )

    # Act
    count = password_reset_repo.cleanup_expired()

    # Assert
    assert count == 2  # Solo los 2 tokens expirados

    # Verificar que los tokens expirados fueron eliminados
    assert password_reset_repo.get_by_token("very-old") is None
    assert password_reset_repo.get_by_token("recently-expired") is None

    # Verificar que los tokens válidos siguen existiendo
    assert password_reset_repo.get_by_token("expiring-soon") is not None
    assert password_reset_repo.get_by_token("future") is not None

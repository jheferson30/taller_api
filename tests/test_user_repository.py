"""
Tests unitarios para UserRepository.

Valida las operaciones CRUD del repositorio de usuarios.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.user import User
from app.repositorios.user_repository import UserRepository


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos en memoria para tests."""
    engine = create_engine("sqlite:///:memory:")
    # Importar todos los modelos para que SQLAlchemy los registre
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def user_repo(db_session):
    """Crea una instancia de UserRepository para tests."""
    return UserRepository(db_session)


@pytest.fixture
def sample_user():
    """Crea un usuario de ejemplo para tests."""
    return User(
        username="testuser",
        email="test@example.com",
        password_hash="$2b$12$hashedpassword",
        is_active=True,
        is_migrated=False,
    )


def test_create_user(user_repo, sample_user):
    """Test: crear un usuario retorna el usuario con ID asignado."""
    created_user = user_repo.create(sample_user)

    assert created_user.id is not None
    assert created_user.username == "testuser"
    assert created_user.email == "test@example.com"
    assert created_user.is_active is True


def test_get_by_id(user_repo, sample_user):
    """Test: obtener usuario por ID retorna el usuario correcto."""
    created_user = user_repo.create(sample_user)

    retrieved_user = user_repo.get_by_id(created_user.id)

    assert retrieved_user is not None
    assert retrieved_user.id == created_user.id
    assert retrieved_user.username == "testuser"


def test_get_by_id_not_found(user_repo):
    """Test: obtener usuario por ID inexistente retorna None."""
    retrieved_user = user_repo.get_by_id(9999)

    assert retrieved_user is None


def test_get_by_username(user_repo, sample_user):
    """Test: obtener usuario por username retorna el usuario correcto."""
    user_repo.create(sample_user)

    retrieved_user = user_repo.get_by_username("testuser")

    assert retrieved_user is not None
    assert retrieved_user.username == "testuser"
    assert retrieved_user.email == "test@example.com"


def test_get_by_username_not_found(user_repo):
    """Test: obtener usuario por username inexistente retorna None."""
    retrieved_user = user_repo.get_by_username("nonexistent")

    assert retrieved_user is None


def test_get_by_email(user_repo, sample_user):
    """Test: obtener usuario por email retorna el usuario correcto."""
    user_repo.create(sample_user)

    retrieved_user = user_repo.get_by_email("test@example.com")

    assert retrieved_user is not None
    assert retrieved_user.email == "test@example.com"
    assert retrieved_user.username == "testuser"


def test_get_by_email_not_found(user_repo):
    """Test: obtener usuario por email inexistente retorna None."""
    retrieved_user = user_repo.get_by_email("nonexistent@example.com")

    assert retrieved_user is None


def test_get_all_active_users_only(user_repo):
    """Test: get_all por defecto solo retorna usuarios activos."""
    # Crear usuario activo
    active_user = User(
        username="active", email="active@example.com", password_hash="hash", is_active=True
    )
    user_repo.create(active_user)

    # Crear usuario inactivo
    inactive_user = User(
        username="inactive", email="inactive@example.com", password_hash="hash", is_active=False
    )
    user_repo.create(inactive_user)

    users = user_repo.get_all()

    assert len(users) == 1
    assert users[0].username == "active"


def test_get_all_include_inactive(user_repo):
    """Test: get_all con include_inactive=True retorna todos los usuarios."""
    # Crear usuario activo
    active_user = User(
        username="active", email="active@example.com", password_hash="hash", is_active=True
    )
    user_repo.create(active_user)

    # Crear usuario inactivo
    inactive_user = User(
        username="inactive", email="inactive@example.com", password_hash="hash", is_active=False
    )
    user_repo.create(inactive_user)

    users = user_repo.get_all(include_inactive=True)

    assert len(users) == 2


def test_get_all_pagination(user_repo):
    """Test: get_all respeta parámetros de paginación."""
    # Crear 5 usuarios
    for i in range(5):
        user = User(
            username=f"user{i}", email=f"user{i}@example.com", password_hash="hash", is_active=True
        )
        user_repo.create(user)

    # Obtener página 1 (primeros 2)
    page1 = user_repo.get_all(skip=0, limit=2)
    assert len(page1) == 2

    # Obtener página 2 (siguientes 2)
    page2 = user_repo.get_all(skip=2, limit=2)
    assert len(page2) == 2

    # Verificar que son usuarios diferentes
    assert page1[0].id != page2[0].id


def test_update_user(user_repo, sample_user):
    """Test: actualizar usuario persiste los cambios."""
    created_user = user_repo.create(sample_user)

    # Modificar usuario
    created_user.email = "newemail@example.com"
    updated_user = user_repo.update(created_user)

    # Verificar cambios
    assert updated_user.email == "newemail@example.com"

    # Verificar que se persistió en DB
    retrieved_user = user_repo.get_by_id(created_user.id)
    assert retrieved_user.email == "newemail@example.com"


def test_delete_user_soft_delete(user_repo, sample_user):
    """Test: delete marca usuario como inactivo (soft delete)."""
    created_user = user_repo.create(sample_user)
    assert created_user.is_active is True

    user_repo.delete(created_user.id)

    # Verificar que el usuario existe pero está inactivo
    retrieved_user = user_repo.get_by_id(created_user.id)
    assert retrieved_user is not None
    assert retrieved_user.is_active is False


def test_delete_nonexistent_user(user_repo):
    """Test: delete de usuario inexistente no causa error."""
    # No debe lanzar excepción
    user_repo.delete(9999)


def test_username_uniqueness(user_repo, sample_user):
    """Test: crear usuarios con username duplicado causa error de integridad."""
    user_repo.create(sample_user)

    # Intentar crear otro usuario con mismo username
    duplicate_user = User(
        username="testuser",  # Mismo username
        email="different@example.com",
        password_hash="hash",
        is_active=True,
    )

    with pytest.raises(Exception):  # SQLAlchemy lanzará IntegrityError
        user_repo.create(duplicate_user)


def test_email_uniqueness(user_repo, sample_user):
    """Test: crear usuarios con email duplicado causa error de integridad."""
    user_repo.create(sample_user)

    # Intentar crear otro usuario con mismo email
    duplicate_user = User(
        username="different",
        email="test@example.com",  # Mismo email
        password_hash="hash",
        is_active=True,
    )

    with pytest.raises(Exception):  # SQLAlchemy lanzará IntegrityError
        user_repo.create(duplicate_user)

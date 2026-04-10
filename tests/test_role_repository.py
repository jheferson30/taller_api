"""
Tests unitarios para RoleRepository.

Valida las operaciones CRUD del repositorio de roles.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.role import Role
from app.repositorios.role_repository import RoleRepository


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos en memoria para tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def role_repo(db_session):
    """Crea una instancia de RoleRepository para tests."""
    return RoleRepository(db_session)


@pytest.fixture
def sample_role():
    """Crea un rol de ejemplo para tests."""
    return Role(name="ADMIN", description="Administrador del sistema")


def test_create_role(role_repo, sample_role):
    """Test: crear un rol retorna el rol con ID asignado."""
    created_role = role_repo.create(sample_role)

    assert created_role.id is not None
    assert created_role.name == "ADMIN"
    assert created_role.description == "Administrador del sistema"
    assert created_role.created_at is not None


def test_get_by_id(role_repo, sample_role):
    """Test: obtener rol por ID retorna el rol correcto."""
    created_role = role_repo.create(sample_role)

    retrieved_role = role_repo.get_by_id(created_role.id)

    assert retrieved_role is not None
    assert retrieved_role.id == created_role.id
    assert retrieved_role.name == "ADMIN"


def test_get_by_id_not_found(role_repo):
    """Test: obtener rol por ID inexistente retorna None."""
    retrieved_role = role_repo.get_by_id(9999)

    assert retrieved_role is None


def test_get_by_name(role_repo, sample_role):
    """Test: obtener rol por nombre retorna el rol correcto."""
    role_repo.create(sample_role)

    retrieved_role = role_repo.get_by_name("ADMIN")

    assert retrieved_role is not None
    assert retrieved_role.name == "ADMIN"
    assert retrieved_role.description == "Administrador del sistema"


def test_get_by_name_not_found(role_repo):
    """Test: obtener rol por nombre inexistente retorna None."""
    retrieved_role = role_repo.get_by_name("NONEXISTENT")

    assert retrieved_role is None


def test_get_all(role_repo):
    """Test: get_all retorna todos los roles."""
    # Crear múltiples roles
    roles_data = [
        ("ADMIN", "Administrador del sistema"),
        ("MECANICO", "Mecánico del taller"),
        ("RECEPCIONISTA", "Recepcionista"),
        ("SOLO_LECTURA", "Usuario de solo lectura"),
    ]

    for name, description in roles_data:
        role = Role(name=name, description=description)
        role_repo.create(role)

    roles = role_repo.get_all()

    assert len(roles) == 4
    role_names = [role.name for role in roles]
    assert "ADMIN" in role_names
    assert "MECANICO" in role_names
    assert "RECEPCIONISTA" in role_names
    assert "SOLO_LECTURA" in role_names


def test_get_all_pagination(role_repo):
    """Test: get_all respeta parámetros de paginación."""
    # Crear 5 roles
    for i in range(5):
        role = Role(name=f"ROLE{i}", description=f"Role {i}")
        role_repo.create(role)

    # Obtener página 1 (primeros 2)
    page1 = role_repo.get_all(skip=0, limit=2)
    assert len(page1) == 2

    # Obtener página 2 (siguientes 2)
    page2 = role_repo.get_all(skip=2, limit=2)
    assert len(page2) == 2

    # Verificar que son roles diferentes
    assert page1[0].id != page2[0].id


def test_update_role(role_repo, sample_role):
    """Test: actualizar rol persiste los cambios."""
    created_role = role_repo.create(sample_role)

    # Modificar rol
    created_role.description = "Administrador con permisos completos"
    updated_role = role_repo.update(created_role)

    # Verificar cambios
    assert updated_role.description == "Administrador con permisos completos"

    # Verificar que se persistió en DB
    retrieved_role = role_repo.get_by_id(created_role.id)
    assert retrieved_role.description == "Administrador con permisos completos"


def test_delete_role(role_repo, sample_role):
    """Test: delete elimina el rol de la base de datos."""
    created_role = role_repo.create(sample_role)
    role_id = created_role.id

    role_repo.delete(role_id)

    # Verificar que el rol ya no existe
    retrieved_role = role_repo.get_by_id(role_id)
    assert retrieved_role is None


def test_delete_nonexistent_role(role_repo):
    """Test: delete de rol inexistente no causa error."""
    # No debe lanzar excepción
    role_repo.delete(9999)


def test_name_uniqueness(role_repo, sample_role):
    """Test: crear roles con nombre duplicado causa error de integridad."""
    role_repo.create(sample_role)

    # Intentar crear otro rol con mismo nombre
    duplicate_role = Role(
        name="ADMIN",  # Mismo nombre
        description="Otra descripción",
    )

    with pytest.raises(Exception):  # SQLAlchemy lanzará IntegrityError
        role_repo.create(duplicate_role)


def test_create_role_without_description(role_repo):
    """Test: crear rol sin descripción es válido."""
    role = Role(name="MECANICO")
    created_role = role_repo.create(role)

    assert created_role.id is not None
    assert created_role.name == "MECANICO"
    assert created_role.description is None


def test_get_all_empty(role_repo):
    """Test: get_all retorna lista vacía cuando no hay roles."""
    roles = role_repo.get_all()

    assert roles == []


def test_multiple_operations(role_repo):
    """Test: múltiples operaciones CRUD en secuencia funcionan correctamente."""
    # Crear
    role1 = Role(name="ADMIN", description="Admin")
    created1 = role_repo.create(role1)

    role2 = Role(name="MECANICO", description="Mechanic")
    created2 = role_repo.create(role2)

    # Leer
    all_roles = role_repo.get_all()
    assert len(all_roles) == 2

    # Actualizar
    created1.description = "Administrator"
    role_repo.update(created1)

    # Verificar actualización
    updated = role_repo.get_by_name("ADMIN")
    assert updated.description == "Administrator"

    # Eliminar
    role_repo.delete(created2.id)

    # Verificar eliminación
    remaining_roles = role_repo.get_all()
    assert len(remaining_roles) == 1
    assert remaining_roles[0].name == "ADMIN"

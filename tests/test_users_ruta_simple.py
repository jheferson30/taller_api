"""
Tests simplificados para endpoints de gestión de usuarios.
Valida la funcionalidad básica sin depender del middleware completo.
"""


import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.user_repository import UserRepository
from app.seguridad.password_hasher import PasswordHasher
from app.servicios.audit_service import AuditService
from app.servicios.user_service import DuplicateError, UserService, ValidationError

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Fixture que crea una sesión de base de datos limpia para cada test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def password_hasher():
    """Fixture que crea un hasher de contraseñas."""
    return PasswordHasher()


@pytest.fixture
def user_service(db_session, password_hasher):
    """Fixture que crea un UserService."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)
    token_blacklist_repo = TokenBlacklistRepository(db_session)
    audit_log_repo = AuditLogRepository(db_session)
    audit_service = AuditService(audit_log_repo)

    return UserService(
        user_repo=user_repo,
        role_repo=role_repo,
        token_blacklist_repo=token_blacklist_repo,
        password_hasher=password_hasher,
        audit_service=audit_service,
        db=db_session,
    )


@pytest.fixture
def admin_user(db_session, password_hasher):
    """Fixture que crea un usuario administrador."""
    # Crear rol ADMIN
    admin_role = Role(name="ADMIN", description="Administrator")
    db_session.add(admin_role)
    db_session.commit()

    # Crear usuario admin
    admin = User(
        username="admin",
        email="admin@test.com",
        password_hash=password_hasher.hash_password("Admin123"),
        is_active=True,
        is_migrated=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    # Asignar rol
    user_role = UserRole(user_id=admin.id, role_id=admin_role.id)
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(admin)

    return admin


class TestUserServiceCreateUser:
    """Tests para UserService.create_user()"""

    def test_create_user_success(self, db_session, user_service, admin_user):
        """Test: Crear usuario exitosamente."""
        # Crear rol USER
        user_role = Role(name="USER", description="Regular user")
        db_session.add(user_role)
        db_session.commit()

        user = user_service.create_user(
            username="newuser",
            email="newuser@test.com",
            password="NewUser123",
            roles=["USER"],
            created_by=admin_user.id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@test.com"
        assert user.is_active is True
        assert len(user.roles) == 1
        assert user.roles[0].name == "USER"

    def test_create_user_duplicate_username(self, db_session, user_service, admin_user):
        """Test: No se puede crear usuario con username duplicado."""
        with pytest.raises(DuplicateError) as exc_info:
            user_service.create_user(
                username="admin",  # Ya existe
                email="another@test.com",
                password="Test123",
                roles=["ADMIN"],
                created_by=admin_user.id,
                ip_address="127.0.0.1",
                user_agent="test-agent",
            )

        assert "username" in str(exc_info.value).lower()

    def test_create_user_weak_password(self, db_session, user_service, admin_user):
        """Test: Contraseña débil es rechazada."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@test.com",
                password="weak",  # No cumple requisitos
                roles=["ADMIN"],
                created_by=admin_user.id,
                ip_address="127.0.0.1",
                user_agent="test-agent",
            )

        assert "contraseña" in str(exc_info.value).lower()


class TestUserServiceUpdateRoles:
    """Tests para UserService.update_user_roles()"""

    def test_update_roles_success(self, db_session, user_service, admin_user):
        """Test: Actualizar roles exitosamente."""
        # Crear rol MECANICO
        mecanico_role = Role(name="MECANICO", description="Mechanic")
        db_session.add(mecanico_role)
        db_session.commit()

        user = user_service.update_user_roles(
            user_id=admin_user.id,
            roles=["ADMIN", "MECANICO"],
            updated_by=admin_user.id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        role_names = [role.name for role in user.roles]
        assert "ADMIN" in role_names
        assert "MECANICO" in role_names


class TestUserServiceDeactivateUser:
    """Tests para UserService.deactivate_user()"""

    def test_deactivate_user_success(self, db_session, user_service, admin_user):
        """Test: Desactivar usuario exitosamente."""
        user_service.deactivate_user(
            user_id=admin_user.id,
            deactivated_by=admin_user.id,
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        db_session.refresh(admin_user)
        assert admin_user.is_active is False


class TestUserServiceChangePassword:
    """Tests para UserService.change_password()"""

    def test_change_password_success(self, db_session, user_service, admin_user, password_hasher):
        """Test: Cambiar contraseña exitosamente."""
        user_service.change_password(
            user_id=admin_user.id,
            current_password="Admin123",
            new_password="NewPassword123",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )

        db_session.refresh(admin_user)
        assert password_hasher.verify_password("NewPassword123", admin_user.password_hash)

    def test_change_password_wrong_current(self, db_session, user_service, admin_user):
        """Test: Contraseña actual incorrecta es rechazada."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.change_password(
                user_id=admin_user.id,
                current_password="WrongPassword",
                new_password="NewPassword123",
                ip_address="127.0.0.1",
                user_agent="test-agent",
            )

        assert "incorrecta" in str(exc_info.value).lower()

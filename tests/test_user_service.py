"""
Tests para UserService.

Verifica la funcionalidad de gestión de usuarios: creación, actualización de roles,
desactivación y cambio de contraseña.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.audit_log import AuditLog
from app.repositorios.user_repository import UserRepository
from app.repositorios.role_repository import RoleRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.audit_log_repository import AuditLogRepository
from app.servicios.user_service import UserService, ValidationError, DuplicateError
from app.servicios.audit_service import AuditService
from app.seguridad.password_hasher import PasswordHasher


# Configuración de base de datos en memoria para tests
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
def user_repo(db_session):
    """Crea un repositorio de usuarios."""
    return UserRepository(db_session)


@pytest.fixture
def role_repo(db_session):
    """Crea un repositorio de roles."""
    return RoleRepository(db_session)


@pytest.fixture
def token_blacklist_repo(db_session):
    """Crea un repositorio de tokens en lista negra."""
    return TokenBlacklistRepository(db_session)


@pytest.fixture
def audit_log_repo(db_session):
    """Crea un repositorio de audit logs."""
    return AuditLogRepository(db_session)


@pytest.fixture
def password_hasher():
    """Crea un hasher de contraseñas."""
    return PasswordHasher(cost_factor=4)  # Cost factor bajo para tests rápidos


@pytest.fixture
def audit_service(audit_log_repo):
    """Crea un servicio de auditoría."""
    return AuditService(audit_log_repo)


@pytest.fixture
def user_service(
    user_repo,
    role_repo,
    token_blacklist_repo,
    password_hasher,
    audit_service,
    db_session
):
    """Crea un servicio de usuarios."""
    return UserService(
        user_repo,
        role_repo,
        token_blacklist_repo,
        password_hasher,
        audit_service,
        db_session
    )


@pytest.fixture
def sample_roles(db_session, role_repo):
    """Crea roles de prueba."""
    roles = [
        Role(name="ADMIN", description="Administrador del sistema"),
        Role(name="MECANICO", description="Mecánico del taller"),
        Role(name="RECEPCIONISTA", description="Recepcionista"),
        Role(name="SOLO_LECTURA", description="Solo lectura")
    ]
    
    for role in roles:
        role_repo.create(role)
    
    return roles


@pytest.fixture
def sample_admin_user(db_session, user_repo, password_hasher):
    """Crea un usuario administrador de prueba."""
    user = User(
        username="admin",
        email="admin@example.com",
        password_hash=password_hasher.hash_password("Admin123"),
        is_active=True,
        is_migrated=True
    )
    return user_repo.create(user)


@pytest.fixture
def sample_user(db_session, user_repo, role_repo, sample_roles, password_hasher):
    """Crea un usuario de prueba con rol MECANICO."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hasher.hash_password("Test123"),
        is_active=True,
        is_migrated=True
    )
    user = user_repo.create(user)
    
    # Asignar rol MECANICO
    mecanico_role = role_repo.get_by_name("MECANICO")
    user_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
    db_session.add(user_role)
    db_session.commit()
    db_session.refresh(user)
    
    return user


class TestCreateUser:
    """Tests para el método create_user()."""
    
    def test_create_user_success(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        user_repo,
        password_hasher
    ):
        """Test: Crear usuario con datos válidos retorna usuario creado."""
        user = user_service.create_user(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            roles=["MECANICO"],
            created_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert user.id is not None
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_migrated is True
        
        # Verificar que la contraseña fue hasheada correctamente
        assert password_hasher.verify_password("Password123", user.password_hash)
        
        # Verificar que el rol fue asignado
        assert len(user.roles) == 1
        assert user.roles[0].name == "MECANICO"
    
    def test_create_user_with_multiple_roles(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario con múltiples roles."""
        user = user_service.create_user(
            username="multiuser",
            email="multi@example.com",
            password="Password123",
            roles=["MECANICO", "RECEPCIONISTA"],
            created_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert len(user.roles) == 2
        role_names = {role.name for role in user.roles}
        assert "MECANICO" in role_names
        assert "RECEPCIONISTA" in role_names
    
    def test_create_user_duplicate_username(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user
    ):
        """Test: Crear usuario con username duplicado falla."""
        with pytest.raises(DuplicateError) as exc_info:
            user_service.create_user(
                username="testuser",  # Ya existe
                email="another@example.com",
                password="Password123",
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "username" in str(exc_info.value).lower()
        assert "testuser" in str(exc_info.value)
    
    def test_create_user_duplicate_email(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user
    ):
        """Test: Crear usuario con email duplicado falla."""
        with pytest.raises(DuplicateError) as exc_info:
            user_service.create_user(
                username="anotheruser",
                email="test@example.com",  # Ya existe
                password="Password123",
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "email" in str(exc_info.value).lower()
        assert "test@example.com" in str(exc_info.value)
    
    def test_create_user_invalid_email(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario con email inválido falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="invalid-email",
                password="Password123",
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "email" in str(exc_info.value).lower()
        assert "formato" in str(exc_info.value).lower()
    
    def test_create_user_weak_password_too_short(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario con contraseña corta falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="Pass1",  # Solo 5 caracteres
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña" in str(exc_info.value).lower()
        assert "8 caracteres" in str(exc_info.value).lower()
    
    def test_create_user_weak_password_no_uppercase(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario sin mayúscula falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="password123",  # Sin mayúscula
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña" in str(exc_info.value).lower()
        assert "mayúscula" in str(exc_info.value).lower()
    
    def test_create_user_weak_password_no_lowercase(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario sin minúscula falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="PASSWORD123",  # Sin minúscula
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña" in str(exc_info.value).lower()
        assert "minúscula" in str(exc_info.value).lower()
    
    def test_create_user_weak_password_no_digit(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario sin número falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="Password",  # Sin número
                roles=["MECANICO"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña" in str(exc_info.value).lower()
        assert "número" in str(exc_info.value).lower()
    
    def test_create_user_invalid_role(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Crear usuario con rol inexistente falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.create_user(
                username="newuser",
                email="newuser@example.com",
                password="Password123",
                roles=["INVALID_ROLE"],
                created_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "rol" in str(exc_info.value).lower()
        assert "INVALID_ROLE" in str(exc_info.value)
    
    def test_create_user_logs_audit_event(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        audit_log_repo
    ):
        """Test: Crear usuario registra evento en audit log."""
        user = user_service.create_user(
            username="newuser",
            email="newuser@example.com",
            password="Password123",
            roles=["MECANICO"],
            created_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que se registró el evento
        logs = audit_log_repo.get_by_user(sample_admin_user.id)
        assert len(logs) > 0
        
        log = logs[0]
        assert log.action == "USER_CREATE"
        assert log.resource_type == "user"
        assert log.resource_id == user.id
        assert log.ip_address == "127.0.0.1"
        assert log.details["username"] == "newuser"


class TestUpdateUserRoles:
    """Tests para el método update_user_roles()."""
    
    def test_update_user_roles_success(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user
    ):
        """Test: Actualizar roles de usuario exitosamente."""
        # Usuario tiene rol MECANICO, cambiar a ADMIN
        user = user_service.update_user_roles(
            user_id=sample_user.id,
            roles=["ADMIN"],
            updated_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert len(user.roles) == 1
        assert user.roles[0].name == "ADMIN"
    
    def test_update_user_roles_multiple(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user
    ):
        """Test: Actualizar a múltiples roles."""
        user = user_service.update_user_roles(
            user_id=sample_user.id,
            roles=["ADMIN", "MECANICO"],
            updated_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert len(user.roles) == 2
        role_names = {role.name for role in user.roles}
        assert "ADMIN" in role_names
        assert "MECANICO" in role_names
    
    def test_update_user_roles_nonexistent_user(
        self,
        user_service,
        sample_roles,
        sample_admin_user
    ):
        """Test: Actualizar roles de usuario inexistente falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.update_user_roles(
                user_id=99999,
                roles=["ADMIN"],
                updated_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "usuario" in str(exc_info.value).lower()
        assert "no existe" in str(exc_info.value).lower()
    
    def test_update_user_roles_invalid_role(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user
    ):
        """Test: Actualizar con rol inexistente falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.update_user_roles(
                user_id=sample_user.id,
                roles=["INVALID_ROLE"],
                updated_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "rol" in str(exc_info.value).lower()
        assert "INVALID_ROLE" in str(exc_info.value)
    
    def test_update_user_roles_logs_audit_event(
        self,
        user_service,
        sample_roles,
        sample_admin_user,
        sample_user,
        audit_log_repo
    ):
        """Test: Actualizar roles registra evento en audit log."""
        user_service.update_user_roles(
            user_id=sample_user.id,
            roles=["ADMIN"],
            updated_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que se registró el evento
        logs = audit_log_repo.get_by_user(sample_admin_user.id)
        assert len(logs) > 0
        
        log = logs[0]
        assert log.action == "ROLE_CHANGE"
        assert log.resource_type == "user"
        assert log.resource_id == sample_user.id
        assert "old_roles" in log.details
        assert "new_roles" in log.details


class TestDeactivateUser:
    """Tests para el método deactivate_user()."""
    
    def test_deactivate_user_success(
        self,
        user_service,
        sample_admin_user,
        sample_user,
        user_repo
    ):
        """Test: Desactivar usuario exitosamente."""
        user_service.deactivate_user(
            user_id=sample_user.id,
            deactivated_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que el usuario fue desactivado
        user = user_repo.get_by_id(sample_user.id)
        assert user.is_active is False
    
    def test_deactivate_user_nonexistent(
        self,
        user_service,
        sample_admin_user
    ):
        """Test: Desactivar usuario inexistente falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.deactivate_user(
                user_id=99999,
                deactivated_by=sample_admin_user.id,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "usuario" in str(exc_info.value).lower()
        assert "no existe" in str(exc_info.value).lower()
    
    def test_deactivate_user_logs_audit_event(
        self,
        user_service,
        sample_admin_user,
        sample_user,
        audit_log_repo
    ):
        """Test: Desactivar usuario registra evento en audit log."""
        user_service.deactivate_user(
            user_id=sample_user.id,
            deactivated_by=sample_admin_user.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que se registró el evento
        logs = audit_log_repo.get_by_user(sample_admin_user.id)
        assert len(logs) > 0
        
        log = logs[0]
        assert log.action == "USER_DEACTIVATE"
        assert log.resource_type == "user"
        assert log.resource_id == sample_user.id
        assert log.details["username"] == sample_user.username


class TestChangePassword:
    """Tests para el método change_password()."""
    
    def test_change_password_success(
        self,
        user_service,
        sample_user,
        user_repo,
        password_hasher
    ):
        """Test: Cambiar contraseña exitosamente."""
        user_service.change_password(
            user_id=sample_user.id,
            current_password="Test123",
            new_password="NewPassword123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que la contraseña cambió
        user = user_repo.get_by_id(sample_user.id)
        assert password_hasher.verify_password("NewPassword123", user.password_hash)
        assert not password_hasher.verify_password("Test123", user.password_hash)
    
    def test_change_password_wrong_current(
        self,
        user_service,
        sample_user
    ):
        """Test: Cambiar contraseña con contraseña actual incorrecta falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.change_password(
                user_id=sample_user.id,
                current_password="WrongPassword",
                new_password="NewPassword123",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña actual" in str(exc_info.value).lower()
        assert "incorrecta" in str(exc_info.value).lower()
    
    def test_change_password_weak_new_password(
        self,
        user_service,
        sample_user
    ):
        """Test: Cambiar a contraseña débil falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.change_password(
                user_id=sample_user.id,
                current_password="Test123",
                new_password="weak",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "contraseña" in str(exc_info.value).lower()
    
    def test_change_password_nonexistent_user(
        self,
        user_service
    ):
        """Test: Cambiar contraseña de usuario inexistente falla."""
        with pytest.raises(ValidationError) as exc_info:
            user_service.change_password(
                user_id=99999,
                current_password="Test123",
                new_password="NewPassword123",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "usuario" in str(exc_info.value).lower()
        assert "no existe" in str(exc_info.value).lower()
    
    def test_change_password_logs_audit_event(
        self,
        user_service,
        sample_user,
        audit_log_repo
    ):
        """Test: Cambiar contraseña registra evento en audit log."""
        user_service.change_password(
            user_id=sample_user.id,
            current_password="Test123",
            new_password="NewPassword123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que se registró el evento
        logs = audit_log_repo.get_by_user(sample_user.id)
        assert len(logs) > 0
        
        log = logs[0]
        assert log.action == "PASSWORD_CHANGE"
        assert log.resource_type == "user"
        assert log.resource_id == sample_user.id

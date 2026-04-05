"""
Tests para AuthService.

Verifica la funcionalidad de autenticación, generación de tokens,
logout, recuperación de contraseña y migración automática de SHA256 a bcrypt.
"""

import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.audit_log import AuditLog
from app.modelos.token_blacklist import TokenBlacklist
from app.modelos.password_reset_token import PasswordResetToken
from app.repositorios.user_repository import UserRepository
from app.repositorios.audit_log_repository import AuditLogRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.repositorios.password_reset_repository import PasswordResetTokenRepository
from app.servicios.audit_service import AuditService
from app.servicios.auth_service import AuthService, InvalidCredentialsError, InvalidTokenError
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager


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
def audit_log_repo(db_session):
    """Crea un repositorio de audit logs."""
    return AuditLogRepository(db_session)


@pytest.fixture
def token_blacklist_repo(db_session):
    """Crea un repositorio de tokens en lista negra."""
    return TokenBlacklistRepository(db_session)


@pytest.fixture
def password_reset_repo(db_session):
    """Crea un repositorio de tokens de recuperación."""
    return PasswordResetTokenRepository(db_session)


@pytest.fixture
def password_hasher():
    """Crea un hasher de contraseñas."""
    return PasswordHasher(cost_factor=4)  # Cost factor bajo para tests rápidos


@pytest.fixture
def token_manager():
    """Crea un gestor de tokens JWT."""
    return TokenManager(
        secret_key="test_secret_key_with_at_least_32_characters_for_security",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7
    )


@pytest.fixture
def audit_service(audit_log_repo):
    """Crea un servicio de auditoría."""
    return AuditService(audit_log_repo)


@pytest.fixture
def auth_service(
    user_repo,
    token_manager,
    password_hasher,
    audit_service,
    token_blacklist_repo,
    password_reset_repo
):
    """Crea un servicio de autenticación."""
    return AuthService(
        user_repo,
        token_manager,
        password_hasher,
        audit_service,
        token_blacklist_repo,
        password_reset_repo
    )


@pytest.fixture
def sample_user_bcrypt(db_session, password_hasher):
    """Crea un usuario de prueba con contraseña bcrypt."""
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hasher.hash_password("password123"),
        is_active=True,
        is_migrated=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_user_sha256(db_session):
    """Crea un usuario de prueba con contraseña SHA256 (legacy)."""
    password = "password123"
    sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    user = User(
        username="legacyuser",
        email="legacy@example.com",
        password_hash=sha256_hash,
        is_active=True,
        is_migrated=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestAuthenticate:
    """Tests para el método authenticate()."""
    
    def test_authenticate_with_bcrypt_success(self, auth_service, sample_user_bcrypt):
        """Test: Login exitoso con contraseña bcrypt retorna tokens."""
        result = auth_service.authenticate(
            username="testuser",
            password="password123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user" in result
        assert result["user"]["username"] == "testuser"
        assert result["user"]["email"] == "test@example.com"
    
    def test_authenticate_with_sha256_migrates_to_bcrypt(
        self,
        auth_service,
        sample_user_sha256,
        user_repo,
        password_hasher
    ):
        """Test: Login con SHA256 migra automáticamente a bcrypt."""
        # Login con contraseña SHA256
        result = auth_service.authenticate(
            username="legacyuser",
            password="password123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que retorna tokens
        assert "access_token" in result
        assert "refresh_token" in result
        
        # Verificar que la contraseña fue migrada
        user = user_repo.get_by_username("legacyuser")
        assert user.is_migrated is True
        assert user.password_hash.startswith("$2b$")  # bcrypt hash empieza con $2b$
        
        # Verificar que la nueva contraseña bcrypt funciona
        assert password_hasher.verify_password("password123", user.password_hash)
    
    def test_authenticate_with_invalid_username(self, auth_service):
        """Test: Login con username inválido retorna error genérico."""
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.authenticate(
                username="nonexistent",
                password="password123",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert str(exc_info.value) == "Credenciales inválidas"
    
    def test_authenticate_with_invalid_password(self, auth_service, sample_user_bcrypt):
        """Test: Login con password incorrecta retorna error genérico."""
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.authenticate(
                username="testuser",
                password="wrongpassword",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert str(exc_info.value) == "Credenciales inválidas"
    
    def test_authenticate_with_inactive_user(self, auth_service, sample_user_bcrypt, user_repo):
        """Test: Login con usuario inactivo retorna error genérico."""
        # Desactivar usuario
        sample_user_bcrypt.is_active = False
        user_repo.update(sample_user_bcrypt)
        
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.authenticate(
                username="testuser",
                password="password123",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert str(exc_info.value) == "Credenciales inválidas"


class TestRefreshAccessToken:
    """Tests para el método refresh_access_token()."""
    
    def test_refresh_token_generates_new_access_token(
        self,
        auth_service,
        sample_user_bcrypt,
        token_manager
    ):
        """Test: Refresh token válido genera nuevo access token."""
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(sample_user_bcrypt)
        
        # Refrescar access token
        new_access_token = auth_service.refresh_access_token(refresh_token)
        
        # Verificar que es un token válido
        assert new_access_token is not None
        payload = token_manager.decode_token(new_access_token)
        assert payload["user_id"] == sample_user_bcrypt.id
        assert payload["token_type"] == "access"
    
    def test_refresh_token_blacklisted_fails(
        self,
        auth_service,
        sample_user_bcrypt,
        token_manager,
        token_blacklist_repo
    ):
        """Test: Refresh token en lista negra falla."""
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(sample_user_bcrypt)
        payload = token_manager.decode_token(refresh_token)
        
        # Agregar a lista negra
        token_blacklist_repo.add_to_blacklist(
            jti=payload["jti"],
            token_type="refresh",
            user_id=sample_user_bcrypt.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            reason="test"
        )
        
        # Intentar refrescar
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_access_token(refresh_token)
        
        assert "revocado" in str(exc_info.value).lower()


class TestLogout:
    """Tests para el método logout()."""
    
    def test_logout_adds_token_to_blacklist(
        self,
        auth_service,
        sample_user_bcrypt,
        token_manager,
        token_blacklist_repo
    ):
        """Test: Logout agrega token a lista negra."""
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(sample_user_bcrypt)
        payload = token_manager.decode_token(refresh_token)
        jti = payload["jti"]
        
        # Hacer logout
        auth_service.logout(
            refresh_token=refresh_token,
            user_id=sample_user_bcrypt.id,
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que está en lista negra
        assert token_blacklist_repo.is_blacklisted(jti) is True


class TestForgotPassword:
    """Tests para el método forgot_password()."""
    
    def test_forgot_password_generates_token(self, auth_service, sample_user_bcrypt):
        """Test: Forgot password genera token para email válido."""
        token = auth_service.forgot_password("test@example.com")
        
        assert token is not None
        assert len(token) == 64  # 32 bytes = 64 caracteres hex
    
    def test_forgot_password_nonexistent_email_returns_none(self, auth_service):
        """Test: Forgot password no revela si email existe."""
        token = auth_service.forgot_password("nonexistent@example.com")
        
        assert token is None


class TestResetPassword:
    """Tests para el método reset_password()."""
    
    def test_reset_password_with_valid_token(
        self,
        auth_service,
        sample_user_bcrypt,
        user_repo,
        password_hasher
    ):
        """Test: Reset password con token válido actualiza contraseña."""
        # Generar token de recuperación
        token = auth_service.forgot_password("test@example.com")
        
        # Resetear contraseña
        auth_service.reset_password(
            token=token,
            new_password="newpassword123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Verificar que la contraseña cambió
        user = user_repo.get_by_email("test@example.com")
        assert password_hasher.verify_password("newpassword123", user.password_hash)
    
    def test_reset_password_with_used_token_fails(
        self,
        auth_service,
        sample_user_bcrypt
    ):
        """Test: Reset password con token usado falla."""
        # Generar token y usarlo
        token = auth_service.forgot_password("test@example.com")
        auth_service.reset_password(
            token=token,
            new_password="newpassword123",
            ip_address="127.0.0.1",
            user_agent="TestAgent/1.0"
        )
        
        # Intentar usar el mismo token de nuevo
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.reset_password(
                token=token,
                new_password="anotherpassword",
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0"
            )
        
        assert "usado" in str(exc_info.value).lower()

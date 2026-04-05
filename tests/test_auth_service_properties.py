"""
Property-based tests para AuthService.

Este módulo implementa property tests usando Hypothesis para validar:
- Property 7: Token validation rejects invalid tokens
- Property 8: Logout invalidates refresh token
- Property 9: Automatic password migration on login
- Property 10: Password migration logging
- Property 12: Generic authentication error messages
- Property 14: Failed login attempts are audited
- Property 45: Logout blacklists refresh token

Valida Requirements: 1.7, 1.10, 2.4, 2.5, 6.1, 6.4, 20.2

# Feature: mejoras-seguridad-jwt-auditoria, Property 7: Token validation rejects invalid tokens
# Feature: mejoras-seguridad-jwt-auditoria, Property 8: Logout invalidates refresh token
# Feature: mejoras-seguridad-jwt-auditoria, Property 9: Automatic password migration on login
# Feature: mejoras-seguridad-jwt-auditoria, Property 10: Password migration logging
# Feature: mejoras-seguridad-jwt-auditoria, Property 12: Generic authentication error messages
# Feature: mejoras-seguridad-jwt-auditoria, Property 14: Failed login attempts are audited
# Feature: mejoras-seguridad-jwt-auditoria, Property 45: Logout blacklists refresh token
"""

import hashlib
import pytest
from datetime import datetime, timedelta, timezone
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from jwt.exceptions import InvalidTokenError as JWTInvalidTokenError, ExpiredSignatureError

from app.configuracion.base_datos import Base
from app.modelos.user import User
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


# Estrategias de Hypothesis
@st.composite
def valid_username(draw):
    """Genera usernames válidos."""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"),
        min_size=3,
        max_size=20
    ))


@st.composite
def valid_email(draw):
    """Genera emails válidos."""
    local = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"),
        min_size=1,
        max_size=20
    ))
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"),
        min_size=1,
        max_size=20
    ))
    tld = draw(st.sampled_from(["com", "org", "net", "edu"]))
    return f"{local}@{domain}.{tld}"


@st.composite
def valid_password(draw):
    """Genera passwords válidos."""
    return draw(st.text(
        alphabet=st.characters(
            blacklist_categories=("Cs", "Cc"),
            min_codepoint=32,
            max_codepoint=126
        ),
        min_size=8,
        max_size=50
    ))


@st.composite
def valid_ip_address(draw):
    """Genera direcciones IP válidas."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(map(str, octets))


@st.composite
def valid_user_agent(draw):
    """Genera user agents válidos."""
    browsers = ["Chrome", "Firefox", "Safari", "Edge"]
    versions = draw(st.integers(min_value=80, max_value=120))
    browser = draw(st.sampled_from(browsers))
    return f"{browser}/{versions}.0"


# Fixtures
@pytest.fixture(scope="function")
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
    return PasswordHasher(cost_factor=4)


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



@pytest.mark.property_test
class TestProperty7_TokenValidationRejectsInvalidTokens:
    """
    Property 7: Token validation rejects invalid tokens
    
    **Validates: Requirements 1.7**
    
    Propiedad: FOR ANY token JWT que esté expirado, tenga firma inválida, o esté en blacklist,
               el Auth_Middleware debe rechazarlo y retornar HTTP 401
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        invalid_token=st.text(min_size=10, max_size=100)
    )
    def test_invalid_signature_tokens_are_rejected(
        self,
        auth_service,
        user_repo,
        password_hasher,
        token_manager,
        username,
        email,
        password,
        invalid_token
    ):
        """
        Property: Tokens con firma inválida son rechazados.
        
        Valida que tokens malformados o con firma incorrecta no pueden
        ser usados para refresh.
        """
        # Evitar colisiones con tokens válidos
        assume(not invalid_token.startswith("eyJ"))
        
        # Intentar refrescar con token inválido
        with pytest.raises(InvalidTokenError):
            auth_service.refresh_access_token(invalid_token)
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password()
    )
    def test_blacklisted_tokens_are_rejected(
        self,
        db_session,
        auth_service,
        user_repo,
        password_hasher,
        token_manager,
        token_blacklist_repo,
        username,
        email,
        password
    ):
        """
        Property: Tokens en blacklist son rechazados.
        
        Valida que tokens agregados a la blacklist no pueden ser usados
        para refresh, incluso si son válidos.
        """
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        payload = token_manager.decode_token(refresh_token)
        
        # Agregar a blacklist
        token_blacklist_repo.add_to_blacklist(
            jti=payload["jti"],
            token_type="refresh",
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            reason="test"
        )
        
        # Intentar refrescar con token blacklisted
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_access_token(refresh_token)
        
        assert "revocado" in str(exc_info.value).lower()
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=30)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password()
    )
    def test_expired_tokens_are_rejected(
        self,
        db_session,
        user_repo,
        password_hasher,
        username,
        email,
        password
    ):
        """
        Property: Tokens expirados son rechazados.
        
        Valida que tokens con tiempo de expiración pasado no pueden ser usados.
        """
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Crear token manager con expiración muy corta (1 segundo)
        short_token_manager = TokenManager(
            secret_key="test_secret_key_with_at_least_32_characters_for_security",
            access_token_expire_minutes=0,  # Expira inmediatamente
            refresh_token_expire_days=0
        )
        
        # Generar token que expira inmediatamente
        refresh_token = short_token_manager.generate_refresh_token(user)
        
        # Esperar un momento para que expire
        import time
        time.sleep(0.1)
        
        # Intentar decodificar token expirado
        with pytest.raises((ExpiredSignatureError, JWTInvalidTokenError)):
            short_token_manager.decode_token(refresh_token)



@pytest.mark.property_test
class TestProperty8_LogoutInvalidatesRefreshToken:
    """
    Property 8: Logout invalidates refresh token
    
    **Validates: Requirements 1.10**
    
    Propiedad: FOR ANY refresh token válido, después de llamar logout con ese token,
               intentar usarlo para refresh debe fallar con un error indicando que
               el token está en blacklist
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_logout_invalidates_refresh_token(
        self,
        db_session,
        auth_service,
        user_repo,
        password_hasher,
        token_manager,
        username,
        email,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Logout invalida el refresh token agregándolo a blacklist.
        
        Valida que después de logout, el refresh token no puede ser usado
        para generar nuevos access tokens.
        """
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        
        # Verificar que el token funciona ANTES de logout
        new_access_token = auth_service.refresh_access_token(refresh_token)
        assert new_access_token is not None
        
        # Hacer logout
        auth_service.logout(
            refresh_token=refresh_token,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Intentar usar el token DESPUÉS de logout
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_access_token(refresh_token)
        
        # Verificar que el error menciona que está revocado/blacklisted
        assert "revocado" in str(exc_info.value).lower()


@pytest.mark.property_test
class TestProperty9_AutomaticPasswordMigrationOnLogin:
    """
    Property 9: Automatic password migration on login
    
    **Validates: Requirements 2.4**
    
    Propiedad: FOR ANY usuario con hash de contraseña SHA256, después de un login exitoso,
               el password_hash debe actualizarse a formato bcrypt y el flag is_migrated
               debe ser True
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_sha256_password_migrates_to_bcrypt_on_login(
        self,
        db_session,
        auth_service,
        user_repo,
        password_hasher,
        username,
        email,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Login con SHA256 migra automáticamente a bcrypt.
        
        Valida que:
        1. Usuario con SHA256 puede hacer login
        2. Después del login, el hash es bcrypt
        3. El flag is_migrated es True
        4. La nueva contraseña bcrypt funciona
        """
        # Crear usuario con contraseña SHA256 (legacy)
        sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        user = User(
            username=username,
            email=email,
            password_hash=sha256_hash,
            is_active=True,
            is_migrated=False
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Verificar que es SHA256 (64 caracteres hex)
        assert len(user.password_hash) == 64
        assert all(c in '0123456789abcdef' for c in user.password_hash)
        assert user.is_migrated is False
        
        # Hacer login
        result = auth_service.authenticate(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Verificar que retorna tokens
        assert "access_token" in result
        assert "refresh_token" in result
        
        # Verificar que la contraseña fue migrada
        db_session.refresh(user)
        assert user.is_migrated is True
        assert user.password_hash.startswith("$2b$"), \
            f"Password should be migrated to bcrypt, got {user.password_hash[:10]}"
        
        # Verificar que la nueva contraseña bcrypt funciona
        assert password_hasher.verify_password(password, user.password_hash)



@pytest.mark.property_test
class TestProperty10_PasswordMigrationLogging:
    """
    Property 10: Password migration logging
    
    **Validates: Requirements 2.5**
    
    Propiedad: FOR ANY migración de contraseña (SHA256 a bcrypt), debe crearse una entrada
               en audit log con acción PASSWORD_MIGRATED
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_password_migration_creates_audit_log(
        self,
        db_session,
        auth_service,
        audit_log_repo,
        username,
        email,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Migración de contraseña crea entrada en audit log.
        
        Valida que cada migración automática de SHA256 a bcrypt se registra
        en el audit log con acción PASSWORD_MIGRATED.
        """
        # Crear usuario con contraseña SHA256
        sha256_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
        user = User(
            username=username,
            email=email,
            password_hash=sha256_hash,
            is_active=True,
            is_migrated=False
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Contar audit logs antes del login
        logs_before = db_session.query(AuditLog).filter(
            AuditLog.action == "PASSWORD_MIGRATED"
        ).count()
        
        # Hacer login (esto debe migrar la contraseña)
        auth_service.authenticate(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Verificar que se creó un audit log de PASSWORD_MIGRATED
        logs_after = db_session.query(AuditLog).filter(
            AuditLog.action == "PASSWORD_MIGRATED"
        ).count()
        
        assert logs_after == logs_before + 1, \
            f"Should create one PASSWORD_MIGRATED audit log, got {logs_after - logs_before}"
        
        # Verificar detalles del audit log
        migration_log = db_session.query(AuditLog).filter(
            AuditLog.action == "PASSWORD_MIGRATED",
            AuditLog.user_id == user.id
        ).order_by(AuditLog.timestamp.desc()).first()
        
        assert migration_log is not None
        assert migration_log.resource_type == "user"
        assert migration_log.resource_id == user.id
        assert migration_log.ip_address == ip_address
        assert migration_log.user_agent == user_agent
        assert "from" in migration_log.details
        assert "to" in migration_log.details
        assert migration_log.details["from"] == "SHA256"
        assert migration_log.details["to"] == "bcrypt"


@pytest.mark.property_test
class TestProperty12_GenericAuthenticationErrorMessages:
    """
    Property 12: Generic authentication error messages
    
    **Validates: Requirements 6.1**
    
    Propiedad: FOR ANY intento de login fallido, ya sea por username inexistente o
               contraseña incorrecta, la API debe retornar el mismo mensaje genérico
               "Credenciales inválidas" sin revelar qué parte falló
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        correct_password=valid_password(),
        wrong_password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_invalid_password_returns_generic_error(
        self,
        db_session,
        auth_service,
        password_hasher,
        username,
        email,
        correct_password,
        wrong_password,
        ip_address,
        user_agent
    ):
        """
        Property: Contraseña incorrecta retorna mensaje genérico.
        
        Valida que el error no revela que el usuario existe pero la contraseña
        es incorrecta.
        """
        # Asegurar que las contraseñas son diferentes
        assume(correct_password != wrong_password)
        
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(correct_password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Intentar login con contraseña incorrecta
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.authenticate(
                username=username,
                password=wrong_password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Verificar mensaje genérico
        assert str(exc_info.value) == "Credenciales inválidas"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        nonexistent_username=valid_username(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_nonexistent_user_returns_generic_error(
        self,
        auth_service,
        nonexistent_username,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Usuario inexistente retorna mensaje genérico.
        
        Valida que el error no revela que el usuario no existe.
        """
        # Intentar login con usuario inexistente
        with pytest.raises(InvalidCredentialsError) as exc_info:
            auth_service.authenticate(
                username=nonexistent_username,
                password=password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        # Verificar mensaje genérico
        assert str(exc_info.value) == "Credenciales inválidas"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        wrong_password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_error_messages_are_identical(
        self,
        db_session,
        auth_service,
        password_hasher,
        username,
        email,
        password,
        wrong_password,
        ip_address,
        user_agent
    ):
        """
        Property: Mensajes de error son idénticos para diferentes fallos.
        
        Valida que no se puede distinguir entre usuario inexistente y
        contraseña incorrecta basándose en el mensaje de error.
        """
        assume(password != wrong_password)
        
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        
        # Error por contraseña incorrecta
        error_msg_1 = None
        try:
            auth_service.authenticate(
                username=username,
                password=wrong_password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except InvalidCredentialsError as e:
            error_msg_1 = str(e)
        
        # Error por usuario inexistente
        error_msg_2 = None
        try:
            auth_service.authenticate(
                username=f"nonexistent_{username}",
                password=password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except InvalidCredentialsError as e:
            error_msg_2 = str(e)
        
        # Verificar que los mensajes son idénticos
        assert error_msg_1 == error_msg_2, \
            f"Error messages should be identical, got '{error_msg_1}' and '{error_msg_2}'"
        assert error_msg_1 == "Credenciales inválidas"



@pytest.mark.property_test
class TestProperty14_FailedLoginAttemptsAreAudited:
    """
    Property 14: Failed login attempts are audited
    
    **Validates: Requirements 6.4**
    
    Propiedad: FOR ANY intento de login fallido, debe crearse una entrada en audit log
               con acción LOGIN_FAILED, incluyendo la dirección IP y timestamp
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        correct_password=valid_password(),
        wrong_password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_failed_login_creates_audit_log(
        self,
        db_session,
        auth_service,
        password_hasher,
        username,
        email,
        correct_password,
        wrong_password,
        ip_address,
        user_agent
    ):
        """
        Property: Login fallido crea entrada en audit log.
        
        Valida que cada intento fallido de login se registra en el audit log
        con acción LOGIN_FAILED, incluyendo IP y timestamp.
        """
        assume(correct_password != wrong_password)
        
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(correct_password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Contar audit logs antes del intento
        logs_before = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED"
        ).count()
        
        # Intentar login con contraseña incorrecta
        try:
            auth_service.authenticate(
                username=username,
                password=wrong_password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except InvalidCredentialsError:
            pass  # Esperado
        
        # Verificar que se creó un audit log de LOGIN_FAILED
        logs_after = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED"
        ).count()
        
        assert logs_after == logs_before + 1, \
            f"Should create one LOGIN_FAILED audit log, got {logs_after - logs_before}"
        
        # Verificar detalles del audit log
        failed_log = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED",
            AuditLog.user_id == user.id
        ).order_by(AuditLog.timestamp.desc()).first()
        
        assert failed_log is not None
        assert failed_log.resource_type == "auth"
        assert failed_log.ip_address == ip_address
        assert failed_log.user_agent == user_agent
        assert failed_log.timestamp is not None
        assert "username" in failed_log.details
        assert "reason" in failed_log.details
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    @given(
        nonexistent_username=valid_username(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_nonexistent_user_login_creates_audit_log(
        self,
        db_session,
        auth_service,
        nonexistent_username,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Login con usuario inexistente también crea audit log.
        
        Valida que incluso intentos con usuarios que no existen se registran
        en el audit log (aunque con user_id = None).
        """
        # Contar audit logs antes del intento
        logs_before = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED"
        ).count()
        
        # Intentar login con usuario inexistente
        try:
            auth_service.authenticate(
                username=nonexistent_username,
                password=password,
                ip_address=ip_address,
                user_agent=user_agent
            )
        except InvalidCredentialsError:
            pass  # Esperado
        
        # Verificar que se creó un audit log
        logs_after = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED"
        ).count()
        
        assert logs_after == logs_before + 1
        
        # Verificar que el log tiene user_id = None
        failed_log = db_session.query(AuditLog).filter(
            AuditLog.action == "LOGIN_FAILED"
        ).order_by(AuditLog.timestamp.desc()).first()
        
        assert failed_log.user_id is None
        assert failed_log.ip_address == ip_address


@pytest.mark.property_test
class TestProperty45_LogoutBlacklistsRefreshToken:
    """
    Property 45: Logout blacklists refresh token
    
    **Validates: Requirements 20.2**
    
    Propiedad: FOR ANY operación de logout, el jti del refresh token debe agregarse
               a la blacklist de tokens, y los intentos subsecuentes de usar ese token
               deben fallar
    """
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=100)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_logout_adds_jti_to_blacklist(
        self,
        db_session,
        auth_service,
        password_hasher,
        token_manager,
        token_blacklist_repo,
        username,
        email,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Logout agrega el JTI del token a la blacklist.
        
        Valida que:
        1. Logout agrega el JTI a token_blacklist
        2. El token blacklisted no puede ser usado para refresh
        3. La entrada en blacklist tiene el tipo correcto
        """
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Generar refresh token
        refresh_token = token_manager.generate_refresh_token(user)
        payload = token_manager.decode_token(refresh_token)
        jti = payload["jti"]
        
        # Verificar que NO está en blacklist antes de logout
        assert not token_blacklist_repo.is_blacklisted(jti)
        
        # Hacer logout
        auth_service.logout(
            refresh_token=refresh_token,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Verificar que SÍ está en blacklist después de logout
        assert token_blacklist_repo.is_blacklisted(jti), \
            f"JTI {jti} should be blacklisted after logout"
        
        # Verificar que el token no puede ser usado
        with pytest.raises(InvalidTokenError) as exc_info:
            auth_service.refresh_access_token(refresh_token)
        
        assert "revocado" in str(exc_info.value).lower()
        
        # Verificar detalles de la entrada en blacklist
        blacklist_entry = db_session.query(TokenBlacklist).filter(
            TokenBlacklist.jti == jti
        ).first()
        
        assert blacklist_entry is not None
        assert blacklist_entry.token_type == "refresh"
        assert blacklist_entry.user_id == user.id
        assert blacklist_entry.reason == "logout"
    
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=50)
    @given(
        username=valid_username(),
        email=valid_email(),
        password=valid_password(),
        ip_address=valid_ip_address(),
        user_agent=valid_user_agent()
    )
    def test_multiple_logouts_with_different_tokens(
        self,
        db_session,
        auth_service,
        password_hasher,
        token_manager,
        token_blacklist_repo,
        username,
        email,
        password,
        ip_address,
        user_agent
    ):
        """
        Property: Múltiples logouts con diferentes tokens funcionan correctamente.
        
        Valida que cada logout agrega su propio JTI a la blacklist sin
        afectar otros tokens.
        """
        # Crear usuario
        user = User(
            username=username,
            email=email,
            password_hash=password_hasher.hash_password(password),
            is_active=True,
            is_migrated=True
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Generar múltiples refresh tokens
        token1 = token_manager.generate_refresh_token(user)
        token2 = token_manager.generate_refresh_token(user)
        token3 = token_manager.generate_refresh_token(user)
        
        jti1 = token_manager.decode_token(token1)["jti"]
        jti2 = token_manager.decode_token(token2)["jti"]
        jti3 = token_manager.decode_token(token3)["jti"]
        
        # Hacer logout del primer token
        auth_service.logout(token1, user.id, ip_address, user_agent)
        
        # Verificar que solo el primer token está blacklisted
        assert token_blacklist_repo.is_blacklisted(jti1)
        assert not token_blacklist_repo.is_blacklisted(jti2)
        assert not token_blacklist_repo.is_blacklisted(jti3)
        
        # Hacer logout del segundo token
        auth_service.logout(token2, user.id, ip_address, user_agent)
        
        # Verificar que los dos primeros están blacklisted
        assert token_blacklist_repo.is_blacklisted(jti1)
        assert token_blacklist_repo.is_blacklisted(jti2)
        assert not token_blacklist_repo.is_blacklisted(jti3)
        
        # El tercer token aún debe funcionar
        new_access_token = auth_service.refresh_access_token(token3)
        assert new_access_token is not None

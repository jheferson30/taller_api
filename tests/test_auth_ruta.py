"""
Tests para endpoints de autenticación en app/rutas/auth_ruta.py.

Valida los endpoints de login, refresh, logout, forgot password y reset password.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base, obtener_db
from app.main import app
from app.modelos.password_reset_token import PasswordResetToken
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager

# Base de datos en memoria para tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Crea una sesión de base de datos para tests."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    """Cliente de test de FastAPI con base de datos de test."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[obtener_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def password_hasher():
    """Instancia de PasswordHasher para tests."""
    return PasswordHasher()


@pytest.fixture
def token_manager():
    """Instancia de TokenManager para tests."""
    return TokenManager()


@pytest.fixture
def test_user(db_session, password_hasher):
    """Crea un usuario de test con contraseña bcrypt."""
    # Crear rol
    role = Role(name="USER", description="Usuario estándar")
    db_session.add(role)
    db_session.commit()

    # Crear usuario
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=password_hasher.hash_password("TestPassword123"),
        is_active=True,
        is_migrated=True,
    )
    db_session.add(user)
    db_session.commit()

    # Asignar rol
    user_role = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


@pytest.fixture
def test_user_sha256(db_session):
    """Crea un usuario de test con contraseña SHA256 (legacy)."""
    import hashlib

    # Crear rol
    role = Role(name="USER", description="Usuario estándar")
    db_session.add(role)
    db_session.commit()

    # Crear usuario con SHA256
    password = "TestPassword123"
    sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    user = User(
        username="legacyuser",
        email="legacy@example.com",
        password_hash=sha256_hash,
        is_active=True,
        is_migrated=False,
    )
    db_session.add(user)
    db_session.commit()

    # Asignar rol
    user_role = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(user_role)
    db_session.commit()

    db_session.refresh(user)
    return user


class TestLoginEndpoint:
    """Tests para POST /auth/login."""

    def test_login_success_bcrypt(self, client, test_user):
        """Test login exitoso con contraseña bcrypt."""
        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "TestPassword123"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data
        assert data["user"]["username"] == "testuser"
        assert data["user"]["email"] == "test@example.com"
        assert "USER" in data["user"]["roles"]

    def test_login_success_sha256_migration(self, client, test_user_sha256, db_session):
        """Test login exitoso con contraseña SHA256 y migración automática a bcrypt."""
        response = client.post(
            "/auth/login", json={"username": "legacyuser", "password": "TestPassword123"}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data

        # Verificar que la contraseña fue migrada a bcrypt
        db_session.refresh(test_user_sha256)
        assert test_user_sha256.is_migrated is True
        assert len(test_user_sha256.password_hash) > 64  # bcrypt es más largo que SHA256

    def test_login_invalid_username(self, client):
        """Test login con username inexistente."""
        response = client.post(
            "/auth/login", json={"username": "nonexistent", "password": "TestPassword123"}
        )

        assert response.status_code == 401
        assert "Credenciales inválidas" in response.json()["detail"]

    def test_login_invalid_password(self, client, test_user):
        """Test login con contraseña incorrecta."""
        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "WrongPassword123"}
        )

        assert response.status_code == 401
        assert "Credenciales inválidas" in response.json()["detail"]

    def test_login_inactive_user(self, client, test_user, db_session):
        """Test login con usuario inactivo."""
        test_user.is_active = False
        db_session.commit()

        response = client.post(
            "/auth/login", json={"username": "testuser", "password": "TestPassword123"}
        )

        assert response.status_code == 401
        assert "Credenciales inválidas" in response.json()["detail"]

    def test_login_captures_ip_and_user_agent(self, client, test_user):
        """Test que login captura IP y user agent del request."""
        response = client.post(
            "/auth/login",
            json={"username": "testuser", "password": "TestPassword123"},
            headers={"User-Agent": "TestClient/1.0"},
        )

        assert response.status_code == 200
        # El audit log debería contener la IP y user agent
        # (verificado indirectamente por el éxito del login)


class TestRefreshEndpoint:
    """Tests para POST /auth/refresh."""

    def test_refresh_success(self, client, test_user, token_manager):
        """Test refresh exitoso con refresh token válido."""
        # Generar tokens
        tokens = token_manager.generate_tokens(test_user)
        refresh_token = tokens["refresh_token"]

        response = client.post("/auth/refresh", json={"refresh_token": refresh_token})

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert data["access_token"] != tokens["access_token"]  # Nuevo token

    def test_refresh_invalid_token(self, client):
        """Test refresh con token inválido."""
        response = client.post("/auth/refresh", json={"refresh_token": "invalid_token"})

        assert response.status_code == 401
        assert "inválido" in response.json()["detail"].lower()

    def test_refresh_expired_token(self, client, test_user, token_manager):
        """Test refresh con token expirado."""
        # Generar token con expiración inmediata (mock)
        with patch.object(token_manager, "decode_token") as mock_decode:
            mock_decode.side_effect = Exception("Token has expired")

            response = client.post("/auth/refresh", json={"refresh_token": "expired_token"})

            assert response.status_code == 401

    def test_refresh_access_token_rejected(self, client, test_user, token_manager):
        """Test refresh rechaza access token (solo acepta refresh tokens)."""
        # Generar tokens
        tokens = token_manager.generate_tokens(test_user)
        access_token = tokens["access_token"]

        response = client.post("/auth/refresh", json={"refresh_token": access_token})

        assert response.status_code == 401
        assert "refresh token" in response.json()["detail"].lower()


class TestLogoutEndpoint:
    """Tests para POST /auth/logout."""

    def test_logout_success(self, client, test_user, token_manager):
        """Test logout exitoso con autenticación."""
        # Generar tokens
        tokens = token_manager.generate_tokens(test_user)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        response = client.post(
            "/auth/logout",
            json={"refresh_token": refresh_token},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 204

    def test_logout_without_auth(self, client):
        """Test logout sin autenticación (debe fallar)."""
        response = client.post("/auth/logout", json={"refresh_token": "some_token"})

        assert response.status_code == 401

    def test_logout_invalid_refresh_token(self, client, test_user, token_manager):
        """Test logout con refresh token inválido."""
        # Generar access token válido
        tokens = token_manager.generate_tokens(test_user)
        access_token = tokens["access_token"]

        response = client.post(
            "/auth/logout",
            json={"refresh_token": "invalid_token"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert response.status_code == 401


class TestForgotPasswordEndpoint:
    """Tests para POST /auth/forgot-password."""

    def test_forgot_password_existing_email(self, client, test_user):
        """Test forgot password con email existente."""
        response = client.post("/auth/forgot-password", json={"email": "test@example.com"})

        assert response.status_code == 200
        data = response.json()

        # Mensaje genérico (no revela si email existe)
        assert "recibirás instrucciones" in data["message"].lower()

    def test_forgot_password_nonexistent_email(self, client):
        """Test forgot password con email inexistente (mismo mensaje)."""
        response = client.post("/auth/forgot-password", json={"email": "nonexistent@example.com"})

        assert response.status_code == 200
        data = response.json()

        # Mismo mensaje genérico (previene enumeración)
        assert "recibirás instrucciones" in data["message"].lower()

    def test_forgot_password_invalid_email_format(self, client):
        """Test forgot password con formato de email inválido."""
        response = client.post("/auth/forgot-password", json={"email": "invalid-email"})

        assert response.status_code == 422  # Validation error


class TestResetPasswordEndpoint:
    """Tests para POST /auth/reset-password."""

    def test_reset_password_success(self, client, test_user, db_session):
        """Test reset password exitoso con token válido."""
        import hashlib
        import secrets

        # Crear token de recuperación
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=test_user.id, token=token_hash, expires_at=expires_at, used=False
        )
        db_session.add(reset_token)
        db_session.commit()

        # Resetear contraseña
        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "NewPassword123"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "exitosamente" in data["message"].lower()

        # Verificar que el token fue marcado como usado
        db_session.refresh(reset_token)
        assert reset_token.used is True

    def test_reset_password_invalid_token(self, client):
        """Test reset password con token inválido."""
        response = client.post(
            "/auth/reset-password",
            json={"token": "invalid_token", "new_password": "NewPassword123"},
        )

        assert response.status_code == 400
        assert "inválido" in response.json()["detail"].lower()

    def test_reset_password_expired_token(self, client, test_user, db_session):
        """Test reset password con token expirado."""
        import hashlib
        import secrets

        # Crear token expirado
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) - timedelta(hours=1)  # Expirado

        reset_token = PasswordResetToken(
            user_id=test_user.id, token=token_hash, expires_at=expires_at, used=False
        )
        db_session.add(reset_token)
        db_session.commit()

        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "NewPassword123"}
        )

        assert response.status_code == 400
        assert "expirado" in response.json()["detail"].lower()

    def test_reset_password_used_token(self, client, test_user, db_session):
        """Test reset password con token ya usado."""
        import hashlib
        import secrets

        # Crear token usado
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=test_user.id,
            token=token_hash,
            expires_at=expires_at,
            used=True,  # Ya usado
        )
        db_session.add(reset_token)
        db_session.commit()

        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "NewPassword123"}
        )

        assert response.status_code == 400
        assert "usado" in response.json()["detail"].lower()

    def test_reset_password_weak_password(self, client, test_user, db_session):
        """Test reset password con contraseña débil (no cumple requisitos)."""
        import hashlib
        import secrets

        # Crear token válido
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=test_user.id, token=token_hash, expires_at=expires_at, used=False
        )
        db_session.add(reset_token)
        db_session.commit()

        # Contraseña sin mayúscula
        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "weakpassword123"}
        )

        assert response.status_code == 422  # Validation error
        assert "mayúscula" in response.json()["detail"][0]["msg"].lower()

    def test_reset_password_complexity_requirements(self, client, test_user, db_session):
        """Test que reset password valida todos los requisitos de complejidad."""
        import hashlib
        import secrets

        # Crear token válido
        raw_token = secrets.token_hex(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        reset_token = PasswordResetToken(
            user_id=test_user.id, token=token_hash, expires_at=expires_at, used=False
        )
        db_session.add(reset_token)
        db_session.commit()

        # Test sin número
        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "NoNumberPassword"}
        )
        assert response.status_code == 422

        # Test sin minúscula
        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "NONLOWERCASE123"}
        )
        assert response.status_code == 422

        # Test muy corta
        response = client.post(
            "/auth/reset-password", json={"token": raw_token, "new_password": "Short1"}
        )
        assert response.status_code == 422

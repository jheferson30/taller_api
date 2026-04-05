"""
Tests para AuthMiddleware y decoradores de autenticación.

Verifica la funcionalidad del middleware de autenticación JWT,
decoradores @require_auth y @require_role.
"""

import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.configuracion.base_datos import Base
from app.modelos.user import User
from app.modelos.role import Role
from app.modelos.user_role import UserRole
from app.modelos.token_blacklist import TokenBlacklist
from app.repositorios.user_repository import UserRepository
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager
from app.seguridad.auth_middleware import AuthMiddleware, require_auth, require_role


# Configuración de base de datos en memoria para tests
@pytest.fixture
def db_session():
    """Crea una sesión de base de datos en memoria para tests."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def token_manager():
    """Crea un gestor de tokens JWT."""
    return TokenManager(
        secret_key="test_secret_key_with_at_least_32_characters_for_security",
        access_token_expire_minutes=15,
        refresh_token_expire_days=7
    )


@pytest.fixture
def password_hasher():
    """Crea un hasher de contraseñas."""
    return PasswordHasher(cost_factor=4)


@pytest.fixture
def sample_user_with_roles(db_session, password_hasher):
    """Crea un usuario de prueba con roles ADMIN y MECANICO."""
    # Crear roles
    admin_role = Role(name="ADMIN", description="Administrator")
    mecanico_role = Role(name="MECANICO", description="Mechanic")
    db_session.add(admin_role)
    db_session.add(mecanico_role)
    db_session.commit()
    
    # Crear usuario
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
    
    # Asignar roles
    user_admin_role = UserRole(user_id=user.id, role_id=admin_role.id)
    user_mecanico_role = UserRole(user_id=user.id, role_id=mecanico_role.id)
    db_session.add(user_admin_role)
    db_session.add(user_mecanico_role)
    db_session.commit()
    
    # Refrescar para cargar relaciones
    db_session.refresh(user)
    
    return user


@pytest.fixture
def sample_user_no_roles(db_session, password_hasher):
    """Crea un usuario de prueba sin roles."""
    user = User(
        username="noroleuser",
        email="norole@example.com",
        password_hash=password_hasher.hash_password("password123"),
        is_active=True,
        is_migrated=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def app_with_middleware(db_session, token_manager):
    """Crea una aplicación FastAPI con AuthMiddleware."""
    app = FastAPI()
    
    # Factory que retorna la misma sesión de test
    def test_db_factory():
        return db_session
    
    # Agregar middleware ANTES de registrar endpoints
    app.add_middleware(
        AuthMiddleware,
        token_manager=token_manager,
        db_session_factory=test_db_factory
    )
    
    # Endpoint público
    @app.get("/public")
    async def public_endpoint():
        return {"message": "Public access"}
    
    # Endpoint protegido con @require_auth
    @app.get("/protected")
    @require_auth
    async def protected_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Hello {user.username}"}
    
    # Endpoint protegido con @require_role
    @app.get("/admin")
    @require_auth
    @require_role("ADMIN")
    async def admin_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Admin access for {user.username}"}
    
    # Endpoint con múltiples roles
    @app.get("/staff")
    @require_auth
    @require_role("ADMIN", "MECANICO")
    async def staff_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Staff access for {user.username}"}
    
    return app


class TestAuthMiddleware:
    """Tests para AuthMiddleware."""
    
    def test_public_endpoint_without_token(self, app_with_middleware):
        """Test: Endpoint público accesible sin token."""
        client = TestClient(app_with_middleware)
        response = client.get("/public")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Public access"}
    
    def test_protected_endpoint_without_token(self, app_with_middleware):
        """Test: Endpoint protegido sin token retorna 401."""
        client = TestClient(app_with_middleware)
        response = client.get("/protected")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_protected_endpoint_with_valid_token(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager
    ):
        """Test: Endpoint protegido con token válido retorna 200."""
        # Generar token
        token = token_manager.generate_access_token(sample_user_with_roles)
        
        # Hacer request con token
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert response.json() == {"message": "Hello testuser"}
    
    def test_protected_endpoint_with_invalid_token(self, app_with_middleware):
        """Test: Endpoint protegido con token inválido retorna 401."""
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        assert "Invalid token" in response.json()["detail"]
    
    def test_protected_endpoint_with_expired_token(
        self,
        app_with_middleware,
        sample_user_with_roles
    ):
        """Test: Endpoint protegido con token expirado retorna 401."""
        # Crear token manager con expiración inmediata
        expired_token_manager = TokenManager(
            secret_key="test_secret_key_with_at_least_32_characters_for_security",
            access_token_expire_minutes=-1  # Token ya expirado
        )
        
        token = expired_token_manager.generate_access_token(sample_user_with_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()
    
    def test_protected_endpoint_with_blacklisted_token(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager,
        db_session
    ):
        """Test: Endpoint protegido con token en blacklist retorna 401."""
        # Generar token
        token = token_manager.generate_access_token(sample_user_with_roles)
        payload = token_manager.decode_token(token)
        
        # Agregar a blacklist
        blacklist_repo = TokenBlacklistRepository(db_session)
        blacklist_repo.add_to_blacklist(
            jti=payload["jti"],
            token_type="access",
            user_id=sample_user_with_roles.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            reason="test"
        )
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()
    
    def test_protected_endpoint_with_inactive_user(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager,
        db_session
    ):
        """Test: Endpoint protegido con usuario inactivo retorna 401."""
        # Generar token
        token = token_manager.generate_access_token(sample_user_with_roles)
        
        # Desactivar usuario
        sample_user_with_roles.is_active = False
        db_session.commit()
        db_session.refresh(sample_user_with_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 401
        assert "inactive" in response.json()["detail"].lower()
    
    def test_middleware_with_invalid_authorization_header_format(
        self,
        app_with_middleware
    ):
        """Test: Header Authorization con formato inválido retorna 401."""
        client = TestClient(app_with_middleware)
        
        # Sin "Bearer" prefix
        response = client.get(
            "/protected",
            headers={"Authorization": "invalid_token"}
        )
        assert response.status_code == 401
        assert "Invalid authorization header format" in response.json()["detail"]


class TestRequireAuthDecorator:
    """Tests para decorador @require_auth."""
    
    def test_require_auth_with_authenticated_user(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager
    ):
        """Test: @require_auth permite acceso con usuario autenticado."""
        token = token_manager.generate_access_token(sample_user_with_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Hello testuser" in response.json()["message"]
    
    def test_require_auth_without_authenticated_user(self, app_with_middleware):
        """Test: @require_auth bloquea acceso sin usuario autenticado."""
        client = TestClient(app_with_middleware)
        response = client.get("/protected")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestRequireRoleDecorator:
    """Tests para decorador @require_role."""
    
    def test_require_role_with_matching_role(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager
    ):
        """Test: @require_role permite acceso con rol correcto."""
        token = token_manager.generate_access_token(sample_user_with_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Admin access" in response.json()["message"]
    
    def test_require_role_with_multiple_roles(
        self,
        app_with_middleware,
        sample_user_with_roles,
        token_manager
    ):
        """Test: @require_role con múltiples roles permite acceso si tiene uno."""
        token = token_manager.generate_access_token(sample_user_with_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/staff",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        assert "Staff access" in response.json()["message"]
    
    def test_require_role_without_matching_role(
        self,
        app_with_middleware,
        sample_user_no_roles,
        token_manager
    ):
        """Test: @require_role bloquea acceso sin rol requerido."""
        token = token_manager.generate_access_token(sample_user_no_roles)
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/admin",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    def test_require_role_without_authentication(self, app_with_middleware):
        """Test: @require_role bloquea acceso sin autenticación."""
        client = TestClient(app_with_middleware)
        response = client.get("/admin")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]

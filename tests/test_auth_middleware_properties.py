"""
Property-based tests para AuthMiddleware y decoradores de autenticación.

Este módulo implementa property tests usando Hypothesis para validar:
- Property 11: Protected endpoints require authentication
- Property 27: Role-based access control
- Property 47: Blacklist verification in token validation

Valida Requirements: 3.1-3.6, 14.4, 14.5, 20.4
"""

from datetime import UTC, datetime

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.repositorios.token_blacklist_repository import TokenBlacklistRepository
from app.seguridad.auth_middleware import AuthMiddleware, require_auth, require_role
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager


# Estrategias de Hypothesis
@st.composite
def valid_username(draw):
    """Genera usernames válidos."""
    return draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
            min_size=3,
            max_size=20,
        )
    )


@st.composite
def valid_email(draw):
    """Genera emails válidos."""
    local = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._-"
            ),
            min_size=1,
            max_size=20,
        )
    )
    domain = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"
            ),
            min_size=1,
            max_size=20,
        )
    )
    tld = draw(st.sampled_from(["com", "org", "net", "edu"]))
    return f"{local}@{domain}.{tld}"


@st.composite
def role_name(draw):
    """Genera nombres de roles válidos."""
    return draw(st.sampled_from(["ADMIN", "MECANICO", "RECEPCIONISTA", "SOLO_LECTURA"]))


# Fixtures
@pytest.fixture(scope="function")
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
        refresh_token_expire_days=7,
    )


@pytest.fixture
def password_hasher():
    """Crea un hasher de contraseñas."""
    return PasswordHasher(cost_factor=4)


@pytest.fixture
def app_factory(db_session, token_manager):
    """Factory para crear aplicaciones FastAPI con diferentes configuraciones."""

    def create_app(protected_paths=None, role_requirements=None):
        """
        Crea una aplicación FastAPI con endpoints configurables.

        Args:
            protected_paths: Lista de paths que requieren autenticación
            role_requirements: Dict de {path: [roles]} para control de acceso
        """
        app = FastAPI()

        # Factory que retorna la misma sesión de test
        def test_db_factory():
            return db_session

        # Agregar middleware
        app.add_middleware(
            AuthMiddleware, token_manager=token_manager, db_session_factory=test_db_factory
        )

        # Endpoint público
        @app.get("/public")
        async def public_endpoint():
            return {"message": "Public access"}

        # Endpoints protegidos dinámicos
        if protected_paths:
            for path in protected_paths:

                @app.get(path)
                @require_auth
                async def protected_endpoint(request: Request):
                    user = request.state.user
                    return {"message": f"Protected access for {user.username}", "path": path}

        # Endpoints con roles dinámicos
        if role_requirements:
            for path, roles in role_requirements.items():

                @app.get(path)
                @require_auth
                @require_role(*roles)
                async def role_endpoint(request: Request):
                    user = request.state.user
                    return {"message": f"Role access for {user.username}", "path": path}

        return app

    return create_app


def create_user_with_roles(db_session, username, email, roles, password_hasher):
    """Helper para crear usuarios con roles específicos."""
    # Crear roles si no existen
    existing_roles = {}
    for role_name in ["ADMIN", "MECANICO", "RECEPCIONISTA", "SOLO_LECTURA"]:
        role = db_session.query(Role).filter(Role.name == role_name).first()
        if not role:
            role = Role(name=role_name, description=f"{role_name} role")
            db_session.add(role)
            db_session.commit()
            db_session.refresh(role)
        existing_roles[role_name] = role

    # Crear usuario
    user = User(
        username=username,
        email=email,
        password_hash=password_hasher.hash_password("password123"),
        is_active=True,
        is_migrated=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Asignar roles
    for role_name in roles:
        if role_name in existing_roles:
            user_role = UserRole(user_id=user.id, role_id=existing_roles[role_name].id)
            db_session.add(user_role)

    db_session.commit()
    db_session.refresh(user)

    return user


class TestProperty11_ProtectedEndpointsRequireAuthentication:
    """
    Property 11: Protected endpoints require authentication

    Valida Requirements: 3.1-3.6

    Propiedad: FOR ALL endpoints protegidos con @require_auth,
               requests sin token válido MUST retornar HTTP 401
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
    @given(
        username=valid_username(),
        email=valid_email(),
        path_suffix=st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/_-"
            ),
            min_size=1,
            max_size=20,
        ),
    )
    def test_protected_endpoint_rejects_unauthenticated_requests(
        self, db_session, token_manager, password_hasher, app_factory, username, email, path_suffix
    ):
        """
        Property: Cualquier endpoint protegido rechaza requests sin autenticación.

        Valida que todos los endpoints con @require_auth retornan 401
        cuando se accede sin token válido.
        """
        # Sanitizar path
        path = f"/protected/{path_suffix.replace('//', '/').strip('/')}"
        assume(len(path) < 100)  # Evitar paths demasiado largos

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=[path])
        client = TestClient(app)

        # Intentar acceder sin token
        response = client.get(path)

        # Verificar que retorna 401
        assert (
            response.status_code == 401
        ), f"Protected endpoint {path} should return 401 without token, got {response.status_code}"
        assert "detail" in response.json()

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
    @given(
        username=valid_username(),
        email=valid_email(),
        invalid_token=st.text(
            alphabet=st.characters(min_codepoint=33, max_codepoint=126), min_size=10, max_size=100
        ),
    )
    def test_protected_endpoint_rejects_invalid_tokens(
        self,
        db_session,
        token_manager,
        password_hasher,
        app_factory,
        username,
        email,
        invalid_token,
    ):
        """
        Property: Cualquier endpoint protegido rechaza tokens inválidos.

        Valida que tokens malformados o inválidos son rechazados con 401.
        """
        # Evitar colisiones con tokens válidos
        assume(not invalid_token.startswith("eyJ"))

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=["/protected/test"])
        client = TestClient(app)

        # Intentar acceder con token inválido
        response = client.get(
            "/protected/test", headers={"Authorization": f"Bearer {invalid_token}"}
        )

        # Verificar que retorna 401
        assert (
            response.status_code == 401
        ), f"Protected endpoint should reject invalid token, got {response.status_code}"

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15)
    @given(username=valid_username(), email=valid_email())
    def test_protected_endpoint_accepts_valid_tokens(
        self, db_session, token_manager, password_hasher, app_factory, username, email
    ):
        """
        Property: Cualquier endpoint protegido acepta tokens válidos.

        Valida que tokens JWT válidos permiten acceso a endpoints protegidos.
        """
        # Crear usuario
        user = create_user_with_roles(db_session, username, email, [], password_hasher)

        # Generar token válido
        token = token_manager.generate_access_token(user)

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=["/protected/test"])
        client = TestClient(app)

        # Intentar acceder con token válido
        response = client.get("/protected/test", headers={"Authorization": f"Bearer {token}"})

        # Verificar que retorna 200
        assert (
            response.status_code == 200
        ), f"Protected endpoint should accept valid token, got {response.status_code}"
        assert username in response.json()["message"]


class TestProperty27_RoleBasedAccessControl:
    """
    Property 27: Role-based access control

    Valida Requirements: 14.4, 14.5

    Propiedad: FOR ALL endpoints protegidos con @require_role(*roles),
               ONLY usuarios con al menos uno de los roles especificados
               MUST tener acceso (HTTP 200), otros MUST recibir HTTP 403
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=20)
    @given(
        username=valid_username(),
        email=valid_email(),
        required_role=role_name(),
        user_roles=st.lists(role_name(), min_size=0, max_size=3, unique=True),
    )
    def test_role_based_access_control(
        self,
        db_session,
        token_manager,
        password_hasher,
        app_factory,
        username,
        email,
        required_role,
        user_roles,
    ):
        """
        Property: Endpoints con @require_role solo permiten acceso a usuarios con rol correcto.

        Valida que:
        - Usuarios CON el rol requerido reciben 200
        - Usuarios SIN el rol requerido reciben 403
        """
        # Crear usuario con roles específicos
        user = create_user_with_roles(db_session, username, email, user_roles, password_hasher)

        # Generar token
        token = token_manager.generate_access_token(user)

        # Crear app con endpoint que requiere rol específico
        app = app_factory(role_requirements={"/role-test": [required_role]})
        client = TestClient(app)

        # Intentar acceder
        response = client.get("/role-test", headers={"Authorization": f"Bearer {token}"})

        # Verificar comportamiento esperado
        has_required_role = required_role in user_roles

        if has_required_role:
            assert (
                response.status_code == 200
            ), f"User with role {required_role} should have access, got {response.status_code}"
            assert username in response.json()["message"]
        else:
            assert (
                response.status_code == 403
            ), f"User without role {required_role} should be forbidden, got {response.status_code}"
            assert "Insufficient permissions" in response.json()["detail"]

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15)
    @given(
        username=valid_username(),
        email=valid_email(),
        required_roles=st.lists(role_name(), min_size=2, max_size=3, unique=True),
        user_roles=st.lists(role_name(), min_size=0, max_size=3, unique=True),
    )
    def test_multiple_roles_access_control(
        self,
        db_session,
        token_manager,
        password_hasher,
        app_factory,
        username,
        email,
        required_roles,
        user_roles,
    ):
        """
        Property: Endpoints con múltiples roles permiten acceso si usuario tiene AL MENOS UNO.

        Valida que @require_role("ADMIN", "MECANICO") permite acceso si el usuario
        tiene ADMIN O MECANICO (o ambos).
        """
        # Crear usuario con roles específicos
        user = create_user_with_roles(db_session, username, email, user_roles, password_hasher)

        # Generar token
        token = token_manager.generate_access_token(user)

        # Crear app con endpoint que requiere múltiples roles
        app = app_factory(role_requirements={"/multi-role": required_roles})
        client = TestClient(app)

        # Intentar acceder
        response = client.get("/multi-role", headers={"Authorization": f"Bearer {token}"})

        # Verificar comportamiento esperado
        has_any_required_role = any(role in user_roles for role in required_roles)

        if has_any_required_role:
            assert (
                response.status_code == 200
            ), f"User with any of {required_roles} should have access, got {response.status_code}"
        else:
            assert (
                response.status_code == 403
            ), f"User without any of {required_roles} should be forbidden, got {response.status_code}"

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    @given(username=valid_username(), email=valid_email(), required_role=role_name())
    def test_role_check_requires_authentication(
        self,
        db_session,
        token_manager,
        password_hasher,
        app_factory,
        username,
        email,
        required_role,
    ):
        """
        Property: Endpoints con @require_role también requieren autenticación.

        Valida que no se puede acceder a endpoints con roles sin estar autenticado.
        """
        # Crear app con endpoint que requiere rol
        app = app_factory(role_requirements={"/role-test": [required_role]})
        client = TestClient(app)

        # Intentar acceder sin token
        response = client.get("/role-test")

        # Verificar que retorna 401 (no 403)
        assert (
            response.status_code == 401
        ), f"Role-protected endpoint without auth should return 401, got {response.status_code}"


class TestProperty47_BlacklistVerificationInTokenValidation:
    """
    Property 47: Blacklist verification in token validation

    Valida Requirements: 20.4

    Propiedad: FOR ALL tokens JWT en blacklist,
               requests usando esos tokens MUST ser rechazados con HTTP 401,
               EVEN IF el token es válido y no ha expirado
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15)
    @given(
        username=valid_username(),
        email=valid_email(),
        blacklist_reason=st.sampled_from(
            ["logout", "user_deactivated", "security_breach", "manual_revoke"]
        ),
    )
    def test_blacklisted_tokens_are_rejected(
        self,
        db_session,
        token_manager,
        password_hasher,
        app_factory,
        username,
        email,
        blacklist_reason,
    ):
        """
        Property: Tokens en blacklist son rechazados incluso si son válidos.

        Valida que el middleware verifica la blacklist antes de permitir acceso.
        """
        # Crear usuario
        user = create_user_with_roles(db_session, username, email, [], password_hasher)

        # Generar token válido
        token = token_manager.generate_access_token(user)
        payload = token_manager.decode_token(token)

        # Agregar token a blacklist
        blacklist_repo = TokenBlacklistRepository(db_session)
        blacklist_repo.add_to_blacklist(
            jti=payload["jti"],
            token_type="access",
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            reason=blacklist_reason,
        )

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=["/protected/test"])
        client = TestClient(app)

        # Intentar acceder con token blacklisted
        response = client.get("/protected/test", headers={"Authorization": f"Bearer {token}"})

        # Verificar que retorna 401
        assert (
            response.status_code == 401
        ), f"Blacklisted token should be rejected, got {response.status_code}"
        assert "revoked" in response.json()["detail"].lower()

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=15)
    @given(username=valid_username(), email=valid_email())
    def test_non_blacklisted_tokens_are_accepted(
        self, db_session, token_manager, password_hasher, app_factory, username, email
    ):
        """
        Property: Tokens NO en blacklist son aceptados si son válidos.

        Valida que tokens válidos que no están en blacklist funcionan correctamente.
        """
        # Crear usuario
        user = create_user_with_roles(db_session, username, email, [], password_hasher)

        # Generar token válido
        token = token_manager.generate_access_token(user)

        # NO agregar a blacklist

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=["/protected/test"])
        client = TestClient(app)

        # Intentar acceder con token válido
        response = client.get("/protected/test", headers={"Authorization": f"Bearer {token}"})

        # Verificar que retorna 200
        assert (
            response.status_code == 200
        ), f"Valid non-blacklisted token should be accepted, got {response.status_code}"

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    @given(
        username=valid_username(),
        email=valid_email(),
        roles=st.lists(role_name(), min_size=1, max_size=2, unique=True),
    )
    def test_blacklist_check_happens_before_role_check(
        self, db_session, token_manager, password_hasher, app_factory, username, email, roles
    ):
        """
        Property: Verificación de blacklist ocurre ANTES de verificación de roles.

        Valida que tokens blacklisted son rechazados incluso si el usuario
        tiene los roles correctos.
        """
        # Crear usuario con roles
        user = create_user_with_roles(db_session, username, email, roles, password_hasher)

        # Generar token válido
        token = token_manager.generate_access_token(user)
        payload = token_manager.decode_token(token)

        # Agregar token a blacklist
        blacklist_repo = TokenBlacklistRepository(db_session)
        blacklist_repo.add_to_blacklist(
            jti=payload["jti"],
            token_type="access",
            user_id=user.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            reason="test",
        )

        # Crear app con endpoint que requiere uno de los roles del usuario
        app = app_factory(role_requirements={"/role-test": [roles[0]]})
        client = TestClient(app)

        # Intentar acceder con token blacklisted
        response = client.get("/role-test", headers={"Authorization": f"Bearer {token}"})

        # Verificar que retorna 401 (no 403)
        # Esto confirma que la blacklist se verifica antes de los roles
        assert (
            response.status_code == 401
        ), f"Blacklisted token should return 401 even with correct roles, got {response.status_code}"
        assert "revoked" in response.json()["detail"].lower()


class TestProperty47_InactiveUserTokensRejected:
    """
    Property adicional: Tokens de usuarios inactivos son rechazados.

    Complementa Property 47 validando que usuarios desactivados no pueden
    usar tokens válidos.
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=10)
    @given(username=valid_username(), email=valid_email())
    def test_inactive_user_tokens_are_rejected(
        self, db_session, token_manager, password_hasher, app_factory, username, email
    ):
        """
        Property: Tokens de usuarios inactivos son rechazados.

        Valida que desactivar un usuario invalida sus tokens existentes.
        """
        # Crear usuario activo
        user = create_user_with_roles(db_session, username, email, [], password_hasher)

        # Generar token válido
        token = token_manager.generate_access_token(user)

        # Desactivar usuario
        user.is_active = False
        db_session.commit()
        db_session.refresh(user)

        # Crear app con endpoint protegido
        app = app_factory(protected_paths=["/protected/test"])
        client = TestClient(app)

        # Intentar acceder con token de usuario inactivo
        response = client.get("/protected/test", headers={"Authorization": f"Bearer {token}"})

        # Verificar que retorna 401
        assert (
            response.status_code == 401
        ), f"Token of inactive user should be rejected, got {response.status_code}"
        assert "inactive" in response.json()["detail"].lower()

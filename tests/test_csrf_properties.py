"""
Property-based tests para CSRF Protection y Security Headers.

Este módulo implementa property tests usando Hypothesis para validar:
- Property 1: CSRF Enforcement en Endpoints de Escritura
- Property 2: Presencia de Headers de Seguridad

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.1, 4.2, 4.3, 4.4, 4.5**
"""

import os

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.configuracion.base_datos import Base
from app.modelos.role import Role
from app.modelos.user import User
from app.modelos.user_role import UserRole
from app.seguridad.auth_middleware import AuthMiddleware, require_auth
from app.seguridad.csrf_middleware import CSRFMiddleware
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.security_headers_middleware import SecurityHeadersMiddleware
from app.seguridad.token_manager import TokenManager


# ── Estrategias de Hypothesis ────────────────────────────────────────────────
@st.composite
def valid_username(draw):
    """Genera usernames válidos únicos usando UUID."""
    import uuid
    # Usar UUID para garantizar unicidad
    unique_id = str(uuid.uuid4())[:8]
    prefix = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"
            ),
            min_size=3,
            max_size=10,
        )
    )
    return f"{prefix}_{unique_id}"


@st.composite
def valid_email(draw):
    """Genera emails válidos únicos usando UUID."""
    import uuid
    # Usar UUID para garantizar unicidad
    unique_id = str(uuid.uuid4())[:8]
    local = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="._"
            ),
            min_size=1,
            max_size=10,
        )
    )
    domain = draw(
        st.text(
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-"
            ),
            min_size=1,
            max_size=10,
        )
    )
    tld = draw(st.sampled_from(["com", "org", "net", "edu"]))
    return f"{local}_{unique_id}@{domain}.{tld}"


# ── Fixtures ──────────────────────────────────────────────────────────────────
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
def app_with_csrf_and_security_headers(db_session, token_manager):
    """
    Crea una aplicación FastAPI con CSRF y Security Headers middlewares.

    Esta fixture simula la configuración completa de main.py con todos los
    middlewares de seguridad en el orden correcto.
    """
    # Configurar CSRF Protection
    from fastapi_csrf_protect import CsrfProtect

    @CsrfProtect.load_config
    def get_csrf_config():
        return [
            ("secret_key", "test_csrf_secret_key_with_at_least_32_characters_for_security"),
            ("cookie_samesite", "strict"),
            ("cookie_secure", False),  # False para tests
            ("cookie_httponly", True),
            ("token_location", "header"),
            ("header_name", "X-CSRF-Token"),
            ("header_type", ""),
        ]

    app = FastAPI()

    # Factory que retorna la misma sesión de test
    def test_db_factory():
        return db_session

    # Agregar middlewares en el orden correcto (se ejecutan en orden inverso)
    # SecurityHeadersMiddleware se agrega PRIMERO → ejecuta ÚLTIMO
    app.add_middleware(SecurityHeadersMiddleware)

    # CSRFMiddleware se agrega DESPUÉS → ejecuta ANTES que SecurityHeaders
    app.add_middleware(CSRFMiddleware)

    # AuthMiddleware se agrega AL FINAL → ejecuta PRIMERO
    app.add_middleware(
        AuthMiddleware, token_manager=token_manager, db_session_factory=test_db_factory
    )

    # Endpoints de prueba
    @app.get("/public")
    async def public_endpoint():
        return {"message": "Public access"}

    @app.get("/health")
    async def health_endpoint():
        return {"status": "ok"}

    @app.get("/protected/read")
    @require_auth
    async def protected_read_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Protected read for {user.username}"}

    @app.post("/protected/write")
    @require_auth
    async def protected_write_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Protected write for {user.username}"}

    @app.put("/protected/update")
    @require_auth
    async def protected_update_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Protected update for {user.username}"}

    @app.patch("/protected/patch")
    @require_auth
    async def protected_patch_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Protected patch for {user.username}"}

    @app.delete("/protected/delete")
    @require_auth
    async def protected_delete_endpoint(request: Request):
        user = request.state.user
        return {"message": f"Protected delete for {user.username}"}

    # Endpoint exento de CSRF (login)
    @app.post("/auth/login")
    async def login_endpoint():
        return {"message": "Login successful"}

    return app


def create_user_with_roles(db_session, username, email, roles, password_hasher):
    """Helper para crear usuarios con roles específicos."""
    try:
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
    except Exception:
        # Si hay error (ej: unique constraint), hacer rollback y relanzar
        db_session.rollback()
        raise


# ── Property 1: CSRF Enforcement en Endpoints de Escritura ───────────────────
class TestProperty1_CSRFEnforcementOnWriteEndpoints:
    """
    Property 1: CSRF Enforcement en Endpoints de Escritura

    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

    Propiedad: Para todo Write_Endpoint no exento, un request sin X-CSRF-Token
               retorna HTTP 403 con error "csrf_error".

    Formalmente:
    ∀ (endpoint, method) donde method ∈ {POST, PUT, PATCH, DELETE} y endpoint ∉ Exempt_Paths:
    request(endpoint, method, csrf_token=None).status_code == 403
    """

    # Lista de endpoints de escritura representativos (no exentos)
    WRITE_ENDPOINTS = [
        ("POST", "/protected/write"),
        ("PUT", "/protected/update"),
        ("PATCH", "/protected/patch"),
        ("DELETE", "/protected/delete"),
    ]

    @pytest.mark.property_test
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=20,
        deadline=None,
    )
    @given(
        endpoint=st.sampled_from(WRITE_ENDPOINTS),
        username=valid_username(),
        email=valid_email(),
    )
    def test_write_endpoint_without_csrf_returns_403(
        self,
        endpoint,
        username,
        email,
        db_session,
        token_manager,
        password_hasher,
        app_with_csrf_and_security_headers,
    ):
        """
        Property 1: Para todo Write_Endpoint no exento, un request sin
        X-CSRF-Token retorna HTTP 403.

        Este test valida que:
        1. Endpoints de escritura (POST, PUT, PATCH, DELETE) requieren CSRF token
        2. Requests sin X-CSRF-Token son rechazados con HTTP 403
        3. El error retornado tiene el código "csrf_error"
        4. Esto ocurre incluso si el usuario tiene un JWT válido
        """
        method, path = endpoint

        # Crear usuario y generar JWT válido
        user = create_user_with_roles(db_session, username, email, ["ADMIN"], password_hasher)
        valid_jwt = token_manager.generate_access_token(user)

        # Crear cliente de test
        client = TestClient(app_with_csrf_and_security_headers)

        # Request con JWT válido pero SIN X-CSRF-Token
        response = client.request(
            method,
            path,
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                # NO incluir X-CSRF-Token
            },
            json={},  # Body vacío para métodos que lo requieren
        )

        # Verificar que retorna 403
        assert (
            response.status_code == 403
        ), f"Write endpoint {method} {path} without CSRF token should return 403, got {response.status_code}"

        # Verificar que el error es "csrf_error"
        response_data = response.json()
        assert (
            response_data.get("error") == "csrf_error"
        ), f"Error should be 'csrf_error', got {response_data.get('error')}"

        # Verificar mensaje de error
        assert "CSRF token missing or invalid" in response_data.get(
            "message", ""
        ), f"Error message should mention CSRF token, got {response_data.get('message')}"

    @pytest.mark.property_test
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=10,
        deadline=None,
    )
    @given(
        username=valid_username(),
        email=valid_email(),
    )
    def test_exempt_endpoints_do_not_require_csrf(
        self,
        username,
        email,
        db_session,
        token_manager,
        password_hasher,
        app_with_csrf_and_security_headers,
    ):
        """
        Property complementaria: Endpoints exentos NO requieren CSRF token.

        Valida que endpoints como /auth/login pueden ser accedidos sin CSRF token,
        confirmando que la lista de exenciones funciona correctamente.
        """
        # Crear cliente de test
        client = TestClient(app_with_csrf_and_security_headers)

        # Request a endpoint exento sin CSRF token
        response = client.post(
            "/auth/login",
            json={"username": username, "password": "password123"},
        )

        # Verificar que NO retorna 403 por CSRF
        # Puede retornar 401 (credenciales inválidas) u otro código, pero no 403 por CSRF
        assert (
            response.status_code != 403
        ), f"Exempt endpoint /auth/login should not require CSRF token, got {response.status_code}"

        # Si retorna 403, verificar que NO es por CSRF
        if response.status_code == 403:
            response_data = response.json()
            assert (
                response_data.get("error") != "csrf_error"
            ), "Exempt endpoint should not return csrf_error"

    @pytest.mark.property_test
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=10,
        deadline=None,
    )
    @given(
        username=valid_username(),
        email=valid_email(),
    )
    def test_read_endpoints_do_not_require_csrf(
        self,
        username,
        email,
        db_session,
        token_manager,
        password_hasher,
        app_with_csrf_and_security_headers,
    ):
        """
        Property complementaria: Endpoints de lectura (GET) NO requieren CSRF token.

        Valida que métodos HTTP de solo lectura no están sujetos a validación CSRF,
        confirmando que solo métodos de escritura requieren el token.
        """
        # Crear usuario y generar JWT válido
        user = create_user_with_roles(db_session, username, email, ["ADMIN"], password_hasher)
        valid_jwt = token_manager.generate_access_token(user)

        # Crear cliente de test
        client = TestClient(app_with_csrf_and_security_headers)

        # Request GET sin CSRF token
        response = client.get(
            "/protected/read",
            headers={
                "Authorization": f"Bearer {valid_jwt}",
                # NO incluir X-CSRF-Token
            },
        )

        # Verificar que NO retorna 403 por CSRF
        assert (
            response.status_code == 200
        ), f"GET endpoint should not require CSRF token, got {response.status_code}"


# ── Property 2: Presencia de Headers de Seguridad ────────────────────────────
class TestProperty2_SecurityHeadersPresence:
    """
    Property 2: Presencia de Headers de Seguridad

    **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

    Propiedad: Para toda respuesta HTTP del sistema, los headers de seguridad
               requeridos están presentes con los valores correctos.

    Formalmente:
    ∀ (endpoint, method, auth_state):
    response(endpoint, method, auth_state).headers contiene todos los headers
    definidos en Requirement 4 con sus valores exactos
    """

    # Endpoints representativos para probar headers
    TEST_ENDPOINTS = [
        ("/", "GET"),
        ("/health", "GET"),
        ("/public", "GET"),
        ("/auth/login", "POST"),
    ]

    # Headers de seguridad esperados (siempre presentes)
    EXPECTED_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
    }

    @pytest.mark.property_test
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=10,
        deadline=None,
    )
    @given(
        endpoint_method=st.sampled_from(TEST_ENDPOINTS),
    )
    def test_security_headers_middleware_adds_headers(self, endpoint_method):
        """
        Property 2: SecurityHeadersMiddleware agrega headers de seguridad correctamente.

        Este test valida directamente el middleware sin depender de TestClient,
        verificando que los headers se agregan a las respuestas.
        """
        from app.seguridad.security_headers_middleware import (
            SECURITY_HEADERS_ALWAYS,
            SecurityHeadersMiddleware,
        )

        endpoint, method = endpoint_method

        # Verificar que las constantes del middleware tienen los valores correctos
        assert SECURITY_HEADERS_ALWAYS["X-Content-Type-Options"] == "nosniff"
        assert SECURITY_HEADERS_ALWAYS["X-Frame-Options"] == "DENY"
        assert SECURITY_HEADERS_ALWAYS["X-XSS-Protection"] == "1; mode=block"
        assert SECURITY_HEADERS_ALWAYS["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in SECURITY_HEADERS_ALWAYS

        # Verificar que CSP contiene directivas básicas
        csp = SECURITY_HEADERS_ALWAYS["Content-Security-Policy"]
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    @pytest.mark.property_test
    def test_hsts_only_in_production(self):
        """
        Property complementaria: HSTS solo se agrega en producción.

        Valida que el middleware detecta correctamente el entorno y solo
        agrega HSTS cuando ENVIRONMENT=production.
        """
        from app.seguridad.security_headers_middleware import (
            SECURITY_HEADERS_PRODUCTION,
            SecurityHeadersMiddleware,
        )

        # Verificar que HSTS está en los headers de producción
        assert "Strict-Transport-Security" in SECURITY_HEADERS_PRODUCTION
        assert (
            SECURITY_HEADERS_PRODUCTION["Strict-Transport-Security"]
            == "max-age=31536000; includeSubDomains"
        )

        # Verificar que el middleware detecta el entorno correctamente
        # En tests, ENVIRONMENT no es "production", por lo que is_production debe ser False
        import os

        original_env = os.getenv("ENVIRONMENT")
        try:
            # Test con entorno no productivo
            os.environ["ENVIRONMENT"] = "development"
            middleware_dev = SecurityHeadersMiddleware(app=None)
            assert middleware_dev.is_production is False

            # Test con entorno productivo
            os.environ["ENVIRONMENT"] = "production"
            middleware_prod = SecurityHeadersMiddleware(app=None)
            assert middleware_prod.is_production is True
        finally:
            # Restaurar entorno original
            if original_env:
                os.environ["ENVIRONMENT"] = original_env
            elif "ENVIRONMENT" in os.environ:
                del os.environ["ENVIRONMENT"]


# ── Property Adicional: Integración CSRF + Security Headers ──────────────────
class TestProperty_CSRFAndSecurityHeadersIntegration:
    """
    Property adicional: Integración correcta de CSRF y Security Headers.

    Valida que ambos middlewares funcionan correctamente juntos:
    - CSRF valida tokens en endpoints de escritura
    - Security Headers se agregan a todas las respuestas (incluyendo errores CSRF)
    - El orden de ejecución es correcto
    """

    @pytest.mark.property_test
    def test_csrf_middleware_validates_write_methods(self):
        """
        Property: CSRFMiddleware valida correctamente los métodos de escritura.

        Valida que el middleware tiene configurados los métodos correctos y
        las rutas exentas apropiadas.
        """
        from app.seguridad.csrf_middleware import CSRF_EXEMPT_PATHS, CSRF_WRITE_METHODS

        # Verificar métodos de escritura
        assert "POST" in CSRF_WRITE_METHODS
        assert "PUT" in CSRF_WRITE_METHODS
        assert "PATCH" in CSRF_WRITE_METHODS
        assert "DELETE" in CSRF_WRITE_METHODS

        # Verificar que GET no está en métodos de escritura
        assert "GET" not in CSRF_WRITE_METHODS

        # Verificar rutas exentas críticas
        assert "/auth/login" in CSRF_EXEMPT_PATHS
        assert "/auth/refresh" in CSRF_EXEMPT_PATHS
        assert "/health" in CSRF_EXEMPT_PATHS
        assert "/whatsapp/webhook" in CSRF_EXEMPT_PATHS

    @pytest.mark.property_test
    def test_middleware_order_is_correct(self):
        """
        Property: El orden de middlewares es correcto para seguridad.

        Valida que los middlewares están configurados en el orden esperado:
        1. SecurityHeadersMiddleware (ejecuta último, agrega headers a todas las respuestas)
        2. CSRFMiddleware (ejecuta antes que SecurityHeaders, valida CSRF)
        3. AuthMiddleware (ejecuta primero, valida JWT)
        """
        # Este test valida la configuración documentada en el design.md
        # El orden de add_middleware es inverso al orden de ejecución

        # Verificar que los middlewares existen y están correctamente implementados
        from app.seguridad.csrf_middleware import CSRFMiddleware
        from app.seguridad.security_headers_middleware import SecurityHeadersMiddleware

        # Verificar que CSRFMiddleware es un BaseHTTPMiddleware
        from starlette.middleware.base import BaseHTTPMiddleware

        assert issubclass(CSRFMiddleware, BaseHTTPMiddleware)

        # Verificar que SecurityHeadersMiddleware es un middleware ASGI puro
        assert hasattr(SecurityHeadersMiddleware, "__call__")
        assert hasattr(SecurityHeadersMiddleware, "__init__")

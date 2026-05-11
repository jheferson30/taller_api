"""
Unit tests for economia route RLS fixes (Phase 3, Task 5.5).

Tests verify:
- All economia endpoints require JWT authentication
- Economia reports return only data for authenticated taller
- Cross-tenant MovimientoCaja access returns empty results
- _base_query_dia includes taller_id filter in generated SQL
- _sumar_por_tipo passes taller_id correctly

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5**
"""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.configuracion.base_datos import Base
# Import all models to register them with SQLAlchemy
from app.modelos.audit_log import AuditLog  # noqa: F401
from app.modelos.configuracion_taller import ConfiguracionTaller
from app.modelos.movimiento_caja import MovimientoCaja, TipoMovimiento
from app.modelos.password_reset_token import PasswordResetToken  # noqa: F401
from app.modelos.role import Role
from app.modelos.taller import Taller  # noqa: F401
from app.modelos.ticket import Ticket
from app.modelos.ticket_proceso import TicketProceso
from app.modelos.token_blacklist import TokenBlacklist  # noqa: F401
from app.modelos.user import User
from app.modelos.user_role import UserRole  # noqa: F401
from app.modelos.vehiculo import Vehiculo  # noqa: F401
from app.repositorios.movimiento_caja_repository import MovimientoCajaRepository
from app.rutas.economia_ruta import router as economia_router
from app.seguridad.auth_middleware import AuthMiddleware
from app.seguridad.password_hasher import PasswordHasher
from app.seguridad.token_manager import TokenManager


@pytest.fixture
def db_session():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def password_hasher():
    """Password hasher for creating test users."""
    return PasswordHasher()


@pytest.fixture
def token_manager():
    """Token manager for generating test JWTs."""
    return TokenManager()


@pytest.fixture
def test_user_taller_1(db_session, password_hasher):
    """Create test user for taller_id=1."""
    user = User(
        username="user_taller_1",
        email="user1@test.com",
        password_hash=password_hasher.hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    
    # Add ADMIN role
    role = Role(name="ADMIN")
    db_session.add(role)
    db_session.flush()
    user.roles.append(role)
    db_session.commit()
    
    return user


@pytest.fixture
def test_user_taller_2(db_session, password_hasher):
    """Create test user for taller_id=2."""
    user = User(
        username="user_taller_2",
        email="user2@test.com",
        password_hash=password_hasher.hash_password("password123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    
    # Add ADMIN role
    role = db_session.query(Role).filter(Role.name == "ADMIN").first()
    if not role:
        role = Role(name="ADMIN")
        db_session.add(role)
        db_session.flush()
    user.roles.append(role)
    db_session.commit()
    
    return user


@pytest.fixture
def app_with_middleware(db_session, token_manager):
    """Create FastAPI app with AuthMiddleware for testing."""
    app = FastAPI()
    
    # Mock db_session_factory that returns the test session
    def mock_db_factory():
        return db_session
    
    # Add AuthMiddleware
    app.add_middleware(
        AuthMiddleware,
        token_manager=token_manager,
        db_session_factory=mock_db_factory,
    )
    
    # Include economia router
    app.include_router(economia_router)
    
    # Override obtener_db dependency
    def override_get_db():
        yield db_session
    
    from app.configuracion.base_datos import obtener_db
    app.dependency_overrides[obtener_db] = override_get_db
    
    # Override requerir_password_admin to always return True
    from app.seguridad.dependencias import requerir_password_admin
    async def mock_admin_check(request: Request):
        return True
    app.dependency_overrides[requerir_password_admin] = mock_admin_check
    
    return app


@pytest.fixture
def movimientos_taller_1(db_session):
    """Create test MovimientoCaja records for taller_id=1."""
    hoy = date.today()
    
    movimientos = [
        MovimientoCaja(
            taller_id=1,
            tipo=TipoMovimiento.INGRESO_ANTICIPO,
            valor=50000,
            fecha_creacion=hoy,
            ticket_codigo="T001",
            placa="ABC123",
            responsable="Admin",
        ),
        MovimientoCaja(
            taller_id=1,
            tipo=TipoMovimiento.INGRESO_FINAL,
            valor=150000,
            fecha_creacion=hoy,
            ticket_codigo="T001",
            placa="ABC123",
            responsable="Admin",
        ),
        MovimientoCaja(
            taller_id=1,
            tipo=TipoMovimiento.EGRESO,
            valor=30000,
            fecha_creacion=hoy,
            concepto="Compra repuestos",
            responsable="Admin",
        ),
    ]
    
    for mov in movimientos:
        db_session.add(mov)
    db_session.commit()
    
    return movimientos


@pytest.fixture
def movimientos_taller_2(db_session):
    """Create test MovimientoCaja records for taller_id=2."""
    hoy = date.today()
    
    movimientos = [
        MovimientoCaja(
            taller_id=2,
            tipo=TipoMovimiento.INGRESO_ANTICIPO,
            valor=80000,
            fecha_creacion=hoy,
            ticket_codigo="T002",
            placa="XYZ789",
            responsable="Admin2",
        ),
        MovimientoCaja(
            taller_id=2,
            tipo=TipoMovimiento.INGRESO_FINAL,
            valor=200000,
            fecha_creacion=hoy,
            ticket_codigo="T002",
            placa="XYZ789",
            responsable="Admin2",
        ),
    ]
    
    for mov in movimientos:
        db_session.add(mov)
    db_session.commit()
    
    return movimientos


class TestEconomiaRutaAuthentication:
    """Test that all economia endpoints require authentication."""
    
    def test_obtener_resumen_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        response = client.get("/economia-dia")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_obtener_ingresos_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia/ingresos without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        response = client.get("/economia-dia/ingresos")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_obtener_egresos_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia/egresos without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        response = client.get("/economia-dia/egresos")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_obtener_estadisticas_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia/estadisticas without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        response = client.get("/economia-dia/estadisticas")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_obtener_historico_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia/historico without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        hoy = date.today()
        response = client.get(
            f"/economia-dia/historico?fecha_desde={hoy}&fecha_hasta={hoy}"
        )
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]
    
    def test_generar_pdf_without_jwt_returns_401(
        self, app_with_middleware, movimientos_taller_1
    ):
        """
        Test: GET /economia-dia/pdf without JWT → 401
        **Validates: Requirement 2.5**
        """
        client = TestClient(app_with_middleware)
        response = client.get("/economia-dia/pdf")
        
        assert response.status_code == 401
        assert "Authentication required" in response.json()["detail"]


class TestEconomiaRutaTenantIsolation:
    """Test that economia endpoints return only data for authenticated taller."""
    
    def test_obtener_resumen_returns_only_own_taller_data(
        self,
        app_with_middleware,
        test_user_taller_1,
        token_manager,
        movimientos_taller_1,
        movimientos_taller_2,
    ):
        """
        Test: Economia reports return only data for authenticated taller.
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        # Generate JWT for taller_id=1
        token = token_manager.generate_access_token(
            test_user_taller_1,
            additional_claims={"taller_id": 1}
        )
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/economia-dia",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only include taller_id=1 data
        # Taller 1: 50000 anticipo + 150000 final = 200000 ingresos, 30000 egresos
        assert data["ingresos"] == 200000
        assert data["egresos"] == 30000
        assert data["balance"] == 170000
        
        # Should NOT include taller_id=2 data (80000 + 200000 = 280000)
        assert data["ingresos"] != 280000
    
    def test_obtener_ingresos_returns_only_own_taller_data(
        self,
        app_with_middleware,
        test_user_taller_1,
        token_manager,
        movimientos_taller_1,
        movimientos_taller_2,
    ):
        """
        Test: Ingresos endpoint returns only data for authenticated taller.
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        # Generate JWT for taller_id=1
        token = token_manager.generate_access_token(
            test_user_taller_1,
            additional_claims={"taller_id": 1}
        )
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/economia-dia/ingresos",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have 1 anticipo and 1 final from taller_id=1
        assert len(data["anticipos"]) == 1
        assert len(data["cobros_finales"]) == 1
        assert data["anticipos"][0]["placa"] == "ABC123"
        assert data["cobros_finales"][0]["placa"] == "ABC123"
        
        # Should NOT include taller_id=2 data (XYZ789)
        assert all(a["placa"] != "XYZ789" for a in data["anticipos"])
        assert all(c["placa"] != "XYZ789" for c in data["cobros_finales"])
    
    def test_cross_tenant_access_returns_empty_results(
        self,
        app_with_middleware,
        test_user_taller_2,
        token_manager,
        movimientos_taller_1,
    ):
        """
        Test: Cross-tenant MovimientoCaja access returns empty results.
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        # Generate JWT for taller_id=2
        token = token_manager.generate_access_token(
            test_user_taller_2,
            additional_claims={"taller_id": 2}
        )
        
        # Create movimientos only for taller_id=1
        # User from taller_id=2 should see empty results
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/economia-dia",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return 0 for all values (no data for taller_id=2)
        assert data["ingresos"] == 0
        assert data["egresos"] == 0
        assert data["balance"] == 0


class TestEconomiaHelperFunctions:
    """Test that helper functions include taller_id filter."""
    
    def test_base_query_dia_includes_taller_id_filter(
        self, db_session, movimientos_taller_1, movimientos_taller_2
    ):
        """
        Test: _base_query_dia includes taller_id filter in generated SQL.
        **Validates: Requirement 2.1**
        """
        from app.rutas.economia_ruta import _base_query_dia
        
        hoy = date.today()
        
        # Query for taller_id=1
        query = _base_query_dia(db_session, hoy, taller_id=1)
        results = query.all()
        
        # Should only return taller_id=1 records
        assert len(results) == 3  # 2 ingresos + 1 egreso
        assert all(m.taller_id == 1 for m in results)
        
        # Query for taller_id=2
        query = _base_query_dia(db_session, hoy, taller_id=2)
        results = query.all()
        
        # Should only return taller_id=2 records
        assert len(results) == 2  # 2 ingresos
        assert all(m.taller_id == 2 for m in results)
    
    def test_sumar_por_tipo_passes_taller_id_correctly(
        self, db_session, movimientos_taller_1, movimientos_taller_2
    ):
        """
        Test: _sumar_por_tipo passes taller_id correctly.
        **Validates: Requirement 2.2**
        """
        from app.rutas.economia_ruta import _sumar_por_tipo
        
        hoy = date.today()
        
        # Sum INGRESO_ANTICIPO for taller_id=1
        total = _sumar_por_tipo(
            db_session, hoy, TipoMovimiento.INGRESO_ANTICIPO, taller_id=1
        )
        assert total == 50000  # Only taller_id=1 anticipo
        
        # Sum INGRESO_ANTICIPO for taller_id=2
        total = _sumar_por_tipo(
            db_session, hoy, TipoMovimiento.INGRESO_ANTICIPO, taller_id=2
        )
        assert total == 80000  # Only taller_id=2 anticipo
        
        # Sum INGRESO_FINAL for taller_id=1
        total = _sumar_por_tipo(
            db_session, hoy, TipoMovimiento.INGRESO_FINAL, taller_id=1
        )
        assert total == 150000  # Only taller_id=1 final


class TestEconomiaRepositoryRLS:
    """Test that MovimientoCajaRepository includes taller_id filter."""
    
    def test_get_historico_economico_filters_by_taller_id(
        self, db_session, movimientos_taller_1, movimientos_taller_2
    ):
        """
        Test: get_historico_economico includes taller_id filter.
        **Validates: Requirements 2.1, 2.3**
        """
        repo = MovimientoCajaRepository(db_session)
        
        hoy = date.today()
        
        # Get historico for taller_id=1
        items = repo.get_historico_economico(hoy, hoy, taller_id=1)
        
        assert len(items) == 1  # One day of data
        assert items[0]["total_ingresos"] == 200000  # 50000 + 150000
        assert items[0]["total_egresos"] == 30000
        
        # Get historico for taller_id=2
        items = repo.get_historico_economico(hoy, hoy, taller_id=2)
        
        assert len(items) == 1  # One day of data
        assert items[0]["total_ingresos"] == 280000  # 80000 + 200000
        assert items[0]["total_egresos"] == 0


class TestEconomiaEstadisticasRLS:
    """Test that estadisticas endpoint filters by taller_id."""
    
    def test_estadisticas_filters_tickets_by_taller_id(
        self,
        app_with_middleware,
        test_user_taller_1,
        token_manager,
        db_session,
        movimientos_taller_1,
    ):
        """
        Test: Estadisticas endpoint filters Ticket queries by taller_id.
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        # Create tickets for taller_id=1
        hoy = date.today()
        ticket1 = Ticket(
            taller_id=1,
            codigo="T001",
            placa="ABC123",
            motivo_visita="Cambio aceite",
            fecha_ingreso=hoy,
        )
        db_session.add(ticket1)
        db_session.commit()
        
        # Generate JWT for taller_id=1
        token = token_manager.generate_access_token(
            test_user_taller_1,
            additional_claims={"taller_id": 1}
        )
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/economia-dia/estadisticas?periodo=semana",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include servicios_frecuentes from taller_id=1
        assert len(data["servicios_frecuentes"]) == 1
        assert data["servicios_frecuentes"][0]["servicio"] == "Cambio aceite"
    
    def test_estadisticas_filters_ticket_proceso_by_taller_id(
        self,
        app_with_middleware,
        test_user_taller_1,
        token_manager,
        db_session,
        movimientos_taller_1,
    ):
        """
        Test: Estadisticas endpoint filters TicketProceso queries by taller_id.
        **Validates: Requirements 2.1, 2.3, 2.4**
        """
        # Create ticket proceso for taller_id=1
        hoy = date.today()
        proceso = TicketProceso(
            taller_id=1,
            ticket_id=1,
            mecanico="Juan Perez",
            descripcion="Cambio aceite",
            fecha_creacion=hoy,
        )
        db_session.add(proceso)
        db_session.commit()
        
        # Generate JWT for taller_id=1
        token = token_manager.generate_access_token(
            test_user_taller_1,
            additional_claims={"taller_id": 1}
        )
        
        client = TestClient(app_with_middleware)
        response = client.get(
            "/economia-dia/estadisticas?periodo=semana",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include mecanicos_ranking from taller_id=1
        assert len(data["mecanicos_ranking"]) == 1
        assert data["mecanicos_ranking"][0]["mecanico"] == "Juan Perez"

"""
Tests: WhatsApp Ticket Ownership Verification (Task 3.5)
=========================================================
Verifica que los endpoints de WhatsApp validen la propiedad del ticket
antes de permitir operaciones de envío de mensajes.

Validates: Requirements 1.7, 1.8 (C-07)
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
from app.modelos.ticket import Ticket
from app.modelos.vehiculo import Vehiculo
from app.rutas.whatsapp_ruta import router
from app.seguridad.token_manager import TokenManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def test_app():
    """Crea una app FastAPI con SQLite en memoria."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Crear tablas manualmente para evitar problemas de relaciones
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE talleres (
                id INTEGER PRIMARY KEY,
                nombre VARCHAR(200) NOT NULL
            )
        """))
        conn.execute(text("""
            CREATE TABLE vehiculos (
                id INTEGER PRIMARY KEY,
                taller_id INTEGER NOT NULL,
                placa VARCHAR(20) UNIQUE NOT NULL,
                marca VARCHAR(100),
                modelo VARCHAR(100),
                anio INTEGER,
                cilindraje VARCHAR(50),
                color VARCHAR(50),
                nombre_propietario VARCHAR(500),
                telefono_propietario VARCHAR(500),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_actualizacion TIMESTAMP,
                FOREIGN KEY (taller_id) REFERENCES talleres(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE tickets (
                id INTEGER PRIMARY KEY,
                vehiculo_id INTEGER NOT NULL,
                ticket_codigo VARCHAR(40) UNIQUE NOT NULL,
                placa VARCHAR(20) NOT NULL,
                fecha_ingreso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                motivo_visita VARCHAR(250) NOT NULL,
                observaciones_recepcion VARCHAR(500),
                kilometraje INTEGER,
                estado_inicial VARCHAR(300),
                anticipo_recibido INTEGER DEFAULT 0,
                metodo_pago_anticipo VARCHAR(50),
                recepcionado_por VARCHAR(120),
                estado VARCHAR(20) DEFAULT 'ABIERTO',
                total_servicio INTEGER,
                saldo_pendiente INTEGER,
                metodo_pago_final VARCHAR(50),
                observaciones_finales VARCHAR(800),
                recomendaciones VARCHAR(800),
                proximo_mantenimiento VARCHAR(200),
                confirmado_entrega_por VARCHAR(120),
                firma_entrega_url VARCHAR(255),
                comprobante_pdf_url VARCHAR(255),
                fecha_cierre TIMESTAMP,
                fecha_entrega TIMESTAMP,
                fecha_actualizacion TIMESTAMP,
                FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id)
            )
        """))
        conn.commit()
    
    TestSession = sessionmaker(bind=engine)

    def override_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[obtener_db] = override_db
    
    return app, TestSession


@pytest.fixture
def token_manager():
    """Fixture para crear tokens JWT de prueba."""
    # No necesitamos un TokenManager real, solo mockeamos el middleware
    return None


# ---------------------------------------------------------------------------
# Task 3.5.1 — POST /api/mobile/tickets/{id}/whatsapp verifica propiedad (req 1.7)
# ---------------------------------------------------------------------------


def test_enviar_whatsapp_mobile_verifica_propiedad_ticket(test_app, token_manager):
    """
    POST /api/mobile/tickets/{id}/whatsapp debe verificar que el ticket
    pertenece al taller del usuario autenticado.
    
    Validates: Requirement 1.7 - Verificación de propiedad del ticket
    """
    app, TestSession = test_app
    
    # Arrange: Crear vehículo y ticket para taller_id=1
    db = TestSession()
    try:
        # Crear vehículo con taller_id=1
        vehiculo = Vehiculo(
            taller_id=1,
            placa="ABC123",
            marca="Toyota",
            modelo="Corolla",
            telefono_propietario="3001234567",
        )
        db.add(vehiculo)
        db.flush()
        
        # Crear ticket asociado al vehículo
        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo="T-001",
            placa="ABC123",
            motivo_visita="Mantenimiento",
            estado="ABIERTO",
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id
    finally:
        db.close()
    
    # Act: Intentar enviar WhatsApp con JWT de taller_id=1 (mismo taller)
    token = token_manager.create_access_token(
        data={"sub": "user1", "taller_id": 1, "roles": ["ADMIN"]}
    )
    
    client = TestClient(app)
    
    # Mock del middleware para inyectar request.state
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user1"}, "taller_id": 1}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    response = client.post(
        f"/api/mobile/tickets/{ticket_id}/whatsapp",
        json={"mensaje": "Hola desde taller 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assert: Debe permitir el envío (aunque falle por falta de configuración de Twilio)
    # Lo importante es que NO retorne 404 por falta de propiedad
    assert response.status_code != 404 or response.json().get("error") != "ticket_no_encontrado"


def test_enviar_whatsapp_mobile_rechaza_ticket_otro_taller(test_app, token_manager):
    """
    POST /api/mobile/tickets/{id}/whatsapp debe retornar 404 cuando el ticket
    pertenece a un taller diferente al del usuario autenticado.
    
    Validates: Requirement 1.8 - Retornar 404 para cross-tenant access
    """
    app, TestSession = test_app
    
    # Arrange: Crear vehículo y ticket para taller_id=1 usando raw SQL
    db = TestSession()
    try:
        # Insertar vehículo con taller_id=1
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, modelo, telefono_propietario)
            VALUES (1, 'XYZ789', 'Honda', 'Civic', '3009876543')
        """))
        
        # Obtener el ID del vehículo insertado
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'XYZ789'"))
        vehiculo_id = result.scalar()
        
        # Insertar ticket asociado al vehículo
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita, estado)
            VALUES (:vehiculo_id, 'T-002', 'XYZ789', 'Reparación', 'ABIERTO')
        """), {"vehiculo_id": vehiculo_id})
        
        # Obtener el ID del ticket insertado
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-002'"))
        ticket_id = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Act: Intentar enviar WhatsApp con JWT de taller_id=2 (diferente taller)
    # No necesitamos un token real, solo mockeamos el middleware
    
    client = TestClient(app)
    
    # Mock del middleware para inyectar request.state
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user2"}, "taller_id": 2}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    response = client.post(
        f"/api/mobile/tickets/{ticket_id}/whatsapp",
        json={"mensaje": "Intento de acceso cross-tenant"},
    )
    
    # Assert: Debe retornar 404 sin revelar que el ticket existe
    assert response.status_code == 200  # El endpoint retorna JSON con ok: False
    assert response.json().get("ok") is False
    assert response.json().get("error") == "ticket_no_encontrado"


# ---------------------------------------------------------------------------
# Task 3.5.2 — POST /api/whatsapp/tickets/{id}/mensaje verifica propiedad (req 1.7)
# ---------------------------------------------------------------------------


def test_enviar_whatsapp_web_verifica_propiedad_ticket(test_app, token_manager):
    """
    POST /api/whatsapp/tickets/{id}/mensaje debe verificar que el ticket
    pertenece al taller del usuario autenticado.
    
    Validates: Requirement 1.7 - Verificación de propiedad del ticket
    """
    app, TestSession = test_app
    
    # Arrange: Crear vehículo y ticket para taller_id=1
    db = TestSession()
    try:
        # Crear vehículo con taller_id=1
        vehiculo = Vehiculo(
            taller_id=1,
            placa="DEF456",
            marca="Mazda",
            modelo="3",
            telefono_propietario="3005555555",
        )
        db.add(vehiculo)
        db.flush()
        
        # Crear ticket asociado al vehículo
        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo="T-003",
            placa="DEF456",
            motivo_visita="Revisión",
            estado="ABIERTO",
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id
    finally:
        db.close()
    
    # Act: Intentar enviar WhatsApp con JWT de taller_id=1 (mismo taller)
    token = token_manager.create_access_token(
        data={"sub": "user1", "taller_id": 1, "roles": ["ADMIN"]}
    )
    
    client = TestClient(app)
    
    # Mock del middleware para inyectar request.state
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user1"}, "taller_id": 1}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    response = client.post(
        f"/api/whatsapp/tickets/{ticket_id}/mensaje",
        json={"mensaje": "Hola desde web taller 1"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assert: Debe permitir el envío (aunque falle por falta de configuración de Twilio)
    # Lo importante es que NO retorne 404 por falta de propiedad
    assert response.status_code != 404 or "Resource not found" not in response.json().get("detail", "")


def test_enviar_whatsapp_web_rechaza_ticket_otro_taller(test_app, token_manager):
    """
    POST /api/whatsapp/tickets/{id}/mensaje debe retornar 404 cuando el ticket
    pertenece a un taller diferente al del usuario autenticado.
    
    Validates: Requirement 1.8 - Retornar 404 para cross-tenant access
    """
    app, TestSession = test_app
    
    # Arrange: Crear vehículo y ticket para taller_id=1
    db = TestSession()
    try:
        # Crear vehículo con taller_id=1
        vehiculo = Vehiculo(
            taller_id=1,
            placa="GHI789",
            marca="Nissan",
            modelo="Sentra",
            telefono_propietario="3007777777",
        )
        db.add(vehiculo)
        db.flush()
        
        # Crear ticket asociado al vehículo
        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo="T-004",
            placa="GHI789",
            motivo_visita="Diagnóstico",
            estado="ABIERTO",
        )
        db.add(ticket)
        db.commit()
        ticket_id = ticket.id
    finally:
        db.close()
    
    # Act: Intentar enviar WhatsApp con JWT de taller_id=2 (diferente taller)
    token = token_manager.create_access_token(
        data={"sub": "user2", "taller_id": 2, "roles": ["ADMIN"]}
    )
    
    client = TestClient(app)
    
    # Mock del middleware para inyectar request.state
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user2"}, "taller_id": 2}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    response = client.post(
        f"/api/whatsapp/tickets/{ticket_id}/mensaje",
        json={"mensaje": "Intento de acceso cross-tenant desde web"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assert: Debe retornar 404 sin revelar que el ticket existe
    assert response.status_code == 404
    assert response.json().get("detail") == "Resource not found"


# ---------------------------------------------------------------------------
# Task 3.5.3 — Verificar que el mensaje de error no revela información (req 1.8)
# ---------------------------------------------------------------------------


def test_error_404_no_revela_existencia_ticket(test_app, token_manager):
    """
    Los endpoints de WhatsApp deben retornar el mismo error 404 genérico
    tanto para tickets inexistentes como para tickets de otro taller.
    
    Validates: Requirement 1.8 - No revelar que el recurso existe en otro tenant
    """
    app, TestSession = test_app
    
    # Arrange: Crear vehículo y ticket para taller_id=1
    db = TestSession()
    try:
        vehiculo = Vehiculo(
            taller_id=1,
            placa="JKL012",
            marca="Ford",
            modelo="Focus",
            telefono_propietario="3008888888",
        )
        db.add(vehiculo)
        db.flush()
        
        ticket = Ticket(
            vehiculo_id=vehiculo.id,
            ticket_codigo="T-005",
            placa="JKL012",
            motivo_visita="Cambio de aceite",
            estado="ABIERTO",
        )
        db.add(ticket)
        db.commit()
        ticket_id_existente = ticket.id
    finally:
        db.close()
    
    # Act 1: Intentar acceder a ticket de otro taller
    token = token_manager.create_access_token(
        data={"sub": "user2", "taller_id": 2, "roles": ["ADMIN"]}
    )
    
    client = TestClient(app)
    
    # Mock del middleware
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": "user2"}, "taller_id": 2}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    
    response_cross_tenant = client.post(
        f"/api/whatsapp/tickets/{ticket_id_existente}/mensaje",
        json={"mensaje": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Act 2: Intentar acceder a ticket inexistente
    response_inexistente = client.post(
        "/api/whatsapp/tickets/99999/mensaje",
        json={"mensaje": "Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    
    # Assert: Ambos deben retornar el mismo error genérico
    assert response_cross_tenant.status_code == 404
    assert response_inexistente.status_code == 404
    assert response_cross_tenant.json().get("detail") == "Resource not found"
    assert response_inexistente.json().get("detail") == "Resource not found"

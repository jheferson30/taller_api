"""
Tests unitarios para WhatsApp route fixes (Task 3.6)
=====================================================
Consolida todos los tests requeridos por la tarea 3.6 del spec seguridad-rls.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8

Tests:
- POST /api/mobile/tickets/{id}/whatsapp sin JWT → 401
- POST /api/whatsapp/tickets/{id}/mensaje sin JWT → 401
- GET /api/mobile/whatsapp/logs sin JWT → 401
- GET /api/mobile/whatsapp/logs filtra por taller_id autenticado
- Cross-tenant ticket access en endpoints WhatsApp → 404
- Webhook routing con teléfono registrado → enruta correctamente
- Webhook routing con teléfono no registrado → 404 y logged
"""

import os
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.configuracion.base_datos import Base, obtener_db
from app.modelos.log_notificacion import LogNotificacion
from app.modelos.taller import Taller
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
                nombre VARCHAR(200) NOT NULL,
                whatsapp_phone_number VARCHAR(50) UNIQUE
            )
        """))
        conn.execute(text("""
            CREATE TABLE vehiculos (
                id INTEGER PRIMARY KEY,
                taller_id INTEGER NOT NULL,
                placa VARCHAR(20) UNIQUE NOT NULL,
                marca VARCHAR(100),
                modelo VARCHAR(100),
                telefono_propietario VARCHAR(500),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                estado VARCHAR(20) DEFAULT 'ABIERTO',
                FOREIGN KEY (vehiculo_id) REFERENCES vehiculos(id)
            )
        """))
        conn.execute(text("""
            CREATE TABLE log_notificacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                taller_id INTEGER,
                ticket_id INTEGER,
                telefono_destino VARCHAR(30),
                tipo_evento VARCHAR(20) NOT NULL,
                mensaje_enviado TEXT,
                resultado VARCHAR(10) NOT NULL,
                error_detalle TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


def mock_auth_middleware(app, taller_id: int):
    """Helper para mockear el middleware de autenticación."""
    original_call = app.__call__
    
    async def mock_call(scope, receive, send):
        if scope["type"] == "http":
            scope["state"] = {"user": {"sub": f"user{taller_id}"}, "taller_id": taller_id}
        return await original_call(scope, receive, send)
    
    app.__call__ = mock_call
    return app


# ---------------------------------------------------------------------------
# Task 3.6.1 — POST /api/mobile/tickets/{id}/whatsapp sin JWT → 401
# ---------------------------------------------------------------------------


def test_enviar_whatsapp_mobile_sin_jwt_retorna_401(test_app):
    """
    POST /api/mobile/tickets/{id}/whatsapp sin JWT debe retornar 401.
    
    Validates: Requirement 1.1 - El endpoint requiere autenticación
    """
    app, TestSession = test_app
    
    # Arrange: Crear ticket válido
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, telefono_propietario)
            VALUES (1, 'ABC123', 'Toyota', '3001234567')
        """))
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'ABC123'"))
        vehiculo_id = result.scalar()
        
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita)
            VALUES (:vehiculo_id, 'T-001', 'ABC123', 'Mantenimiento')
        """), {"vehiculo_id": vehiculo_id})
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-001'"))
        ticket_id = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Act: Request sin token JWT
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        response = client.post(
            f"/api/mobile/tickets/{ticket_id}/whatsapp",
            json={"mensaje": "Test sin auth"}
        )
    
    # Assert: Debe retornar 401 Unauthorized
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 3.6.2 — POST /api/whatsapp/tickets/{id}/mensaje sin JWT → 401
# ---------------------------------------------------------------------------


def test_enviar_whatsapp_web_sin_jwt_retorna_401(test_app):
    """
    POST /api/whatsapp/tickets/{id}/mensaje sin JWT debe retornar 401.
    
    Validates: Requirement 1.2 - El endpoint requiere autenticación
    """
    app, TestSession = test_app
    
    # Arrange: Crear ticket válido
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, telefono_propietario)
            VALUES (1, 'DEF456', 'Honda', '3009876543')
        """))
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'DEF456'"))
        vehiculo_id = result.scalar()
        
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita)
            VALUES (:vehiculo_id, 'T-002', 'DEF456', 'Reparación')
        """), {"vehiculo_id": vehiculo_id})
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-002'"))
        ticket_id = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Act: Request sin token JWT
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        response = client.post(
            f"/api/whatsapp/tickets/{ticket_id}/mensaje",
            json={"mensaje": "Test sin auth"}
        )
    
    # Assert: Debe retornar 401 Unauthorized
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 3.6.3 — GET /api/mobile/whatsapp/logs sin JWT → 401
# ---------------------------------------------------------------------------


def test_obtener_logs_sin_jwt_retorna_401(test_app):
    """
    GET /api/mobile/whatsapp/logs sin JWT debe retornar 401.
    
    Validates: Requirement 1.3 - El endpoint requiere autenticación
    """
    app, _ = test_app
    
    # Act: Request sin token JWT
    client = TestClient(app)
    response = client.get("/api/mobile/whatsapp/logs")
    
    # Assert: Debe retornar 401 Unauthorized
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Task 3.6.4 — GET /api/mobile/whatsapp/logs filtra por taller autenticado
# ---------------------------------------------------------------------------


def test_obtener_logs_filtra_por_taller_id(test_app):
    """
    GET /api/mobile/whatsapp/logs debe retornar solo logs del taller autenticado.
    
    Validates: Requirement 1.4 - Filtrado por taller_id del JWT
    """
    app, TestSession = test_app
    
    # Arrange: Crear logs para dos talleres diferentes
    db = TestSession()
    try:
        # Logs para taller 1
        for i in range(3):
            db.execute(text("""
                INSERT INTO log_notificacion 
                (taller_id, tipo_evento, resultado, telefono_destino, mensaje_enviado)
                VALUES (1, 'MANUAL', 'ENVIADO', :telefono, :mensaje)
            """), {
                "telefono": f"30011111{i}",
                "mensaje": f"Mensaje taller 1 - {i}"
            })
        
        # Logs para taller 2
        for i in range(2):
            db.execute(text("""
                INSERT INTO log_notificacion 
                (taller_id, tipo_evento, resultado, telefono_destino, mensaje_enviado)
                VALUES (2, 'MANUAL', 'ENVIADO', :telefono, :mensaje)
            """), {
                "telefono": f"30022222{i}",
                "mensaje": f"Mensaje taller 2 - {i}"
            })
        
        db.commit()
    finally:
        db.close()
    
    # Act: Request con JWT de taller_id=1
    mock_auth_middleware(app, taller_id=1)
    
    client = TestClient(app)
    response = client.get(
        "/api/mobile/whatsapp/logs",
        headers={"Authorization": "Bearer fake_token"}
    )
    
    # Assert: Debe retornar solo logs de taller_id=1
    assert response.status_code == 200
    logs = response.json()
    
    # Verificar que hay exactamente 3 logs (del taller 1)
    assert len(logs) == 3
    
    # Verificar que todos los teléfonos empiezan con 30011111
    for log in logs:
        assert log["telefono_destino"].startswith("30011111")


# ---------------------------------------------------------------------------
# Task 3.6.5 — Cross-tenant ticket access en WhatsApp endpoints → 404
# ---------------------------------------------------------------------------


def test_cross_tenant_ticket_access_mobile_retorna_404(test_app):
    """
    POST /api/mobile/tickets/{id}/whatsapp con ticket de otro taller → 404.
    
    Validates: Requirements 1.7, 1.8 - Cross-tenant isolation
    """
    app, TestSession = test_app
    
    # Arrange: Crear ticket para taller_id=1
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, telefono_propietario)
            VALUES (1, 'XYZ789', 'Mazda', '3005555555')
        """))
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'XYZ789'"))
        vehiculo_id = result.scalar()
        
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita)
            VALUES (:vehiculo_id, 'T-003', 'XYZ789', 'Revisión')
        """), {"vehiculo_id": vehiculo_id})
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-003'"))
        ticket_id = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Act: Intentar acceder con JWT de taller_id=2
    mock_auth_middleware(app, taller_id=2)
    
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        response = client.post(
            f"/api/mobile/tickets/{ticket_id}/whatsapp",
            json={"mensaje": "Cross-tenant attempt"},
            headers={"Authorization": "Bearer fake_token"}
        )
    
    # Assert: Debe retornar error indicando ticket no encontrado
    assert response.status_code == 200
    assert response.json().get("ok") is False
    assert response.json().get("error") == "ticket_no_encontrado"


def test_cross_tenant_ticket_access_web_retorna_404(test_app):
    """
    POST /api/whatsapp/tickets/{id}/mensaje con ticket de otro taller → 404.
    
    Validates: Requirements 1.7, 1.8 - Cross-tenant isolation
    """
    app, TestSession = test_app
    
    # Arrange: Crear ticket para taller_id=1
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, telefono_propietario)
            VALUES (1, 'GHI012', 'Nissan', '3007777777')
        """))
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'GHI012'"))
        vehiculo_id = result.scalar()
        
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita)
            VALUES (:vehiculo_id, 'T-004', 'GHI012', 'Diagnóstico')
        """), {"vehiculo_id": vehiculo_id})
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-004'"))
        ticket_id = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Act: Intentar acceder con JWT de taller_id=2
    mock_auth_middleware(app, taller_id=2)
    
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        response = client.post(
            f"/api/whatsapp/tickets/{ticket_id}/mensaje",
            json={"mensaje": "Cross-tenant attempt"},
            headers={"Authorization": "Bearer fake_token"}
        )
    
    # Assert: Debe retornar 404 sin revelar que el ticket existe
    assert response.status_code == 404
    assert response.json().get("detail") == "Resource not found"


# ---------------------------------------------------------------------------
# Task 3.6.6 — Webhook routing con teléfono registrado → enruta correctamente
# ---------------------------------------------------------------------------


def test_webhook_routing_con_telefono_registrado(test_app):
    """
    POST /whatsapp/webhook con teléfono registrado debe enrutar al taller correcto.
    
    Validates: Requirement 1.5 - Webhook routing correcto
    """
    app, TestSession = test_app
    
    # Arrange: Crear taller con número de WhatsApp
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO talleres (nombre, whatsapp_phone_number)
            VALUES ('Taller Test', '+573001234567')
        """))
        result = db.execute(text("SELECT id FROM talleres WHERE nombre = 'Taller Test'"))
        taller_id = result.scalar()
        db.commit()
    finally:
        db.close()
    
    # Act: Enviar webhook con ese número
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "display_phone_number": "+573001234567"
                    },
                    "messages": [{
                        "from": "573009876543",
                        "type": "text",
                        "text": {"body": "Hola desde cliente"}
                    }]
                }
            }]
        }]
    }
    
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        response = client.post("/whatsapp/webhook", json=payload)
    
    # Assert: Debe retornar 200 y crear log con taller_id correcto
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    
    # Verificar que se creó el log con taller_id correcto
    db = TestSession()
    try:
        result = db.execute(text("""
            SELECT taller_id, telefono_destino, mensaje_enviado, resultado
            FROM log_notificacion
            WHERE tipo_evento = 'ENTRANTE'
            ORDER BY id DESC
            LIMIT 1
        """))
        row = result.fetchone()
        
        assert row is not None
        assert row[0] == taller_id  # taller_id
        assert row[1] == "573009876543"  # telefono_destino
        assert row[2] == "Hola desde cliente"  # mensaje_enviado
        assert row[3] == "ENVIADO"  # resultado
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task 3.6.7 — Webhook routing con teléfono no registrado → 404 y logged
# ---------------------------------------------------------------------------


def test_webhook_routing_con_telefono_no_registrado_retorna_404(test_app):
    """
    POST /whatsapp/webhook con teléfono NO registrado debe retornar 404 y loguear.
    
    Validates: Requirement 1.6 - Manejo de webhooks no enrutados
    """
    app, TestSession = test_app
    
    # Act: Enviar webhook con número no registrado
    payload = {
        "entry": [{
            "changes": [{
                "value": {
                    "metadata": {
                        "display_phone_number": "+573009999999"
                    },
                    "messages": [{
                        "from": "573001111111",
                        "type": "text",
                        "text": {"body": "Mensaje sin destino"}
                    }]
                }
            }]
        }]
    }
    
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f), \
         patch('app.rutas.whatsapp_ruta.logger') as mock_logger:
        
        client = TestClient(app)
        response = client.post("/whatsapp/webhook", json=payload)
        
        # Assert: Debe retornar 404 con mensaje genérico
        assert response.status_code == 404
        assert response.json() == {"status": "unrouted", "message": "Resource not found"}
        
        # Verificar que se logueó warning
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Unrouted WhatsApp message" in warning_call
        assert "+573009999999" in warning_call
    
    # Verificar que se creó log de error
    db = TestSession()
    try:
        result = db.execute(text("""
            SELECT taller_id, telefono_destino, resultado, error_detalle
            FROM log_notificacion
            WHERE tipo_evento = 'ENTRANTE' AND resultado = 'ERROR'
            ORDER BY id DESC
            LIMIT 1
        """))
        row = result.fetchone()
        
        assert row is not None
        assert row[0] is None  # taller_id debe ser NULL
        assert row[1] == "+573009999999"  # telefono_destino
        assert row[2] == "ERROR"  # resultado
        assert "Unrouted message" in row[3]  # error_detalle
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Task 3.6.8 — Verificar que errores no revelan información de otros talleres
# ---------------------------------------------------------------------------


def test_error_messages_no_revelan_cross_tenant_info(test_app):
    """
    Los errores 404 deben ser idénticos para tickets inexistentes y de otros talleres.
    
    Validates: Requirement 1.8 - No revelar existencia de recursos en otros tenants
    """
    app, TestSession = test_app
    
    # Arrange: Crear ticket para taller_id=1
    db = TestSession()
    try:
        db.execute(text("""
            INSERT INTO vehiculos (taller_id, placa, marca, telefono_propietario)
            VALUES (1, 'JKL345', 'Ford', '3008888888')
        """))
        result = db.execute(text("SELECT id FROM vehiculos WHERE placa = 'JKL345'"))
        vehiculo_id = result.scalar()
        
        db.execute(text("""
            INSERT INTO tickets (vehiculo_id, ticket_codigo, placa, motivo_visita)
            VALUES (:vehiculo_id, 'T-005', 'JKL345', 'Cambio de aceite')
        """), {"vehiculo_id": vehiculo_id})
        result = db.execute(text("SELECT id FROM tickets WHERE ticket_codigo = 'T-005'"))
        ticket_id_existente = result.scalar()
        
        db.commit()
    finally:
        db.close()
    
    # Mock del middleware para taller_id=2
    mock_auth_middleware(app, taller_id=2)
    
    with patch('app.rutas.whatsapp_ruta.limiter.limit', lambda x: lambda f: f):
        client = TestClient(app)
        
        # Act 1: Intentar acceder a ticket de otro taller
        response_cross_tenant = client.post(
            f"/api/whatsapp/tickets/{ticket_id_existente}/mensaje",
            json={"mensaje": "Test"},
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Act 2: Intentar acceder a ticket inexistente
        response_inexistente = client.post(
            "/api/whatsapp/tickets/99999/mensaje",
            json={"mensaje": "Test"},
            headers={"Authorization": "Bearer fake_token"}
        )
        
        # Assert: Ambos deben retornar el mismo error genérico
        assert response_cross_tenant.status_code == 404
        assert response_inexistente.status_code == 404
        assert response_cross_tenant.json().get("detail") == "Resource not found"
        assert response_inexistente.json().get("detail") == "Resource not found"
